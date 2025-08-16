#!/usr/bin/env python3
"""
Simple WebSocket Server for Real-time Mock Data
Provides real-time updates using mock data while we resolve Kalshi WebSocket auth
"""

import asyncio
import json
import time
import random
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Simple WebSocket Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
websocket_connections: Set[WebSocket] = set()
mock_markets = [
    "KXAPRPOTUS-25AUG22-46.5",
    "KXAPRPOTUS-25AUG22-46.3", 
    "KXAPRPOTUS-25AUG22-45.8"
]

async def generate_mock_ticker_update():
    """Generate realistic mock ticker update"""
    market = random.choice(mock_markets)
    
    # Generate realistic bid/ask prices
    base_price = 45 + random.randint(0, 20)
    spread = random.randint(1, 5)
    
    bid = base_price
    ask = base_price + spread
    
    return {
        "type": "ticker",
        "data": {
            "market_ticker": market,
            "bid": bid,
            "ask": ask,
            "last_price": bid + (spread // 2),
            "volume_24h": random.randint(1000, 10000),
            "ts": int(time.time() * 1000)
        }
    }

async def generate_mock_orderbook_update():
    """Generate realistic mock orderbook update"""
    market = random.choice(mock_markets)
    
    # Generate some bid/ask levels
    base_price = 45 + random.randint(0, 20)
    
    yes_bids = []
    for i in range(5):
        price = max(1, base_price - i)
        qty = random.randint(50, 500)
        yes_bids.append([price, qty])
    
    no_bids = []
    for i in range(5):
        price = max(1, 100 - base_price - i)
        qty = random.randint(50, 500)  
        no_bids.append([price, qty])
    
    return {
        "type": "orderbook_snapshot",
        "data": {
            "market_ticker": market,
            "yes": yes_bids,
            "no": no_bids,
            "ts": int(time.time() * 1000)
        }
    }

async def generate_mock_trade():
    """Generate realistic mock trade"""
    market = random.choice(mock_markets)
    
    return {
        "type": "trade",
        "data": {
            "market_ticker": market,
            "yes_price": random.randint(40, 60),
            "no_price": random.randint(40, 60),
            "count": random.randint(1, 10),
            "taker_side": random.choice(["yes", "no"]),
            "ts": int(time.time() * 1000)
        }
    }

async def broadcast_to_all(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    message_str = json.dumps(message)
    disconnected = []
    
    for websocket in websocket_connections.copy():
        try:
            await websocket.send_text(message_str)
        except Exception:
            disconnected.append(websocket)
    
    # Remove disconnected clients
    for websocket in disconnected:
        websocket_connections.discard(websocket)

async def mock_data_generator():
    """Background task to generate mock real-time data"""
    print("🔄 Starting mock data generator...")
    
    while True:
        try:
            # Generate different types of updates
            update_type = random.choices(
                ["ticker", "orderbook", "trade"],
                weights=[0.5, 0.3, 0.2]
            )[0]
            
            if update_type == "ticker":
                message = await generate_mock_ticker_update()
            elif update_type == "orderbook":
                message = await generate_mock_orderbook_update()
            else:
                message = await generate_mock_trade()
            
            await broadcast_to_all(message)
            
            # Random delay between updates (1-5 seconds)
            await asyncio.sleep(random.uniform(1.0, 5.0))
            
        except Exception as e:
            print(f"Error in mock data generator: {e}")
            await asyncio.sleep(1.0)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket.accept()
    websocket_connections.add(websocket)
    
    print(f"📡 Client connected. Total connections: {len(websocket_connections)}")
    
    # Send welcome message
    welcome = {
        "type": "connected",
        "data": {
            "message": "Connected to Simple WebSocket Server",
            "mock_mode": True,
            "available_markets": mock_markets
        }
    }
    await websocket.send_text(json.dumps(welcome))
    
    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (subscriptions, etc.)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle subscription requests
                if message.get("type") == "subscribe":
                    channels = message.get("channels", [])
                    
                    # Send subscription confirmation
                    response = {
                        "type": "subscribed",
                        "data": {
                            "channels": channels,
                            "message": f"Subscribed to {channels}"
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    
                    print(f"📋 Client subscribed to: {channels}")
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error handling WebSocket message: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        websocket_connections.discard(websocket)
        print(f"📤 Client disconnected. Total connections: {len(websocket_connections)}")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Simple WebSocket Server",
        "version": "1.0.0",
        "websocket_endpoint": "/ws",
        "connected_clients": len(websocket_connections),
        "mock_markets": mock_markets
    }

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    print("🚀 Starting Simple WebSocket Server...")
    
    # Start mock data generator
    asyncio.create_task(mock_data_generator())
    
    print("✅ WebSocket server ready")

if __name__ == "__main__":
    print("🔌 Starting Simple WebSocket Server on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")