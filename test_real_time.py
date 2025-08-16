#!/usr/bin/env python3
"""
Test Real-time Data Flow
Quick test to verify our bridge is working
"""

import asyncio
import json
import websockets

async def test_real_time_bridge():
    """Test connection to our real-time bridge"""
    uri = "ws://localhost:8001/ws"
    
    print("🧪 Testing Real-time Bridge Connection...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to bridge!")
            
            # Listen for a few messages
            message_count = 0
            start_time = asyncio.get_event_loop().time()
            
            while message_count < 10:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    message_type = data.get("type", "unknown")
                    message_count += 1
                    
                    if message_type == "connected":
                        print(f"📡 {message_count}: Bridge welcome - {data['data']['message']}")
                        print(f"   Kalshi connected: {data['data']['kalshi_connected']}")
                        print(f"   Cached markets: {data['data']['cached_markets']}")
                        
                    elif message_type == "ticker":
                        ticker_data = data["data"]
                        market = ticker_data["market_ticker"]
                        bid = ticker_data["bid"]
                        ask = ticker_data["ask"]
                        price = ticker_data["last_price"]
                        print(f"📊 {message_count}: {market} - Price: {price}¢, Bid: {bid}¢, Ask: {ask}¢")
                        
                    elif message_type == "status":
                        status_data = data["data"]
                        print(f"📢 {message_count}: Status - {status_data['message']}")
                        
                    else:
                        print(f"❓ {message_count}: {message_type}")
                        
                except asyncio.TimeoutError:
                    print("⏰ No message received in 10 seconds")
                    break
            
            elapsed = asyncio.get_event_loop().time() - start_time
            print(f"\n📈 Test Results:")
            print(f"   Messages received: {message_count}")
            print(f"   Time elapsed: {elapsed:.1f} seconds")
            print(f"   Message rate: {message_count/elapsed:.1f} messages/second")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_real_time_bridge())