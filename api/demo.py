#!/usr/bin/env python3
"""
Simplified API for demo without Redis dependency
"""

import asyncio
import json
import time
import random
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kalshi Terminal Demo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
websocket_connections: List[WebSocket] = []

# Sample markets and books
SAMPLE_MARKETS = [
    {
        "id": "BIDEN25",
        "title": "Will Biden be re-elected in 2025?",
        "yes_bid": 45,
        "yes_ask": 48,
        "no_bid": 52,
        "no_ask": 55
    },
    {
        "id": "TRUMP25", 
        "title": "Will Trump win in 2025?",
        "yes_bid": 42,
        "yes_ask": 45,
        "no_bid": 55,
        "no_ask": 58
    },
    {
        "id": "HOUSE25",
        "title": "Will Republicans control House in 2025?",
        "yes_bid": 58,
        "yes_ask": 61,
        "no_bid": 39,
        "no_ask": 42
    }
]

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "kalshi-terminal-demo-api"}

@app.get("/status")
async def get_status():
    """Get system status"""
    return {
        "timestamp": time.time(),
        "venues": {
            "kalshi": {
                "status": "connected",
                "latency_p50_ms": 45.2,
                "latency_p95_ms": 89.1,
                "subscribed_markets": 3,
                "stale_markets": 0
            }
        },
        "api_status": "healthy",
        "redis_connected": True  # Fake for demo
    }

@app.get("/books")
async def get_books():
    """Get current book data"""
    books = {}
    
    for market in SAMPLE_MARKETS:
        for outcome in ["yes", "no"]:
            if outcome == "yes":
                bids = [{"px_cents": market["yes_bid"], "qty": random.randint(100, 500)}]
                asks = [{"px_cents": market["yes_ask"], "qty": random.randint(100, 500)}]
                best_bid = market["yes_bid"]
                best_ask = market["yes_ask"]
            else:
                bids = [{"px_cents": market["no_bid"], "qty": random.randint(100, 500)}]  
                asks = [{"px_cents": market["no_ask"], "qty": random.randint(100, 500)}]
                best_bid = market["no_bid"]
                best_ask = market["no_ask"]
            
            key = f"{market['id']}_{outcome}"
            books[key] = {
                "ts_ns": time.time_ns(),
                "bids": bids,
                "asks": asks,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid_px": (best_bid + best_ask) / 2,
                "stored_at": time.time() * 1000  # milliseconds
            }
    
    return {"books": books}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": {
                "timestamp": time.time(),
                "venues": {
                    "kalshi": {
                        "status": "healthy",
                        "latency_p50_ms": 45.2,
                        "latency_p95_ms": 89.1,
                        "subscribed_markets": 3,
                        "stale_markets": 0
                    }
                },
                "api_status": "healthy", 
                "redis_connected": True
            }
        }))
        
        # Simulate some live events
        event_count = 0
        while True:
            try:
                # Wait for client messages or send periodic updates
                await asyncio.sleep(2)
                
                # Send a mock event every few seconds
                event_count += 1
                
                if event_count % 3 == 0:
                    # Send book snapshot event
                    market = random.choice(SAMPLE_MARKETS)
                    await websocket.send_text(json.dumps({
                        "type": "event",
                        "data": {
                            "type": "book_snapshot",
                            "venue_id": "kalshi",
                            "data": [
                                {
                                    "market_id": market["id"],
                                    "outcome_id": "yes",
                                    "ts_ns": time.time_ns(),
                                    "bids": [{"px_cents": market["yes_bid"] + random.randint(-2, 2), "qty": random.randint(100, 500)}],
                                    "asks": [{"px_cents": market["yes_ask"] + random.randint(-2, 2), "qty": random.randint(100, 500)}],
                                    "best_bid": market["yes_bid"],
                                    "best_ask": market["yes_ask"],
                                    "mid_px": (market["yes_bid"] + market["yes_ask"]) / 2
                                }
                            ],
                            "ts_received_ns": time.time_ns()
                        }
                    }))
                elif event_count % 5 == 0:
                    # Send health event
                    await websocket.send_text(json.dumps({
                        "type": "event", 
                        "data": {
                            "type": "health",
                            "venue_id": "kalshi",
                            "data": {
                                "status": "healthy",
                                "latency_p50_ms": 45.0 + random.uniform(-10, 10),
                                "latency_p95_ms": 90.0 + random.uniform(-20, 20),
                                "subscribed_markets": 3,
                                "stale_markets": 0,
                                "ts_ns": time.time_ns()
                            },
                            "ts_received_ns": time.time_ns()
                        }
                    }))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
                
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Kalshi Terminal Demo API...")
    print("   URL: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)