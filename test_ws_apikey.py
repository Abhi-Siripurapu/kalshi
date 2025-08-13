#!/usr/bin/env python3
"""
Test WebSocket with API key authentication as mentioned in docs
"""

import asyncio
import json
import websockets

API_KEY = "6d7e4138-afce-47a3-ace2-495d6d801410"
WS_URL = "wss://demo-api.kalshi.co"  # Base URL from docs

async def test_websocket_apikey():
    """Test WebSocket with API key in handshake"""
    
    print("🧪 Testing WebSocket with API key authentication...")
    print(f"   API Key: {API_KEY}")
    print(f"   URL: {WS_URL}")
    
    # Try different approaches based on the docs
    approaches = [
        # Approach 1: API key in headers
        {
            "url": WS_URL,
            "extra_headers": {"Authorization": f"Bearer {API_KEY}"},
            "name": "Authorization header"
        },
        # Approach 2: API key in query params  
        {
            "url": f"{WS_URL}?api_key={API_KEY}",
            "extra_headers": {},
            "name": "Query parameter"
        },
        # Approach 3: Custom header
        {
            "url": WS_URL,
            "extra_headers": {"KALSHI-ACCESS-KEY": API_KEY},
            "name": "Custom header"
        }
    ]
    
    for approach in approaches:
        print(f"\n🔌 Trying {approach['name']}...")
        try:
            headers = approach["extra_headers"] if approach["extra_headers"] else None
            
            async with websockets.connect(
                approach["url"], 
                additional_headers=headers
            ) as websocket:
                print(f"✅ Connected with {approach['name']}!")
                
                # Try to subscribe to ticker updates
                subscribe_msg = {
                    "cmd": "subscribe",
                    "params": {
                        "channels": ["ticker"]
                    }
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                print("📡 Sent subscription request")
                
                # Listen for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"📩 Received: {response}")
                    return True
                except asyncio.TimeoutError:
                    print("⏰ No response within 5 seconds")
                    return True  # Connection worked even if no immediate response
                    
        except Exception as e:
            print(f"❌ Failed with {approach['name']}: {e}")
    
    print("\n❌ All WebSocket approaches failed")
    return False

if __name__ == "__main__":
    asyncio.run(test_websocket_apikey())