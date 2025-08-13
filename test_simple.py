#!/usr/bin/env python3
"""
Simplified test to just verify Kalshi connection works
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adapters.kalshi.client import KalshiClient

load_dotenv()

async def test_kalshi_connection():
    """Test basic Kalshi API connection"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Get configuration
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    print("🧪 Testing Kalshi Connection...")
    print(f"   API Key: {api_key}")
    print(f"   Private Key: {private_key_path}")
    
    async with KalshiClient(api_key, private_key_path) as client:
        
        # Test 1: Get a few markets
        print("\n📊 Testing market discovery...")
        try:
            markets = await client.get_markets(limit=5, status="open")
            print(f"✅ Found {len(markets['markets'])} markets")
            
            for market in markets['markets'][:3]:
                print(f"   - {market['ticker']}: {market['title']}")
                
        except Exception as e:
            print(f"❌ Market discovery failed: {e}")
            return
        
        # Test 2: Get orderbook for first market
        if markets['markets']:
            market_ticker = markets['markets'][0]['ticker']
            print(f"\n📖 Testing orderbook for {market_ticker}...")
            try:
                orderbook = await client.get_orderbook(market_ticker)
                yes_bids = orderbook['orderbook']['yes']
                no_bids = orderbook['orderbook']['no']
                print(f"✅ Orderbook retrieved")
                print(f"   YES bids: {len(yes_bids)} levels")
                print(f"   NO bids: {len(no_bids)} levels")
                
                if yes_bids:
                    best_yes_bid = yes_bids[-1][0]  # Last element is highest
                    print(f"   Best YES bid: {best_yes_bid}¢")
                    
            except Exception as e:
                print(f"❌ Orderbook failed: {e}")
                return
        
        # Test 3: WebSocket connection (brief)
        print(f"\n🔌 Testing WebSocket connection...")
        try:
            connected = await client.connect_websocket()
            if connected:
                print("✅ WebSocket connected successfully")
                
                # Subscribe to one market
                if markets['markets']:
                    test_market = markets['markets'][0]['ticker']
                    await client.subscribe_to_orderbooks([test_market])
                    print(f"✅ Subscribed to {test_market}")
                    
                    # Listen for a few messages
                    message_count = 0
                    async for message in client.websocket:
                        print(f"📩 Received: {message[:100]}...")
                        message_count += 1
                        if message_count >= 3:  # Stop after 3 messages
                            break
                            
            else:
                print("❌ WebSocket connection failed")
                
        except Exception as e:
            print(f"❌ WebSocket test failed: {e}")
    
    print("\n🎉 Kalshi connection test completed!")

if __name__ == "__main__":
    asyncio.run(test_kalshi_connection())