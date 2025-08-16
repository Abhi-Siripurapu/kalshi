#!/usr/bin/env python3
"""
Simple Kalshi WebSocket Client - Atomic implementation
Only handles WebSocket connection and basic subscriptions
"""

import asyncio
import json
import time
import base64
import os
import websockets
from typing import Optional, Callable
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class SimpleKalshiWebSocketAuth:
    """Simple WebSocket authentication for Kalshi"""
    
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
    
    def create_ws_headers(self) -> dict:
        """Create WebSocket authentication headers"""
        # WebSocket uses SECONDS timestamp (different from REST API which uses milliseconds!)
        timestamp = str(int(time.time()))
        message = f"{timestamp}GET/trade-api/ws/v2"
        signature = self._sign_message(message)
        
        print(f"🔐 WebSocket Auth (SECONDS format):")
        print(f"  Timestamp: {timestamp}")
        print(f"  Message: {message}")
        print(f"  API Key: {self.api_key_id}")
        print(f"  Signature: {signature[:50]}...")
        
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp
        }


class SimpleKalshiWebSocketClient:
    """Minimal WebSocket client for Kalshi real-time data"""
    
    def __init__(self, api_key_id: str, private_key_path: str):
        self.auth = SimpleKalshiWebSocketAuth(api_key_id, private_key_path)
        self.ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.message_id = 1
        self.subscriptions = []
        
        # Callbacks
        self.on_message: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    async def connect(self) -> bool:
        """Connect to Kalshi WebSocket"""
        try:
            headers = self.auth.create_ws_headers()
            print(f"Connecting to Kalshi WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            print("✅ WebSocket connected successfully")
            
            if self.on_connected:
                await self.on_connected()
            
            return True
            
        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            if self.on_error:
                await self.on_error(e)
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
            if self.on_disconnected:
                await self.on_disconnected()
    
    async def send_message(self, message: dict):
        """Send message to WebSocket"""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        message["id"] = self.message_id
        self.message_id += 1
        
        message_str = json.dumps(message)
        print(f"📤 Sending: {message_str}")
        
        await self.websocket.send(message_str)
    
    async def subscribe_to_orderbook(self, market_tickers: list):
        """Subscribe to orderbook updates for specific markets"""
        subscription = {
            "cmd": "subscribe",
            "params": {
                "channels": ["orderbook"],
                "market_tickers": market_tickers
            }
        }
        
        await self.send_message(subscription)
        self.subscriptions.append(("orderbook", market_tickers))
        print(f"📋 Subscribed to orderbook updates for {market_tickers}")
    
    async def subscribe_to_trades(self, market_tickers: list):
        """Subscribe to trade updates for specific markets"""
        subscription = {
            "cmd": "subscribe",
            "params": {
                "channels": ["trades"],
                "market_tickers": market_tickers
            }
        }
        
        await self.send_message(subscription)
        self.subscriptions.append(("trades", market_tickers))
        print(f"📈 Subscribed to trades for {market_tickers}")
    
    async def subscribe_to_ticker(self):
        """Subscribe to ticker updates for all markets"""
        subscription = {
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }
        
        await self.send_message(subscription)
        self.subscriptions.append(("ticker", "all"))
        print(f"📊 Subscribed to ticker updates for all markets")
    
    async def listen(self):
        """Listen for WebSocket messages"""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        print("👂 Listening for messages...")
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    print(f"📥 Received: {json.dumps(data, indent=2)}")
                    
                    if self.on_message:
                        await self.on_message(data)
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON received: {message}, error: {e}")
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
            if self.on_disconnected:
                await self.on_disconnected()
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            if self.on_error:
                await self.on_error(e)


async def test_websocket_client():
    """Test the WebSocket client with real Kalshi data"""
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    if not api_key:
        print("❌ Error: KALSHI_API_KEY environment variable required")
        return
    
    print("🧪 Testing Simple Kalshi WebSocket Client...")
    
    # Create client
    client = SimpleKalshiWebSocketClient(api_key, private_key_path)
    
    # Set up callbacks
    async def on_connected():
        print("🎉 Connected! Now subscribing to markets...")
        
        # Subscribe to ticker updates for all markets
        await client.subscribe_to_ticker()
    
    async def on_message(data):
        msg_type = data.get("type", "unknown")
        if msg_type == "subscribed":
            print(f"✅ Subscription confirmed: {data}")
        elif msg_type == "ticker":
            ticker_data = data.get('msg', {})
            market_ticker = ticker_data.get('market_ticker', 'Unknown')
            price = ticker_data.get('price', 0)
            yes_bid = ticker_data.get('yes_bid', 0)
            yes_ask = ticker_data.get('yes_ask', 0)
            print(f"📊 Ticker {market_ticker}: Price={price}¢, Bid={yes_bid}¢, Ask={yes_ask}¢")
        elif msg_type == "orderbook_delta":
            print(f"📋 Orderbook update: {data.get('msg', {})}")
        elif msg_type == "trade":
            print(f"💰 Trade: {data.get('msg', {})}")
        elif msg_type == "orderbook_snapshot":
            print(f"📷 Orderbook snapshot: {data.get('msg', {})}")
        elif msg_type == "error":
            error_msg = data.get('msg', {})
            print(f"❌ Error: {error_msg}")
        else:
            print(f"❓ Unknown message type: {msg_type}")
    
    async def on_disconnected():
        print("👋 Disconnected from WebSocket")
    
    async def on_error(error):
        print(f"💥 WebSocket error: {error}")
    
    # Set callbacks
    client.on_connected = on_connected
    client.on_message = on_message
    client.on_disconnected = on_disconnected
    client.on_error = on_error
    
    try:
        # Connect
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect, exiting")
            return
        
        # Listen for messages for 30 seconds
        print("⏰ Listening for 30 seconds...")
        await asyncio.wait_for(client.listen(), timeout=30.0)
        
    except asyncio.TimeoutError:
        print("⏰ Test completed after 30 seconds")
    except KeyboardInterrupt:
        print("⌨️  Test interrupted by user")
    finally:
        await client.disconnect()
        print("🔚 Test finished")


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_websocket_client())