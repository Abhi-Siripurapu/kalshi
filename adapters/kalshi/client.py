import asyncio
import json
import time
import logging
import aiohttp
import websockets
from typing import Dict, List, Optional, Callable
from .auth import KalshiAuth

logger = logging.getLogger(__name__)


class KalshiClient:
    def __init__(
        self, 
        api_key_id: str, 
        private_key_path: str,
        base_url: str = "https://api.elections.kalshi.com",
        ws_url: str = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    ):
        self.auth = KalshiAuth(api_key_id, private_key_path)
        self.base_url = base_url
        self.ws_url = ws_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.message_id = 1
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.backoff_base = 1.0
        self.subscribed_markets: Dict[str, List[str]] = {}  # market_ticker -> channels
        
        # Callbacks
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.websocket:
            await self.websocket.close()

    async def get_markets(
        self, 
        limit: int = 100,
        cursor: Optional[str] = None,
        series_ticker: Optional[str] = None,
        status: str = "open"
    ) -> Dict:
        """Get markets with pagination support"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")

        params = {
            "limit": limit,
            "status": status
        }
        if cursor:
            params["cursor"] = cursor
        if series_ticker:
            params["series_ticker"] = series_ticker

        url = f"{self.base_url}/trade-api/v2/markets"
        
        try:
            headers = self.auth.create_headers("GET", "/trade-api/v2/markets")
            async with self.session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            raise

    async def get_all_markets(self, series_ticker: Optional[str] = None, status: str = "open") -> List[Dict]:
        """Get all markets for a series, handling pagination"""
        all_markets = []
        cursor = None
        
        while True:
            try:
                data = await self.get_markets(
                    limit=100, 
                    cursor=cursor, 
                    series_ticker=series_ticker,
                    status=status
                )
                markets = data.get("markets", [])
                all_markets.extend(markets)
                
                cursor = data.get("cursor")
                if not cursor:
                    break
                    
                logger.info(f"Fetched {len(markets)} markets, total: {len(all_markets)}")
                
                # Rate limiting for Basic tier (10 requests/second)
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in get_all_markets: {e}")
                break
                
        return all_markets

    async def get_orderbook(self, market_ticker: str, depth: Optional[int] = None) -> Dict:
        """Get orderbook for a specific market"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")

        params = {}
        if depth:
            params["depth"] = depth

        url = f"{self.base_url}/trade-api/v2/markets/{market_ticker}/orderbook"
        
        try:
            headers = self.auth.create_headers("GET", f"/trade-api/v2/markets/{market_ticker}/orderbook")
            async with self.session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Error fetching orderbook for {market_ticker}: {e}")
            raise

    async def connect_websocket(self):
        """Establish WebSocket connection with authentication"""
        try:
            headers = self.auth.create_ws_headers()
            
            logger.info(f"Connecting to Kalshi WebSocket: {self.ws_url}")
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            logger.info("Kalshi WebSocket connected successfully")
            self.reconnect_attempts = 0
            
            if self.on_connected:
                await self.on_connected()
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kalshi WebSocket: {e}")
            if self.on_error:
                await self.on_error(e)
            return False

    async def subscribe_to_markets(self, channels: List[str], market_tickers: List[str]):
        """Subscribe to specific channels for given markets"""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")

        # Subscribe to each market individually as per Kalshi docs
        for market_ticker in market_tickers:
            subscription = {
                "id": self.message_id,
                "cmd": "subscribe",
                "params": {
                    "channels": channels,
                    "market_ticker": market_ticker  # Singular as per docs
                }
            }
            
            logger.info(f"Subscribing to {channels} for market: {market_ticker}")
            await self.websocket.send(json.dumps(subscription))
            self.message_id += 1
            
            # Track subscriptions for reconnection
            if market_ticker not in self.subscribed_markets:
                self.subscribed_markets[market_ticker] = []
            for channel in channels:
                if channel not in self.subscribed_markets[market_ticker]:
                    self.subscribed_markets[market_ticker].append(channel)
                    
            # Rate limiting between subscriptions
            await asyncio.sleep(0.1)

    async def subscribe_to_orderbooks(self, market_tickers: List[str]):
        """Subscribe to orderbook updates for specific markets"""
        await self.subscribe_to_markets(["orderbook_delta"], market_tickers)
    
    async def subscribe_to_tickers(self, market_tickers: Optional[List[str]] = None):
        """Subscribe to ticker updates for markets (all markets if None)"""
        if market_tickers:
            await self.subscribe_to_markets(["ticker"], market_tickers)
        else:
            # Subscribe to all market tickers
            subscription = {
                "id": self.message_id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["ticker"]
                }
            }
            await self.websocket.send(json.dumps(subscription))
            self.message_id += 1
    
    async def subscribe_to_trades(self, market_tickers: Optional[List[str]] = None):
        """Subscribe to trade updates for markets (all trades if None)"""
        if market_tickers:
            await self.subscribe_to_markets(["trade"], market_tickers)
        else:
            # Subscribe to all trades
            subscription = {
                "id": self.message_id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["trade"]
                }
            }
            await self.websocket.send(json.dumps(subscription))
            self.message_id += 1
    
    async def get_market_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Get detailed market information by ticker"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")

        url = f"{self.base_url}/trade-api/v2/markets/{ticker}"
        
        try:
            headers = self.auth.create_headers("GET", f"/trade-api/v2/markets/{ticker}")
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error fetching market {ticker}: {e}")
            return None

    async def resubscribe_all(self):
        """Resubscribe to all previously subscribed markets"""
        if not self.subscribed_markets:
            return
            
        logger.info("Resubscribing to all markets after reconnection")
        for market_ticker, channels in self.subscribed_markets.items():
            try:
                await self.subscribe_to_markets(channels, [market_ticker])
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error resubscribing to {market_ticker}: {e}")

    async def listen(self):
        """Listen for WebSocket messages with automatic reconnection"""
        while True:
            try:
                if not self.websocket or self.websocket.closed:
                    connected = await self.connect_websocket()
                    if not connected:
                        await self._handle_reconnect()
                        continue
                    
                    # Resubscribe after reconnection
                    if self.subscribed_markets:
                        await self.resubscribe_all()

                async for message in self.websocket:
                    try:
                        data = json.loads(message)
                        
                        if self.on_message:
                            await self.on_message(data)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received: {message}, error: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Kalshi WebSocket connection closed")
                if self.on_disconnected:
                    await self.on_disconnected()
                await self._handle_reconnect()
                
            except Exception as e:
                logger.error(f"Unexpected WebSocket error: {e}")
                if self.on_error:
                    await self.on_error(e)
                await self._handle_reconnect()

    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return

        self.reconnect_attempts += 1
        backoff_time = min(30, self.backoff_base * (2 ** (self.reconnect_attempts - 1)))
        
        logger.info(f"Reconnecting in {backoff_time}s (attempt {self.reconnect_attempts})")
        await asyncio.sleep(backoff_time)

    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        if self.session:
            await self.session.close()
            self.session = None