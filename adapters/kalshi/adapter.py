import asyncio
import logging
import time
import os
from typing import Dict, List, Optional, Callable
from collections import deque
import statistics

from .client import KalshiClient
from .normalizer import KalshiNormalizer


logger = logging.getLogger(__name__)


class LatencyTracker:
    def __init__(self, window_size: int = 100):
        self.latencies = deque(maxlen=window_size)
        
    def add_latency(self, latency_ms: float):
        self.latencies.append(latency_ms)
        
    def get_p50(self) -> Optional[float]:
        if not self.latencies:
            return None
        return statistics.median(self.latencies)
        
    def get_p95(self) -> Optional[float]:
        if len(self.latencies) < 5:
            return None
        sorted_latencies = sorted(self.latencies)
        index = int(0.95 * len(sorted_latencies))
        return sorted_latencies[index]


class BookStateManager:
    def __init__(self):
        self.state = "DISCONNECTED"  # DISCONNECTED -> CONNECTING -> WAIT_SNAPSHOT -> LIVE
        self.buffered_deltas = []
        self.buffer_start_ts = None
        self.last_update_ts = {}  # market_id -> timestamp
        self.staleness_threshold_s = 3
        
    def set_state(self, new_state: str):
        logger.info(f"Book state: {self.state} -> {new_state}")
        self.state = new_state
        
    def is_stale(self, market_id: str) -> bool:
        last_update = self.last_update_ts.get(market_id, 0)
        return (time.time() - last_update) > self.staleness_threshold_s
        
    def update_timestamp(self, market_id: str):
        self.last_update_ts[market_id] = time.time()


class KalshiAdapter:
    def __init__(
        self,
        api_key_id: str,
        private_key_path: str,
        target_markets: List[str],
        publisher: Optional[Callable] = None,
        environment: str = "demo"
    ):
        self.api_key_id = api_key_id
        self.private_key_path = private_key_path
        self.target_markets = target_markets
        self.publisher = publisher  # Function to publish normalized events
        
        # Environment URLs
        if environment == "demo":
            base_url = "https://demo-api.kalshi.co"
            ws_url = "wss://demo-api.kalshi.co/trade-api/ws/v2"
        else:
            base_url = "https://api.elections.kalshi.com"
            ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
            
        self.client = KalshiClient(api_key_id, private_key_path, base_url, ws_url)
        self.normalizer = KalshiNormalizer()
        
        # State management
        self.book_state = BookStateManager()
        self.latency_tracker = LatencyTracker()
        self.health_status = "down"
        self.discovered_markets = {}
        self.running = False
        
        # Health monitoring
        self.last_health_report = 0
        self.health_report_interval = 5  # seconds
        
        # Set up client callbacks
        self.client.on_message = self._handle_message
        self.client.on_connected = self._handle_connected
        self.client.on_disconnected = self._handle_disconnected
        self.client.on_error = self._handle_error

    async def start(self):
        """Start the adapter"""
        logger.info("Starting Kalshi adapter")
        self.running = True
        
        try:
            # Initialize client session
            await self.client.__aenter__()
            
            # Discover target markets
            await self._discover_markets()
            
            # Start WebSocket connection and message processing
            self.book_state.set_state("CONNECTING")
            
            # Start background tasks
            health_task = asyncio.create_task(self._health_monitor_loop())
            listen_task = asyncio.create_task(self.client.listen())
            
            # Wait for tasks to complete
            await asyncio.gather(health_task, listen_task)
            
        except Exception as e:
            logger.error(f"Error in Kalshi adapter: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the adapter"""
        logger.info("Stopping Kalshi adapter")
        self.running = False
        await self.client.close()

    async def _discover_markets(self):
        """Discover and cache information about target markets"""
        logger.info("Discovering target markets")
        
        try:
            # Get first page of markets
            response = await self.client.get_markets(limit=100, status="open")
            market_list = response.get("markets", [])
            
            # If no specific targets, auto-discover from first few markets
            if not self.target_markets:
                # Take only 5 active markets to avoid rate limits
                self.target_markets = [m["ticker"] for m in market_list[:5]]
                logger.info(f"Auto-discovered 5 markets: {self.target_markets}")
            
            for market in market_list:
                ticker = market["ticker"]
                if ticker in self.target_markets:
                    self.discovered_markets[ticker] = market
                    
                    # Publish market info
                    normalized_market = self.normalizer.normalize_market(market)
                    await self._publish_event({
                        "type": "market_info",
                        "venue_id": "kalshi",
                        "data": normalized_market,
                        "ts_received_ns": time.time_ns()
                    })
            
            logger.info(f"Discovered {len(self.discovered_markets)} target markets")
            
        except Exception as e:
            logger.error(f"Error discovering markets: {e}")
            raise

    async def _handle_connected(self):
        """Handle WebSocket connection established"""
        logger.info("Kalshi WebSocket connected")
        self.health_status = "healthy"
        self.book_state.set_state("WAIT_SNAPSHOT")
        
        # Subscribe to orderbook updates for target markets
        if self.target_markets:
            try:
                await self.client.subscribe_to_orderbooks(self.target_markets)
                logger.info(f"Subscribed to orderbooks for {len(self.target_markets)} markets")
            except Exception as e:
                logger.error(f"Error subscribing to markets: {e}")
                self.health_status = "degraded"

    async def _handle_disconnected(self):
        """Handle WebSocket disconnection"""
        logger.warning("Kalshi WebSocket disconnected")
        self.health_status = "down"
        self.book_state.set_state("DISCONNECTED")

    async def _handle_error(self, error):
        """Handle WebSocket errors"""
        logger.error(f"Kalshi WebSocket error: {error}")
        self.health_status = "degraded"

    async def _handle_message(self, message: Dict):
        """Handle incoming WebSocket messages"""
        recv_ts_ns = time.time_ns()
        
        try:
            # Calculate latency if message has timestamp
            if "ts" in message:
                msg_ts_ms = message["ts"]
                latency_ms = (recv_ts_ns / 1_000_000) - msg_ts_ms
                self.latency_tracker.add_latency(latency_ms)
            
            # Normalize message
            normalized_event = self.normalizer.normalize_websocket_message(message, recv_ts_ns)
            
            if normalized_event:
                await self._process_normalized_event(normalized_event)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}, message: {message}")

    async def _process_normalized_event(self, event: Dict):
        """Process normalized events based on type"""
        event_type = event.get("type")
        
        if event_type == "book_snapshot":
            await self._handle_book_snapshot(event)
        elif event_type == "book_delta":
            await self._handle_book_delta(event)
        elif event_type == "subscribed":
            logger.info(f"Subscription confirmed: {event['data']}")
            
            # Get initial orderbook snapshots
            await self._fetch_initial_orderbooks()
            
        elif event_type == "error":
            logger.error(f"Received error: {event['data']}")
            
        # Publish all events
        await self._publish_event(event)

    async def _handle_book_snapshot(self, event: Dict):
        """Handle orderbook snapshot"""
        books = event["data"]
        
        if books:
            market_id = books[0].market_id
            logger.info(f"Received orderbook snapshot for {market_id}")
            
            self.book_state.update_timestamp(market_id)
            
            # If we were waiting for snapshot, now go live
            if self.book_state.state == "WAIT_SNAPSHOT":
                self.book_state.set_state("LIVE")

    async def _handle_book_delta(self, event: Dict):
        """Handle orderbook delta updates"""
        delta_data = event["data"]
        market_id = delta_data.get("market_id", "")
        
        if self.book_state.state == "LIVE":
            self.book_state.update_timestamp(market_id)
        else:
            # Buffer deltas until we get snapshot
            self.book_state.buffered_deltas.append(event)

    async def _fetch_initial_orderbooks(self):
        """Fetch initial orderbook snapshots for subscribed markets"""
        logger.info("Fetching initial orderbook snapshots")
        
        for market_ticker in self.target_markets:
            try:
                orderbook_data = await self.client.get_orderbook(market_ticker)
                recv_ts_ns = time.time_ns()
                
                # Normalize and publish snapshot
                books = self.normalizer.normalize_orderbook_snapshot(
                    market_ticker, 
                    orderbook_data, 
                    recv_ts_ns
                )
                
                await self._publish_event({
                    "type": "book_snapshot",
                    "venue_id": "kalshi",
                    "data": books,
                    "ts_received_ns": recv_ts_ns
                })
                
                # Rate limiting for Basic tier
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching orderbook for {market_ticker}: {e}")

    async def _health_monitor_loop(self):
        """Background task to monitor and report health"""
        while self.running:
            try:
                await asyncio.sleep(self.health_report_interval)
                await self._report_health()
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")

    async def _report_health(self):
        """Report current health status"""
        now = time.time()
        
        # Check for stale markets
        stale_markets = []
        for market_id in self.target_markets:
            if self.book_state.is_stale(market_id):
                stale_markets.append(market_id)
        
        # Determine overall health
        if stale_markets:
            status = "degraded"
            reason = f"Stale data for {len(stale_markets)} markets"
        elif self.health_status == "down":
            status = "down"
            reason = "WebSocket disconnected"
        else:
            status = "healthy"
            reason = None
        
        # Create health event
        health_event = {
            "type": "health",
            "venue_id": "kalshi",
            "data": {
                "status": status,
                "reason": reason,
                "ts_ns": time.time_ns(),
                "latency_p50_ms": self.latency_tracker.get_p50(),
                "latency_p95_ms": self.latency_tracker.get_p95(),
                "subscribed_markets": len(self.target_markets),
                "stale_markets": len(stale_markets)
            },
            "ts_received_ns": time.time_ns()
        }
        
        await self._publish_event(health_event)

    async def _publish_event(self, event: Dict):
        """Publish normalized event to downstream systems"""
        if self.publisher:
            try:
                await self.publisher(event)
            except Exception as e:
                logger.error(f"Error publishing event: {e}")


async def main():
    """Main entry point for running Kalshi adapter standalone"""
    # Get configuration from environment
    api_key_id = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    environment = os.getenv("KALSHI_ENVIRONMENT", "demo")
    
    if not api_key_id:
        raise ValueError("KALSHI_API_KEY environment variable required")
    
    # Target markets - could be loaded from config
    target_markets = [
        "KXHIGHNY-24JAN15-T75",  # Example NYC temperature market
        "KXHIGHNY-24JAN15-T80"   # Another temperature market
    ]
    
    # Simple publisher that just logs events
    async def log_publisher(event):
        event_type = event.get("type")
        if event_type == "book_snapshot":
            books = event["data"]
            for book in books:
                logger.info(f"Book snapshot: {book.market_id}/{book.outcome_id} - "
                           f"Best bid: {book.best_bid}, Best ask: {book.best_ask}")
        elif event_type == "health":
            health = event["data"]
            logger.info(f"Health: {health['status']} - P95 latency: {health['latency_p95_ms']}ms")
    
    # Create and run adapter
    adapter = KalshiAdapter(
        api_key_id=api_key_id,
        private_key_path=private_key_path,
        target_markets=target_markets,
        publisher=log_publisher,
        environment=environment
    )
    
    try:
        await adapter.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await adapter.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())