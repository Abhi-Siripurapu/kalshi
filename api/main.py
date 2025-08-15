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
from adapters.kalshi.client import KalshiClient
from datetime import datetime, timedelta

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
kalshi_client: Optional[KalshiClient] = None

@app.on_event("startup")
async def startup_event():
    global redis_store, recorder, kalshi_client
    
    # Initialize Redis store
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_store = RedisBookStore(redis_url)
    await redis_store.connect()
    
    # Initialize recorder
    data_dir = os.getenv("DATA_DIR", "./data/records")
    recorder = ParquetRecorder(data_dir)
    
    # Initialize Kalshi client for API calls
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    if api_key:
        kalshi_client = KalshiClient(api_key, private_key_path)
        await kalshi_client.__aenter__()
    
    logging.info("API services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    global redis_store, recorder, kalshi_client
    
    if redis_store:
        await redis_store.disconnect()
    if recorder:
        await recorder.close()
    if kalshi_client:
        await kalshi_client.__aexit__(None, None, None)

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
async def get_markets(
    venue_id: Optional[str] = Query(None, description="Filter by venue"),
    limit: Optional[int] = Query(100, description="Number of markets to return"),
    status: Optional[str] = Query("open", description="Market status filter")
):
    """Get market information"""
    if not redis_store:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        if kalshi_client and venue_id == "kalshi":
            # Fetch real markets from Kalshi
            markets = await kalshi_client.get_markets(limit=limit, status=status)
            return markets
        
        # Fallback to empty structure
        return {"markets": []}
    except Exception as e:
        logging.error(f"Error getting markets: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving markets")

@app.get("/market/{ticker}")
async def get_market_info(ticker: str):
    """Get detailed market information by ticker"""
    try:
        if kalshi_client:
            # Fetch real market data from Kalshi
            market_data = await kalshi_client.get_market_by_ticker(ticker)
            if market_data:
                return market_data
        
        # Fallback mock data
        return {
            "ticker": ticker,
            "title": f"Market for {ticker}",
            "subtitle": "Prediction market",
            "status": "open",
            "open_time": "2025-08-01T00:00:00Z",
            "close_time": "2025-12-31T23:59:59Z",
            "volume_24h": 1000,
            "liquidity": 5000
        }
    except Exception as e:
        logging.error(f"Error getting market info for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving market info")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial status safely
        try:
            status = await get_status()
            await websocket.send_text(json.dumps({
                "type": "status",
                "data": status
            }))
        except Exception as e:
            logging.warning(f"Failed to send initial status: {e}")
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages (like subscription requests)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle subscription requests
                if message.get("type") == "subscribe":
                    channels = message.get("channels", [])
                    # Acknowledge subscription
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "channels": channels
                        }))
                    except Exception as e:
                        logging.warning(f"Failed to send subscription ack: {e}")
                        break
                    
            except WebSocketDisconnect:
                logging.info("WebSocket client disconnected")
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
    for websocket in websocket_connections[:]:  # Copy list to avoid modification during iteration
        try:
            await websocket.send_text(message_text)
        except Exception as e:
            logging.debug(f"Removing disconnected WebSocket client: {e}")
            disconnected.append(websocket)
    
    # Clean up disconnected clients
    for websocket in disconnected:
        if websocket in websocket_connections:
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
        
        # Also store book snapshots in Redis for API endpoints
        if event.get("type") == "book_snapshot" and redis_store:
            books = event.get("data", [])
            for book in books:
                if isinstance(book, dict):
                    book_data = {
                        "ts_ns": book.get("ts_ns"),
                        "bids": book.get("bids", []),
                        "asks": book.get("asks", []),
                        "best_bid": book.get("best_bid"),
                        "best_ask": book.get("best_ask"),
                        "mid_px": book.get("mid_px"),
                        "sequence": book.get("sequence", 0),
                        "market_id": book.get("market_id"),
                        "outcome_id": book.get("outcome_id")
                    }
                    await redis_store.set_book(
                        book.get("venue_id", "kalshi"),
                        book.get("market_id", ""),
                        book.get("outcome_id", ""),
                        book_data
                    )
        
    except Exception as e:
        logging.error(f"Error publishing to API: {e}")

@app.get("/market/{ticker}/candlesticks")
async def get_market_candlesticks(
    ticker: str,
    start_days_ago: int = Query(7, description="Days ago to start from"),
    period_interval: int = Query(60, description="Candlestick interval in minutes (1, 60, 1440)")
):
    """Get candlestick data for a market"""
    try:
        if not kalshi_client:
            raise HTTPException(status_code=503, detail="Kalshi client not available")
        
        # Calculate timestamps
        end_ts = int(time.time())
        start_ts = end_ts - (start_days_ago * 24 * 60 * 60)
        
        # Note: This would need the series ticker to work with real API
        # For now, return mock candlestick data
        mock_candlesticks = []
        current_ts = start_ts
        interval_seconds = period_interval * 60
        
        while current_ts < end_ts:
            # Generate realistic mock data
            base_price = 50 + (hash(ticker + str(current_ts)) % 40)
            open_price = base_price
            close_price = base_price + ((hash(str(current_ts)) % 10) - 5)
            high_price = max(open_price, close_price) + (hash(str(current_ts + 1)) % 5)
            low_price = min(open_price, close_price) - (hash(str(current_ts + 2)) % 5)
            volume = 100 + (hash(str(current_ts + 3)) % 500)
            
            mock_candlesticks.append({
                "ts": current_ts,
                "open": max(1, open_price),
                "high": max(1, high_price),
                "low": max(1, low_price),
                "close": max(1, close_price),
                "volume": volume
            })
            current_ts += interval_seconds
        
        return {
            "ticker": ticker,
            "candlesticks": mock_candlesticks,
            "period_interval": period_interval
        }
        
    except Exception as e:
        logging.error(f"Error getting candlesticks for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving candlestick data")

@app.get("/market/{ticker}/orderbook")
async def get_market_orderbook(ticker: str, depth: Optional[int] = Query(10, description="Order book depth")):
    """Get current orderbook for a market"""
    try:
        if not kalshi_client:
            raise HTTPException(status_code=503, detail="Kalshi client not available")
        
        # Fetch real orderbook from Kalshi
        orderbook = await kalshi_client.get_orderbook(ticker, depth=depth)
        return orderbook
        
    except Exception as e:
        logging.error(f"Error getting orderbook for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving orderbook")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)