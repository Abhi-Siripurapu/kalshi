#!/usr/bin/env python3
"""
Standalone WebSocket test for Kalshi - isolate and fix the core WebSocket issue
"""
import asyncio
import json
import logging
import os
import sys
import time
import websockets
from adapters.kalshi.auth import KalshiAuth

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KalshiWebSocketTest:
    def __init__(self, api_key_id: str, private_key_path: str):
        self.auth = KalshiAuth(api_key_id, private_key_path)
        self.ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
        self.websocket = None
        self.message_id = 1
        self.received_messages = []
        
    async def connect(self):
        """Test basic WebSocket connection with auth"""
        try:
            # Generate auth headers
            headers = self.auth.create_ws_headers()
            logger.info(f"Connecting to: {self.ws_url}")
            logger.info(f"Auth headers: {list(headers.keys())}")
            
            # Connect
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            logger.info("✅ WebSocket connected successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            return False
    
    async def test_basic_subscription(self):
        """Test subscribing to a simple ticker channel"""
        if not self.websocket:
            logger.error("Not connected")
            return False
            
        try:
            # Subscribe to ticker updates (simplest channel)
            subscription = {
                "id": self.message_id,
                "cmd": "subscribe", 
                "params": {
                    "channels": ["ticker"]
                }
            }
            
            logger.info(f"Sending subscription: {subscription}")
            await self.websocket.send(json.dumps(subscription))
            self.message_id += 1
            
            # Wait for response
            logger.info("Waiting for subscription response...")
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            response_data = json.loads(response)
            logger.info(f"✅ Received response: {response_data}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Subscription test failed: {e}")
            return False
    
    async def test_market_subscription(self):
        """Test subscribing to orderbook for a specific market"""
        if not self.websocket:
            logger.error("Not connected")
            return False
            
        try:
            # Try subscribing to orderbook_delta for a single market
            test_market = "KXUSAINTEL-25"  # Use a simple market
            
            subscription = {
                "id": self.message_id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_ticker": test_market
                }
            }
            
            logger.info(f"Sending market subscription: {subscription}")
            await self.websocket.send(json.dumps(subscription))
            self.message_id += 1
            
            # Wait for response
            logger.info("Waiting for market subscription response...")
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            response_data = json.loads(response)
            logger.info(f"✅ Received market response: {response_data}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Market subscription test failed: {e}")
            return False
    
    async def listen_for_messages(self, duration=30):
        """Listen for incoming messages"""
        if not self.websocket:
            logger.error("Not connected")
            return
            
        logger.info(f"Listening for messages for {duration} seconds...")
        start_time = time.time()
        message_count = 0
        
        try:
            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=5)
                    message_data = json.loads(message)
                    message_count += 1
                    
                    msg_type = message_data.get("type", "unknown")
                    logger.info(f"📨 Message #{message_count} - Type: {msg_type}")
                    
                    if msg_type in ["orderbook_snapshot", "orderbook_delta"]:
                        market = message_data.get("msg", {}).get("market_ticker", "unknown")
                        logger.info(f"    Market: {market}")
                    elif msg_type == "error":
                        logger.error(f"    Error: {message_data}")
                    else:
                        logger.info(f"    Data: {str(message_data)[:100]}...")
                        
                    self.received_messages.append(message_data)
                    
                except asyncio.TimeoutError:
                    logger.info("No message received in 5s, continuing...")
                    continue
                    
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
        
        logger.info(f"📊 Total messages received: {message_count}")
        return message_count > 0
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket closed")

async def main():
    """Run the standalone WebSocket test"""
    # Get credentials
    api_key = os.getenv("KALSHI_API_KEY", "6d7e4138-afce-47a3-ace2-495d6d801410")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    if not api_key:
        logger.error("KALSHI_API_KEY not found")
        return
    
    logger.info("🧪 Starting Kalshi WebSocket Test")
    logger.info("=" * 50)
    
    test = KalshiWebSocketTest(api_key, private_key_path)
    
    try:
        # Test 1: Basic connection
        logger.info("🔌 Test 1: Basic WebSocket Connection")
        connected = await test.connect()
        if not connected:
            logger.error("❌ Basic connection failed - aborting")
            return
        
        # Test 2: Simple subscription (ticker)
        logger.info("\n📡 Test 2: Simple Ticker Subscription")
        ticker_success = await test.test_basic_subscription()
        
        # Test 3: Market-specific subscription
        logger.info("\n📈 Test 3: Market Orderbook Subscription")
        market_success = await test.test_market_subscription()
        
        # Test 4: Listen for live data
        logger.info("\n👂 Test 4: Listen for Live Data")
        received_data = await test.listen_for_messages(20)
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("🏁 TEST RESULTS:")
        logger.info(f"   Basic Connection: {'✅' if connected else '❌'}")
        logger.info(f"   Ticker Subscription: {'✅' if ticker_success else '❌'}")
        logger.info(f"   Market Subscription: {'✅' if market_success else '❌'}")
        logger.info(f"   Received Live Data: {'✅' if received_data else '❌'}")
        
        if received_data:
            logger.info("🎉 WebSocket is working! Ready to integrate.")
        else:
            logger.error("❌ WebSocket issues found - needs debugging")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await test.close()

if __name__ == "__main__":
    asyncio.run(main())