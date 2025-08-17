#!/usr/bin/env python3
"""
Real-time Kalshi Bridge
Connects real Kalshi WebSocket data to our UI WebSocket server
"""

import asyncio
import json
import time
import logging
import os
from typing import Set, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import our working Kalshi WebSocket client
from simple_websocket_client import SimpleKalshiWebSocketClient

app = FastAPI(title="Real-time Kalshi Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
ui_connections: Set[WebSocket] = set()
kalshi_client: Optional[SimpleKalshiWebSocketClient] = None
latest_data: Dict[str, Dict] = {}  # Cache latest data by market ticker

class KalshiDataBridge:
    """Bridge that connects Kalshi WebSocket to UI clients"""
    
    def __init__(self):
        self.running = False
        self.kalshi_client = None
        self.connection_healthy = False
    
    async def start(self):
        """Start the bridge"""
        print("🌉 Starting Kalshi Data Bridge...")
        self.running = True
        
        # Get credentials
        api_key = os.getenv("KALSHI_API_KEY")
        private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "../kalshi-key.pem")
        
        if not api_key:
            print("❌ Error: KALSHI_API_KEY environment variable required")
            return
        
        # Create Kalshi client
        self.kalshi_client = SimpleKalshiWebSocketClient(api_key, private_key_path)
        
        # Set up callbacks
        self.kalshi_client.on_connected = self._on_kalshi_connected
        self.kalshi_client.on_message = self._on_kalshi_message
        self.kalshi_client.on_disconnected = self._on_kalshi_disconnected
        self.kalshi_client.on_error = self._on_kalshi_error
        
        # Start connection loop
        while self.running:
            try:
                print("🔌 Connecting to Kalshi WebSocket...")
                connected = await self.kalshi_client.connect()
                
                if connected:
                    print("✅ Connected to Kalshi! Starting message listener...")
                    await self.kalshi_client.listen()
                else:
                    print("❌ Failed to connect to Kalshi")
                
            except Exception as e:
                print(f"💥 Bridge error: {e}")
                self.connection_healthy = False
                await self._broadcast_status("error", f"Bridge error: {e}")
            
            if self.running:
                print("🔄 Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the bridge"""
        print("🛑 Stopping bridge...")
        self.running = False
        if self.kalshi_client:
            await self.kalshi_client.disconnect()
    
    async def _on_kalshi_connected(self):
        """Called when Kalshi WebSocket connects"""
        print("🎉 Kalshi WebSocket connected!")
        self.connection_healthy = True
        
        # Subscribe to ticker updates for all markets
        await self.kalshi_client.subscribe_to_ticker()
        
        # Broadcast connection status to UI clients
        await self._broadcast_status("connected", "Connected to Kalshi real-time data")
    
    async def _on_kalshi_disconnected(self):
        """Called when Kalshi WebSocket disconnects"""
        print("👋 Kalshi WebSocket disconnected")
        self.connection_healthy = False
        await self._broadcast_status("disconnected", "Lost connection to Kalshi")
    
    async def _on_kalshi_error(self, error):
        """Called when Kalshi WebSocket error occurs"""
        print(f"💥 Kalshi WebSocket error: {error}")
        self.connection_healthy = False
        await self._broadcast_status("error", f"Kalshi error: {error}")
    
    async def _on_kalshi_message(self, data):
        """Called when we receive a message from Kalshi"""
        try:
            msg_type = data.get("type")
            
            if msg_type == "ticker":
                await self._handle_ticker_update(data)
            elif msg_type == "orderbook_snapshot":
                await self._handle_orderbook_snapshot(data)
            elif msg_type == "orderbook_delta":
                await self._handle_orderbook_delta(data)
            elif msg_type == "subscribed":
                print(f"✅ Subscription confirmed: {data}")
            elif msg_type == "error":
                error_msg = data.get('msg', {})
                print(f"❌ Kalshi error: {error_msg}")
            else:
                print(f"📥 Kalshi message: {msg_type}")
                
        except Exception as e:
            print(f"Error handling Kalshi message: {e}")
    
    async def _handle_ticker_update(self, data):
        """Handle ticker update from Kalshi and forward to UI"""
        try:
            ticker_data = data.get('msg', {})
            market_ticker = ticker_data.get('market_ticker', '')
            
            if not market_ticker:
                return
            
            # Convert Kalshi format to our UI format
            ui_message = {
                "type": "ticker",
                "data": {
                    "market_ticker": market_ticker,
                    "bid": ticker_data.get('yes_bid', 0),
                    "ask": ticker_data.get('yes_ask', 0),
                    "last_price": ticker_data.get('price', 0),
                    "volume_24h": ticker_data.get('volume', 0),
                    "open_interest": ticker_data.get('open_interest', 0),
                    "ts": ticker_data.get('ts', int(time.time()))
                }
            }
            
            # Cache the latest data
            latest_data[market_ticker] = ui_message["data"]
            
            # Broadcast to all UI clients
            await self._broadcast_to_ui(ui_message)
            
        except Exception as e:
            print(f"Error handling ticker update: {e}")
    
    async def _handle_orderbook_snapshot(self, data):
        """Handle orderbook snapshot from Kalshi and forward to UI"""
        try:
            orderbook_data = data.get('msg', {})
            market_ticker = orderbook_data.get('market_ticker', '')
            
            if not market_ticker:
                return
            
            # Convert Kalshi orderbook format to our UI format
            ui_message = {
                "type": "orderbook_snapshot",
                "data": {
                    "market_ticker": market_ticker,
                    "yes": orderbook_data.get('yes', []),
                    "no": orderbook_data.get('no', []),
                    "ts": orderbook_data.get('ts', int(time.time()))
                }
            }
            
            # Broadcast to all UI clients
            await self._broadcast_to_ui(ui_message)
            print(f"📋 Orderbook snapshot for {market_ticker}")
            
        except Exception as e:
            print(f"Error handling orderbook snapshot: {e}")
    
    async def _handle_orderbook_delta(self, data):
        """Handle orderbook delta from Kalshi and forward to UI"""
        try:
            orderbook_data = data.get('msg', {})
            market_ticker = orderbook_data.get('market_ticker', '')
            
            if not market_ticker:
                return
            
            # Convert Kalshi orderbook delta format to our UI format
            ui_message = {
                "type": "orderbook_delta",
                "data": {
                    "market_ticker": market_ticker,
                    "yes": orderbook_data.get('yes', []),
                    "no": orderbook_data.get('no', []),
                    "ts": orderbook_data.get('ts', int(time.time()))
                }
            }
            
            # Broadcast to all UI clients
            await self._broadcast_to_ui(ui_message)
            print(f"📈 Orderbook delta for {market_ticker}")
            
        except Exception as e:
            print(f"Error handling orderbook delta: {e}")
    
    async def _broadcast_status(self, status: str, message: str):
        """Broadcast status update to UI clients"""
        status_message = {
            "type": "status",
            "data": {
                "status": status,
                "message": message,
                "timestamp": time.time(),
                "kalshi_connected": self.connection_healthy
            }
        }
        await self._broadcast_to_ui(status_message)
    
    async def _broadcast_to_ui(self, message: Dict):
        """Broadcast message to all UI WebSocket clients"""
        if not ui_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for websocket in ui_connections.copy():
            try:
                await websocket.send_text(message_str)
            except Exception:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            ui_connections.discard(websocket)

# Global bridge instance
bridge = KalshiDataBridge()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for UI clients"""
    await websocket.accept()
    ui_connections.add(websocket)
    
    print(f"📱 UI client connected. Total connections: {len(ui_connections)}")
    
    # Send welcome message with current status
    welcome = {
        "type": "connected",
        "data": {
            "message": "Connected to Real-time Kalshi Bridge",
            "kalshi_connected": bridge.connection_healthy,
            "cached_markets": len(latest_data)
        }
    }
    await websocket.send_text(json.dumps(welcome))
    
    # Send any cached data
    for market_ticker, data in latest_data.items():
        cached_message = {
            "type": "ticker",
            "data": data
        }
        try:
            await websocket.send_text(json.dumps(cached_message))
        except Exception:
            break
    
    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle subscription requests
                if message.get("type") == "subscribe":
                    channels = message.get("channels", [])
                    market_ticker = message.get("market_ticker")
                    
                    # Handle orderbook subscriptions for specific markets
                    if "orderbook" in channels and market_ticker:
                        if bridge.kalshi_client:
                            try:
                                await bridge.kalshi_client.subscribe_to_orderbook([market_ticker])
                                print(f"📋 Subscribed to orderbook for {market_ticker}")
                            except Exception as e:
                                print(f"❌ Failed to subscribe to orderbook for {market_ticker}: {e}")
                    
                    # Send subscription confirmation
                    response = {
                        "type": "subscribed",
                        "data": {
                            "channels": channels,
                            "market_ticker": market_ticker,
                            "message": f"Subscribed to {channels} for {market_ticker if market_ticker else 'all markets'}"
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    print(f"📋 UI client subscribed to: {channels} for {market_ticker if market_ticker else 'all markets'}")
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error handling UI WebSocket message: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        ui_connections.discard(websocket)
        print(f"📤 UI client disconnected. Total connections: {len(ui_connections)}")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Real-time Kalshi Bridge",
        "version": "1.0.0",
        "websocket_endpoint": "/ws",
        "ui_connections": len(ui_connections),
        "kalshi_connected": bridge.connection_healthy,
        "cached_markets": len(latest_data)
    }

@app.on_event("startup")
async def startup_event():
    """Start the bridge on server startup"""
    print("🚀 Starting Real-time Kalshi Bridge server...")
    
    # Start the bridge in background
    asyncio.create_task(bridge.start())
    
    print("✅ Bridge server ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the bridge on server shutdown"""
    await bridge.stop()

if __name__ == "__main__":
    # Load environment from parent directory
    from dotenv import load_dotenv
    load_dotenv("../.env")
    
    print("🌉 Starting Real-time Kalshi Bridge on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")