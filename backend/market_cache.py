#!/usr/bin/env python3
"""
Simple Market Cache - Atomic implementation
Fetches and caches ALL Kalshi markets in memory
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional
from simple_kalshi_client import SimpleKalshiClient

logger = logging.getLogger(__name__)

class SimpleMarketCache:
    """Simple in-memory cache for all Kalshi markets"""
    
    def __init__(self, api_key: str, private_key_path: str):
        self.api_key = api_key
        self.private_key_path = private_key_path
        self.markets: List[Dict] = []
        self.last_update: float = 0
        self.update_interval = 300  # 5 minutes
        self.client: Optional[SimpleKalshiClient] = None
        self.updating = False
    
    async def start(self):
        """Start the cache and do initial load"""
        self.client = SimpleKalshiClient(self.api_key, self.private_key_path)
        await self.client.__aenter__()
        
        # Initial load
        await self.update_markets()
        
        # Start background update task
        asyncio.create_task(self._background_update())
        print(f"✅ Market cache started with {len(self.markets)} markets")
    
    async def stop(self):
        """Stop the cache and cleanup"""
        if self.client:
            await self.client.__aexit__(None, None, None)
    
    async def _background_update(self):
        """Background task to periodically update markets"""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                if not self.updating:
                    await self.update_markets()
            except Exception as e:
                logger.error(f"Background update error: {e}")
    
    async def update_markets(self):
        """Fetch all markets from Kalshi API"""
        if self.updating or not self.client:
            return
        
        self.updating = True
        start_time = time.time()
        
        try:
            print("🔄 Updating market cache...")
            
            # Fetch markets in batches with pagination
            all_markets = []
            cursor = None
            batch_count = 0
            
            while True:
                batch_count += 1
                print(f"📊 Fetching batch {batch_count}...")
                
                # Get batch of markets
                params = {"limit": 1000, "status": "open"}
                if cursor:
                    params["cursor"] = cursor
                
                data = await self.client.get_markets(**params)
                markets = data.get("markets", [])
                
                if not markets:
                    break
                
                all_markets.extend(markets)
                cursor = data.get("cursor")
                
                print(f"📈 Got {len(markets)} markets (total: {len(all_markets)})")
                
                # If no cursor, we're done
                if not cursor:
                    break
                
                # Safety limit
                if batch_count >= 20:
                    print("⚠️ Reached batch limit, stopping")
                    break
            
            # Update cache
            self.markets = all_markets
            self.last_update = time.time()
            
            duration = time.time() - start_time
            print(f"✅ Market cache updated: {len(self.markets)} markets in {duration:.1f}s")
            
            # Print some stats
            self._print_stats()
            
        except Exception as e:
            print(f"❌ Market cache update failed: {e}")
            logger.error(f"Market cache update error: {e}")
        finally:
            self.updating = False
    
    def _print_stats(self):
        """Print cache statistics"""
        if not self.markets:
            return
        
        # Count by category keywords
        politics = len([m for m in self.markets if any(word in m.get('title', '').lower() 
                       for word in ['election', 'president', 'trump', 'biden', 'vote', 'senate', 'congress', 'potus'])])
        
        sports = len([m for m in self.markets if any(word in m.get('title', '').lower() 
                     for word in ['nfl', 'mlb', 'nba', 'game', 'championship', 'ufc', 'pga', 'match', 'tournament'])])
        
        crypto = len([m for m in self.markets if any(word in m.get('title', '').lower() 
                     for word in ['bitcoin', 'btc', 'crypto', 'ethereum', 'eth'])])
        
        weather = len([m for m in self.markets if any(word in m.get('title', '').lower() 
                      for word in ['temperature', 'weather', 'snow', 'rain', 'hurricane'])])
        
        print(f"📊 Market stats:")
        print(f"  📈 Total: {len(self.markets)}")
        print(f"  🏛️ Politics: {politics}")
        print(f"  🏈 Sports: {sports}")
        print(f"  ₿ Crypto: {crypto}")
        print(f"  🌡️ Weather: {weather}")
    
    def get_markets(self, limit: int = 1000, search: str = "", category: str = "all") -> List[Dict]:
        """Get markets from cache with filtering"""
        markets = self.markets.copy()
        
        # Apply search filter
        if search:
            search = search.lower()
            markets = [m for m in markets if search in m.get('title', '').lower() 
                      or search in m.get('ticker', '').lower()]
        
        # Apply category filter
        if category != "all":
            if category == "politics":
                markets = [m for m in markets if any(word in m.get('title', '').lower() 
                          for word in ['election', 'president', 'trump', 'biden', 'vote', 'senate', 'congress', 'potus'])]
            elif category == "sports":
                markets = [m for m in markets if any(word in m.get('title', '').lower() 
                          for word in ['nfl', 'mlb', 'nba', 'game', 'championship', 'ufc', 'pga', 'match', 'tournament'])]
            elif category == "crypto":
                markets = [m for m in markets if any(word in m.get('title', '').lower() 
                          for word in ['bitcoin', 'btc', 'crypto', 'ethereum', 'eth'])]
            elif category == "weather":
                markets = [m for m in markets if any(word in m.get('title', '').lower() 
                          for word in ['temperature', 'weather', 'snow', 'rain', 'hurricane'])]
        
        return markets[:limit]
    
    def get_cache_info(self) -> Dict:
        """Get cache status info"""
        return {
            "total_markets": len(self.markets),
            "last_update": self.last_update,
            "age_seconds": time.time() - self.last_update if self.last_update else 0,
            "updating": self.updating
        }


# Global cache instance
_cache: Optional[SimpleMarketCache] = None

def get_cache() -> Optional[SimpleMarketCache]:
    """Get the global cache instance"""
    return _cache

def set_cache(cache: SimpleMarketCache):
    """Set the global cache instance"""
    global _cache
    _cache = cache