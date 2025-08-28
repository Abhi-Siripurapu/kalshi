#!/usr/bin/env python3
"""
Simple working Kalshi adapter based on proven WebSocket test
"""
import asyncio
import json
import logging
import os
import time
from adapters.kalshi.auth import KalshiAuth
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleKalshiAdapter:
    def __init__(self, api_key_id: str, private_key_path: str):
        self.auth = KalshiAuth(api_key_id, private_key_path)
        self.ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
        self.websocket = None
        self.message_id = 1
        self.running = False
        
        # Test markets
        self.test_markets = ["KXUSAINTEL-25", "KXSENATESCR-26-PDANS"]
        
    async def start(self):
        """Start the simplified adapter"""
        self.running = True
        logger.info("🚀 Starting Simple Kalshi Adapter")
        
        try:
            # Connect
            await self.connect()
            
            # Subscribe to test markets
            await self.subscribe_to_test_markets()
            
            # Listen indefinitely
            await self.listen_for_data()
            
        except Exception as e:
            logger.error(f"Adapter failed: {e}")
        finally:
            await self.close()
    
    async def connect(self):
        """Connect to Kalshi WebSocket"""
        headers = self.auth.create_ws_headers()
        self.websocket = await websockets.connect(
            self.ws_url,
            additional_headers=headers,
            ping_interval=30,
            ping_timeout=10
        )
        logger.info("✅ Connected to Kalshi WebSocket")
    
    async def subscribe_to_test_markets(self):
        """Subscribe to orderbook updates for test markets"""
        for market in self.test_markets:
            subscription = {
                "id": self.message_id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_ticker": market
                }
            }
            
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"📡 Subscribed to {market}")
            self.message_id += 1
            await asyncio.sleep(0.1)
    
    async def listen_for_data(self):
        """Listen for incoming data and log it"""
        message_count = 0
        last_status_time = 0
        
        while self.running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                message_count += 1
                
                msg_type = data.get("type", "unknown")
                
                # Log different message types
                if msg_type == "orderbook_snapshot":
                    market = data.get("msg", {}).get("market_ticker", "unknown")
                    yes_bids = len(data.get("msg", {}).get("yes", []))
                    no_bids = len(data.get("msg", {}).get("no", []))
                    logger.info(f"📊 SNAPSHOT: {market} - {yes_bids} yes bids, {no_bids} no bids")
                    
                elif msg_type == "orderbook_delta":
                    market = data.get("msg", {}).get("market_ticker", "unknown")
                    price = data.get("msg", {}).get("price", 0)
                    delta = data.get("msg", {}).get("delta", 0)
                    side = data.get("msg", {}).get("side", "unknown")
                    logger.info(f"🔄 DELTA: {market} - {side} @ {price}¢ Δ{delta}")
                    
                elif msg_type == "ticker":
                    market = data.get("msg", {}).get("market_ticker", "unknown")
                    bid = data.get("msg", {}).get("bid")
                    ask = data.get("msg", {}).get("ask")
                    if market in self.test_markets:
                        logger.info(f"📈 TICKER: {market} - Bid: {bid}¢, Ask: {ask}¢")
                    
                elif msg_type == "subscribed":
                    channel = data.get("msg", {}).get("channel", "unknown")
                    logger.info(f"✅ SUBSCRIBED to {channel}")
                    
                elif msg_type == "error":
                    logger.error(f"❌ ERROR: {data.get('msg', {})}")
                
                # Status update every 10 seconds
                if time.time() - last_status_time > 10:
                    logger.info(f"📡 Status: {message_count} messages received, adapter running...")
                    last_status_time = time.time()
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def close(self):
        """Close WebSocket connection"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket closed")

async def main():
    """Run the simple adapter"""
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    if not api_key:
        logger.error("❌ Error: KALSHI_API_KEY environment variable required")
        return
    
    adapter = SimpleKalshiAdapter(api_key, private_key_path)
    
    try:
        await adapter.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main())