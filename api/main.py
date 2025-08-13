import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import time

# Import our core components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state.redis_store import RedisBookStore
from core.recorder.parquet_recorder import ParquetRecorder

app = FastAPI(title="Kalshi Terminal API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
redis_store: Optional[RedisBookStore] = None
recorder: Optional[ParquetRecorder] = None
websocket_connections: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    global redis_store, recorder
    
    # Initialize Redis store
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_store = RedisBookStore(redis_url)
    await redis_store.connect()
    
    # Initialize recorder
    data_dir = os.getenv("DATA_DIR", "./data/records")
    recorder = ParquetRecorder(data_dir)
    
    logging.info("API services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    global redis_store, recorder
    
    if redis_store:
        await redis_store.disconnect()
    if recorder:
        await recorder.close()

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "kalshi-terminal-api"}

@app.get("/")
async def root():
    return {"message": "Kalshi Terminal API", "version": "1.0.0"}

@app.get("/status")
async def get_status():
    """Get detailed system status"""
    if not redis_store:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    # Get venue health
    health_data = await redis_store.get_all_health()
    
    # Get system status
    status = {
        "timestamp": time.time(),
        "venues": health_data,
        "api_status": "healthy",
        "redis_connected": redis_store.redis_client is not None
    }
    
    return status

@app.get("/books")
async def get_books(
    venue_id: Optional[str] = Query(None, description="Filter by venue"),
    market_id: Optional[str] = Query(None, description="Filter by market")
):
    """Get current book data"""
    if not redis_store:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        if venue_id and market_id:
            # Get specific market books
            books = {}
            for outcome_id in ["yes", "no"]:
                book = await redis_store.get_book(venue_id, market_id, outcome_id)
                if book:
                    books[f"{market_id}_{outcome_id}"] = book
            return {"books": books}
        else:
            # Get all books
            books = await redis_store.get_all_books(venue_id)
            return {"books": books}
            
    except Exception as e:
        logging.error(f"Error getting books: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving books")

@app.get("/markets")
async def get_markets(venue_id: Optional[str] = Query(None, description="Filter by venue")):
    """Get market information"""
    if not redis_store:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # This would need to scan for market keys
        # For now, return empty structure
        return {"markets": []}
    except Exception as e:
        logging.error(f"Error getting markets: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving markets")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial status
        status = await get_status()
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": status
        }))
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages (like subscription requests)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle subscription requests
                if message.get("type") == "subscribe":
                    channels = message.get("channels", [])
                    # For now, just acknowledge
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "channels": channels
                    }))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
                break
                
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

async def broadcast_to_websockets(message: Dict):
    """Broadcast message to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    message_text = json.dumps(message)
    
    # Remove disconnected clients
    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_text(message_text)
        except Exception:
            disconnected.append(websocket)
    
    # Clean up disconnected clients
    for websocket in disconnected:
        websocket_connections.remove(websocket)

# Function that adapters can use to publish events
async def publish_to_api(event: Dict):
    """Publish event to API (called by adapters)"""
    try:
        # Record to Parquet
        if recorder:
            await recorder.record_event(event)
        
        # Broadcast to WebSocket clients
        await broadcast_to_websockets({
            "type": "event",
            "data": event
        })
        
    except Exception as e:
        logging.error(f"Error publishing to API: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)