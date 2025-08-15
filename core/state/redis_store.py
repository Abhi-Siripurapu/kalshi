import json
import time
import logging
from typing import Dict, List, Optional, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisBookStore:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def set_book(self, venue_id: str, market_id: str, outcome_id: str, book_data: Dict):
        """Store latest book data"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        key = f"book:{venue_id}:{market_id}:{outcome_id}"
        
        # Add timestamp for staleness checking
        book_data["stored_at"] = time.time()
        
        try:
            await self.redis_client.set(key, json.dumps(book_data))
            logger.debug(f"Stored book: {key}")
        except Exception as e:
            logger.error(f"Error storing book {key}: {e}")
    
    async def get_book(self, venue_id: str, market_id: str, outcome_id: str) -> Optional[Dict]:
        """Get latest book data"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        key = f"book:{venue_id}:{market_id}:{outcome_id}"
        
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting book {key}: {e}")
            return None
    
    async def get_all_books(self, venue_id: Optional[str] = None) -> Dict[str, Dict]:
        """Get all books, optionally filtered by venue"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        pattern = f"book:{venue_id}:*" if venue_id else "book:*"
        books = {}
        
        try:
            async for key in self.redis_client.scan_iter(match=pattern):
                key_str = key.decode()
                data = await self.redis_client.get(key)
                if data:
                    books[key_str] = json.loads(data)
            return books
        except Exception as e:
            logger.error(f"Error getting all books: {e}")
            return {}
    
    async def set_market_info(self, venue_id: str, market_id: str, market_data: Dict):
        """Store market information"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        key = f"market:{venue_id}:{market_id}"
        
        try:
            await self.redis_client.set(key, json.dumps(market_data))
            logger.debug(f"Stored market info: {key}")
        except Exception as e:
            logger.error(f"Error storing market {key}: {e}")
    
    async def get_market_info(self, venue_id: str, market_id: str) -> Optional[Dict]:
        """Get market information"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        key = f"market:{venue_id}:{market_id}"
        
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting market {key}: {e}")
            return None
    
    async def publish_event(self, channel: str, event: Dict):
        """Publish event to Redis pub/sub"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        try:
            await self.redis_client.publish(channel, json.dumps(event))
            logger.debug(f"Published to {channel}: {event.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")
    
    async def set_health(self, venue_id: str, health_data: Dict):
        """Store venue health status"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        key = f"health:{venue_id}"
        
        try:
            await self.redis_client.set(key, json.dumps(health_data))
            # Set expiration to detect stale health reports
            await self.redis_client.expire(key, 30)  # 30 seconds
            logger.debug(f"Stored health: {key}")
        except Exception as e:
            logger.error(f"Error storing health {key}: {e}")
    
    async def get_health(self, venue_id: str) -> Optional[Dict]:
        """Get venue health status"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        key = f"health:{venue_id}"
        
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting health {key}: {e}")
            return None
    
    async def get_all_health(self) -> Dict[str, Dict]:
        """Get health status for all venues"""
        if not self.redis_client:
            raise RuntimeError("Redis not connected")
            
        health_data = {}
        
        try:
            async for key in self.redis_client.scan_iter(match="health:*"):
                key_str = key.decode()
                venue_id = key_str.split(":", 1)[1]
                data = await self.redis_client.get(key)
                if data:
                    health_data[venue_id] = json.loads(data)
            return health_data
        except Exception as e:
            logger.error(f"Error getting all health: {e}")
            return {}


class EventPublisher:
    """Publishes normalized events to Redis and handles routing"""
    
    def __init__(self, redis_store: RedisBookStore):
        self.redis_store = redis_store
        
    async def publish_event(self, event: Dict):
        """Route and publish normalized events"""
        event_type = event.get("type")
        venue_id = event.get("venue_id")
        
        try:
            if event_type == "book_snapshot":
                await self._handle_book_snapshot(event)
            elif event_type == "book_delta":
                await self._handle_book_delta(event)
            elif event_type == "market_info":
                await self._handle_market_info(event)
            elif event_type == "health":
                await self._handle_health(event)
            elif event_type == "trade":
                await self._handle_trade(event)
            
            # Publish to general event stream
            await self.redis_store.publish_event("events", event)
            
            # Publish to venue-specific stream
            if venue_id:
                await self.redis_store.publish_event(f"events:{venue_id}", event)
                
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
    
    async def _handle_book_snapshot(self, event: Dict):
        """Handle book snapshot events"""
        books = event["data"]
        
        for book in books:
            # Handle both dict and object formats
            if isinstance(book, dict):
                # Store in Redis
                book_data = {
                    "ts_ns": book.get("ts_ns"),
                    "bids": book.get("bids"),
                    "asks": book.get("asks"),
                    "best_bid": book.get("best_bid"),
                    "best_ask": book.get("best_ask"),
                    "mid_px": book.get("mid_px"),
                    "sequence": book.get("sequence")
                }
                
                await self.redis_store.set_book(
                    book.get("venue_id"),
                    book.get("market_id"), 
                    book.get("outcome_id"),
                    book_data
                )
            else:
                # Handle object format (fallback) - but should not be needed since we normalize to dict
                try:
                    book_data = {
                        "ts_ns": getattr(book, 'ts_ns', 0),
                        "bids": getattr(book, 'bids', []),
                        "asks": getattr(book, 'asks', []),
                        "best_bid": getattr(book, 'best_bid', None),
                        "best_ask": getattr(book, 'best_ask', None),
                        "mid_px": getattr(book, 'mid_px', None),
                        "sequence": getattr(book, 'sequence', 0)
                    }
                    
                    await self.redis_store.set_book(
                        getattr(book, 'venue_id', ''),
                        getattr(book, 'market_id', ''), 
                        getattr(book, 'outcome_id', ''),
                        book_data
                    )
                except Exception as e:
                    logger.error(f"Error handling book object format: {e}, book: {book}")
    
    async def _handle_book_delta(self, event: Dict):
        """Handle book delta events"""
        # For now, we'll need to fetch current book and apply delta
        # This would require implementing delta application logic
        logger.debug("Book delta received - full implementation needed")
    
    async def _handle_market_info(self, event: Dict):
        """Handle market info events"""
        market = event["data"]
        
        # Handle both dict and object formats
        if isinstance(market, dict):
            market_data = {
                "title": market.get("title"),
                "description": market.get("description"),
                "resolution_source": market.get("resolution_source"),
                "resolution_ts": market.get("resolution_ts"),
                "timezone": market.get("timezone"),
                "currency": market.get("currency"),
                "outcomes": market.get("outcomes"),
                "status": market.get("status"),
                "created_ts": market.get("created_ts"),
                "mapping_tags": market.get("mapping_tags")
            }
            
            await self.redis_store.set_market_info(
                market.get("venue_id"),
                market.get("market_id"),
                market_data
            )
        else:
            # Handle object format (fallback) - but should not be needed since we normalize to dict
            try:
                market_data = {
                    "title": getattr(market, 'title', ''),
                    "description": getattr(market, 'description', ''),
                    "resolution_source": getattr(market, 'resolution_source', ''),
                    "resolution_ts": getattr(market, 'resolution_ts', 0),
                    "timezone": getattr(market, 'timezone', ''),
                    "currency": getattr(market, 'currency', ''),
                    "outcomes": getattr(market, 'outcomes', []),
                    "status": getattr(market, 'status', ''),
                    "created_ts": getattr(market, 'created_ts', 0),
                    "mapping_tags": getattr(market, 'mapping_tags', {})
                }
                
                await self.redis_store.set_market_info(
                    getattr(market, 'venue_id', ''),
                    getattr(market, 'market_id', ''),
                    market_data
                )
            except Exception as e:
                logger.error(f"Error handling market object format: {e}, market: {market}")
    
    async def _handle_health(self, event: Dict):
        """Handle health events"""
        venue_id = event["venue_id"]
        health_data = event["data"]
        
        await self.redis_store.set_health(venue_id, health_data)
    
    async def _handle_trade(self, event: Dict):
        """Handle trade events"""
        # Store recent trades in a time-series structure
        logger.debug("Trade received - implementation needed")


async def create_publisher(redis_url: str = "redis://localhost:6379") -> EventPublisher:
    """Create and initialize an event publisher"""
    redis_store = RedisBookStore(redis_url)
    await redis_store.connect()
    return EventPublisher(redis_store)