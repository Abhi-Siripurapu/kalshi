#!/usr/bin/env python3
"""
Simple Kalshi REST API Client - Atomic implementation
Only handles basic market data fetching with authentication
"""

import asyncio
import aiohttp
import json
import time
import base64
import os
from typing import Dict, List, Optional
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class SimpleKalshiAuth:
    """Simple authentication handler for Kalshi API"""
    
    def __init__(self, api_key_id: str, private_key_path: str):
        self.api_key_id = api_key_id
        self.private_key = self._load_private_key(private_key_path)
    
    def _load_private_key(self, key_path: str):
        """Load private key from PEM file"""
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(), 
                password=None, 
                backend=default_backend()
            )
    
    def _sign_message(self, message: str) -> str:
        """Sign message with private key"""
        message_bytes = message.encode('utf-8')
        signature = self.private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    
    def create_headers(self, method: str, path: str) -> Dict[str, str]:
        """Create authentication headers for REST API"""
        timestamp = str(int(time.time() * 1000))  # milliseconds
        message = f"{timestamp}{method}{path.split('?')[0]}"
        signature = self._sign_message(message)
        
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }


class SimpleKalshiClient:
    """Simple Kalshi REST API client"""
    
    def __init__(self, api_key_id: str, private_key_path: str):
        self.auth = SimpleKalshiAuth(api_key_id, private_key_path)
        self.base_url = "https://api.elections.kalshi.com"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_markets(self, limit: int = 100, status: str = "open") -> Dict:
        """Get markets from Kalshi API"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")
        
        path = "/trade-api/v2/markets"
        url = f"{self.base_url}{path}"
        params = {"limit": limit, "status": status}
        
        headers = self.auth.create_headers("GET", path)
        
        async with self.session.get(url, params=params, headers=headers) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_market(self, ticker: str) -> Optional[Dict]:
        """Get specific market by ticker"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")
        
        path = f"/trade-api/v2/markets/{ticker}"
        url = f"{self.base_url}{path}"
        
        headers = self.auth.create_headers("GET", path)
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("market")
                return None
        except Exception as e:
            print(f"Error fetching market {ticker}: {e}")
            return None
    
    async def get_candlesticks(self, ticker: str, period_interval: int = 60, 
                              start_ts: int = None, end_ts: int = None) -> Optional[Dict]:
        """Get candlestick data for a market
        
        Args:
            ticker: Market ticker
            period_interval: Time period in minutes (1, 60, or 1440)
            start_ts: Start timestamp (Unix)
            end_ts: End timestamp (Unix)
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")
        
        # Extract series ticker from market ticker (everything before the last dash)
        parts = ticker.split('-')
        if len(parts) < 2:
            return None
        series_ticker = '-'.join(parts[:-1])
        
        path = f"/trade-api/v2/series/{series_ticker}/markets/{ticker}/candlesticks"
        url = f"{self.base_url}{path}"
        
        params = {
            "period_interval": period_interval,
        }
        
        if start_ts:
            params["start_ts"] = start_ts
        if end_ts:
            params["end_ts"] = end_ts
        
        headers = self.auth.create_headers("GET", path)
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Candlesticks API error {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            print(f"Error getting candlesticks for {ticker}: {e}")
            return None
    
    async def get_orderbook(self, ticker: str, depth: int = 10) -> Optional[Dict]:
        """Get orderbook for a market"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")
        
        path = f"/trade-api/v2/markets/{ticker}/orderbook"
        url = f"{self.base_url}{path}"
        params = {"depth": depth}
        
        headers = self.auth.create_headers("GET", path)
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("orderbook")
        except Exception as e:
            print(f"Error fetching orderbook for {ticker}: {e}")
            return None


async def test_client():
    """Test the simple client"""
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    if not api_key:
        print("Error: KALSHI_API_KEY environment variable required")
        return
    
    print("Testing Simple Kalshi Client...")
    
    async with SimpleKalshiClient(api_key, private_key_path) as client:
        try:
            # Test getting markets
            print("\n1. Fetching markets...")
            markets_data = await client.get_markets(limit=5)
            markets = markets_data.get("markets", [])
            print(f"Found {len(markets)} markets")
            
            if markets:
                # Show first market
                market = markets[0]
                ticker = market["ticker"]
                title = market.get("title", "No title")
                print(f"First market: {ticker} - {title}")
                
                # Test getting specific market
                print(f"\n2. Fetching market details for {ticker}...")
                market_detail = await client.get_market(ticker)
                if market_detail:
                    print(f"Market detail: {market_detail.get('title', 'No title')}")
                
                # Test getting orderbook
                print(f"\n3. Fetching orderbook for {ticker}...")
                orderbook = await client.get_orderbook(ticker)
                if orderbook:
                    yes_bids = orderbook.get("yes", []) or []
                    no_bids = orderbook.get("no", []) or []
                    print(f"Orderbook - YES bids: {len(yes_bids)}, NO bids: {len(no_bids)}")
                    if yes_bids:
                        print(f"Best YES bid: {yes_bids[0]} cents")
                    if no_bids:
                        print(f"Best NO bid: {no_bids[0]} cents")
                else:
                    print("No orderbook data returned")
        
        except Exception as e:
            print(f"Error during testing: {e}")
    
    print("\nClient test completed!")


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_client())