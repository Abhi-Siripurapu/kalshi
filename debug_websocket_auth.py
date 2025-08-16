#!/usr/bin/env python3
"""
Debug Kalshi WebSocket Authentication
Systematically test different auth variations to find the correct format
"""

import asyncio
import json
import time
import base64
import os
import aiohttp
import websockets
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class AuthDebugger:
    def __init__(self, api_key_id: str, private_key_path: str):
        self.api_key_id = api_key_id
        self.private_key = self._load_private_key(private_key_path)
        
    def _load_private_key(self, key_path: str):
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(), 
                password=None, 
                backend=default_backend()
            )
    
    def _sign_message(self, message: str) -> str:
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
    
    def test_rest_auth(self):
        """Test REST auth that we know works"""
        print("=" * 60)
        print("🔍 Testing REST Authentication (Known Working)")
        print("=" * 60)
        
        timestamp = str(int(time.time() * 1000))
        path = "/trade-api/v2/markets"
        message = f"{timestamp}GET{path}"
        signature = self._sign_message(message)
        
        print(f"📝 REST Auth Details:")
        print(f"   Timestamp: {timestamp} (milliseconds)")
        print(f"   Method: GET")
        print(f"   Path: {path}")
        print(f"   Message: {message}")
        print(f"   Signature: {signature[:50]}...")
        print()
        
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }
    
    def test_websocket_variations(self):
        """Test different WebSocket auth variations"""
        variations = []
        base_timestamp = int(time.time())
        
        print("=" * 60)
        print("🧪 Testing WebSocket Authentication Variations")
        print("=" * 60)
        
        # Variation 1: Milliseconds timestamp (like REST)
        timestamp_ms = str(base_timestamp * 1000)
        message_ms = f"{timestamp_ms}GET/trade-api/ws/v2"
        signature_ms = self._sign_message(message_ms)
        
        variations.append({
            "name": "Milliseconds (like REST)",
            "headers": {
                "KALSHI-ACCESS-KEY": self.api_key_id,
                "KALSHI-ACCESS-SIGNATURE": signature_ms,
                "KALSHI-ACCESS-TIMESTAMP": timestamp_ms
            },
            "details": {
                "timestamp": timestamp_ms,
                "message": message_ms,
                "signature": signature_ms[:50] + "..."
            }
        })
        
        # Variation 2: Seconds timestamp
        timestamp_s = str(base_timestamp)
        message_s = f"{timestamp_s}GET/trade-api/ws/v2"
        signature_s = self._sign_message(message_s)
        
        variations.append({
            "name": "Seconds",
            "headers": {
                "KALSHI-ACCESS-KEY": self.api_key_id,
                "KALSHI-ACCESS-SIGNATURE": signature_s,
                "KALSHI-ACCESS-TIMESTAMP": timestamp_s
            },
            "details": {
                "timestamp": timestamp_s,
                "message": message_s,
                "signature": signature_s[:50] + "..."
            }
        })
        
        # Variation 3: No leading slash
        message_no_slash = f"{timestamp_ms}GETtrade-api/ws/v2"
        signature_no_slash = self._sign_message(message_no_slash)
        
        variations.append({
            "name": "No leading slash",
            "headers": {
                "KALSHI-ACCESS-KEY": self.api_key_id,
                "KALSHI-ACCESS-SIGNATURE": signature_no_slash,
                "KALSHI-ACCESS-TIMESTAMP": timestamp_ms
            },
            "details": {
                "timestamp": timestamp_ms,
                "message": message_no_slash,
                "signature": signature_no_slash[:50] + "..."
            }
        })
        
        # Variation 4: Different path format
        message_alt_path = f"{timestamp_ms}GET/trade-api/ws"
        signature_alt_path = self._sign_message(message_alt_path)
        
        variations.append({
            "name": "Alternative path (/trade-api/ws)",
            "headers": {
                "KALSHI-ACCESS-KEY": self.api_key_id,
                "KALSHI-ACCESS-SIGNATURE": signature_alt_path,
                "KALSHI-ACCESS-TIMESTAMP": timestamp_ms
            },
            "details": {
                "timestamp": timestamp_ms,
                "message": message_alt_path,
                "signature": signature_alt_path[:50] + "..."
            }
        })
        
        # Variation 5: Exact same format as working REST but for WebSocket
        message_exact_rest = f"{timestamp_ms}GET/trade-api/ws/v2"
        signature_exact_rest = self._sign_message(message_exact_rest)
        
        variations.append({
            "name": "Exact REST format for WebSocket",
            "headers": {
                "KALSHI-ACCESS-KEY": self.api_key_id,
                "KALSHI-ACCESS-SIGNATURE": signature_exact_rest,
                "KALSHI-ACCESS-TIMESTAMP": timestamp_ms
            },
            "details": {
                "timestamp": timestamp_ms,
                "message": message_exact_rest,
                "signature": signature_exact_rest[:50] + "..."
            }
        })
        
        # Print all variations
        for i, var in enumerate(variations, 1):
            print(f"🧪 Variation {i}: {var['name']}")
            print(f"   Message: {var['details']['message']}")
            print(f"   Timestamp: {var['details']['timestamp']}")
            print(f"   Signature: {var['details']['signature']}")
            print()
        
        return variations


async def test_rest_api_working():
    """Verify REST API still works with our current auth"""
    print("=" * 60)
    print("✅ Verifying REST API Authentication")
    print("=" * 60)
    
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    debugger = AuthDebugger(api_key, private_key_path)
    headers = debugger.test_rest_auth()
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.elections.kalshi.com/trade-api/v2/markets"
            params = {"limit": 1}
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ REST API Success: {response.status}")
                    print(f"   Got {len(data.get('markets', []))} markets")
                    return True
                else:
                    print(f"❌ REST API Failed: {response.status}")
                    print(f"   Response: {await response.text()}")
                    return False
                    
    except Exception as e:
        print(f"❌ REST API Error: {e}")
        return False


async def test_websocket_variation(variation, urls_to_test):
    """Test a specific WebSocket auth variation"""
    print(f"🔌 Testing: {variation['name']}")
    
    for env_name, ws_url in urls_to_test.items():
        try:
            print(f"   Trying {env_name}: {ws_url}")
            
            websocket = await websockets.connect(
                ws_url,
                additional_headers=variation['headers'],
                ping_interval=30,
                ping_timeout=10
            )
            
            print(f"   ✅ SUCCESS on {env_name}!")
            
            # Send a simple ping to make sure connection works
            ping_message = {"id": 1, "cmd": "ping"}
            await websocket.send(json.dumps(ping_message))
            
            # Wait for response or timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"   📥 Received: {response}")
            except asyncio.TimeoutError:
                print(f"   ⏰ No immediate response (might be normal)")
            
            await websocket.close()
            return True, env_name
            
        except websockets.exceptions.InvalidStatusCode as e:
            status_code = e.status_code
            print(f"   ❌ {env_name}: HTTP {status_code}")
            
        except Exception as e:
            print(f"   ❌ {env_name}: {e}")
    
    return False, None


async def main():
    """Main debug function"""
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    if not api_key:
        print("❌ Error: KALSHI_API_KEY environment variable required")
        return
    
    print("🔐 Kalshi WebSocket Authentication Debugger")
    print(f"🔑 API Key: {api_key}")
    print(f"🗝️  Private Key: {private_key_path}")
    print()
    
    # Step 1: Verify REST API works
    rest_works = await test_rest_api_working()
    if not rest_works:
        print("❌ REST API not working! Fix this first.")
        return
    
    print()
    
    # Step 2: Generate WebSocket variations
    debugger = AuthDebugger(api_key, private_key_path)
    variations = debugger.test_websocket_variations()
    
    # Step 3: Test URLs
    urls_to_test = {
        "Production": "wss://api.elections.kalshi.com/trade-api/ws/v2",
        "Demo": "wss://demo-api.kalshi.co/trade-api/ws/v2"
    }
    
    print("=" * 60)
    print("🧪 Testing WebSocket Variations")
    print("=" * 60)
    
    # Test each variation
    for i, variation in enumerate(variations, 1):
        print(f"\n🔬 Test {i}/{len(variations)}: {variation['name']}")
        print("-" * 40)
        
        success, successful_env = await test_websocket_variation(variation, urls_to_test)
        
        if success:
            print(f"\n🎉 FOUND WORKING COMBINATION!")
            print(f"   Variation: {variation['name']}")
            print(f"   Environment: {successful_env}")
            print(f"   Headers: {json.dumps(variation['headers'], indent=4)}")
            return
    
    print("\n💭 All variations failed. Possible issues:")
    print("   1. Account doesn't have WebSocket permissions")
    print("   2. Different auth method required for WebSockets")
    print("   3. Need to be subscribed to a specific tier")
    print("   4. WebSocket endpoint temporarily down")
    print("   5. Different private key format required")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())