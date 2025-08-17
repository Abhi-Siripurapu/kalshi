#!/usr/bin/env python3
"""
Simple API Server - Minimal implementation
Provides market data with optional mock mode for development
"""

import asyncio
import json
import time
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import our simple client
from simple_kalshi_client import SimpleKalshiClient

app = FastAPI(title="Simple Kalshi Terminal API", version="1.0.0")

# Add CORS for UI development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
kalshi_client: Optional[SimpleKalshiClient] = None
use_mock_data = False

# Mock data for development
MOCK_MARKETS = [
    {
        "ticker": "MOCK-ELECTION-2024",
        "title": "Will the 2024 election have over 150M votes?",
        "subtitle": "Mock prediction market for development",
        "status": "open",
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": "2024-12-31T23:59:59Z",
        "volume_24h": 25000,
        "liquidity": 50000,
        "category": "Politics"
    },
    {
        "ticker": "MOCK-TECH-STOCK",
        "title": "Will NVIDIA stock close above $800?",
        "subtitle": "Mock tech stock prediction",
        "status": "open", 
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": "2024-12-31T23:59:59Z",
        "volume_24h": 15000,
        "liquidity": 30000,
        "category": "Finance"
    },
    {
        "ticker": "MOCK-WEATHER-NYC",
        "title": "Will NYC have snow on Christmas?",
        "subtitle": "Mock weather prediction",
        "status": "open",
        "open_time": "2024-01-01T00:00:00Z", 
        "close_time": "2024-12-25T23:59:59Z",
        "volume_24h": 5000,
        "liquidity": 12000,
        "category": "Weather"
    }
]

def generate_mock_orderbook(ticker: str) -> Dict:
    """Generate realistic mock orderbook data"""
    # Use ticker hash for consistent but varied data
    seed = hash(ticker + str(int(time.time() / 60)))  # Changes every minute
    
    # Generate YES bids (people buying YES)
    yes_bids = []
    base_yes_price = 45 + (seed % 20)  # 45-65 cents
    for i in range(5):
        price = max(1, base_yes_price - i * 2)
        qty = 100 + ((seed + i) % 500)
        yes_bids.append([price, qty])
    
    # Generate NO bids (people buying NO, equivalent to YES asks)
    no_bids = []
    base_no_price = 35 + (seed % 20)  # 35-55 cents
    for i in range(5):
        price = max(1, base_no_price - i * 2)
        qty = 100 + ((seed + i + 10) % 500)
        no_bids.append([price, qty])
    
    return {
        "yes": yes_bids,
        "no": no_bids
    }

@app.on_event("startup")
async def startup_event():
    """Initialize the API server"""
    global kalshi_client, use_mock_data
    
    # Try to initialize Kalshi client
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "../kalshi-key.pem")
    
    if api_key and os.path.exists(private_key_path):
        try:
            kalshi_client = SimpleKalshiClient(api_key, private_key_path)
            await kalshi_client.__aenter__()
            
            # Test connection
            test_data = await kalshi_client.get_markets(limit=1)
            if test_data.get("markets"):
                print("✅ Kalshi API connected successfully")
                use_mock_data = False
            else:
                raise Exception("No markets returned")
                
        except Exception as e:
            print(f"⚠️  Kalshi API connection failed: {e}")
            print("📋 Falling back to mock data mode")
            use_mock_data = True
            if kalshi_client:
                await kalshi_client.__aexit__(None, None, None)
                kalshi_client = None
    else:
        print("📋 No Kalshi credentials found, using mock data mode")
        use_mock_data = True

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean up resources"""
    global kalshi_client
    if kalshi_client:
        await kalshi_client.__aexit__(None, None, None)

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Simple Kalshi Terminal API",
        "version": "1.0.0",
        "mock_mode": use_mock_data,
        "kalshi_connected": kalshi_client is not None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "mock_mode": use_mock_data,
        "kalshi_connected": kalshi_client is not None
    }

@app.get("/markets")
async def get_markets(
    limit: int = Query(100, description="Number of markets to return"),
    status: str = Query("open", description="Market status filter")
):
    """Get available markets"""
    try:
        if use_mock_data:
            # Return mock data
            return {
                "markets": MOCK_MARKETS[:limit],
                "cursor": None,
                "mock_mode": True
            }
        
        # Use real Kalshi data
        if kalshi_client:
            data = await kalshi_client.get_markets(limit=limit, status=status)
            return {
                **data,
                "mock_mode": False
            }
        else:
            raise HTTPException(status_code=503, detail="Kalshi client not available")
            
    except Exception as e:
        print(f"Error in get_markets: {e}")
        # Fallback to mock data on error
        return {
            "markets": MOCK_MARKETS[:limit],
            "cursor": None,
            "mock_mode": True,
            "error": str(e)
        }

@app.get("/market/{ticker}")
async def get_market(ticker: str):
    """Get specific market details"""
    try:
        if use_mock_data:
            # Return mock data
            mock_market = next((m for m in MOCK_MARKETS if m["ticker"] == ticker), None)
            if mock_market:
                return {"market": mock_market, "mock_mode": True}
            else:
                raise HTTPException(status_code=404, detail="Market not found")
        
        # Use real Kalshi data
        if kalshi_client:
            market_data = await kalshi_client.get_market(ticker)
            if market_data:
                return {"market": market_data, "mock_mode": False}
            else:
                raise HTTPException(status_code=404, detail="Market not found")
        else:
            raise HTTPException(status_code=503, detail="Kalshi client not available")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_market: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market/{ticker}/orderbook")
async def get_orderbook(
    ticker: str,
    depth: int = Query(10, description="Orderbook depth")
):
    """Get market orderbook"""
    try:
        if use_mock_data:
            # Return mock orderbook
            return {
                "orderbook": generate_mock_orderbook(ticker),
                "mock_mode": True
            }
        
        # Use real Kalshi data
        if kalshi_client:
            orderbook_data = await kalshi_client.get_orderbook(ticker, depth=depth)
            if orderbook_data is not None:
                return {
                    "orderbook": orderbook_data,
                    "mock_mode": False
                }
            else:
                # Return empty orderbook instead of error
                return {
                    "orderbook": {"yes": [], "no": []},
                    "mock_mode": False
                }
        else:
            raise HTTPException(status_code=503, detail="Kalshi client not available")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_orderbook: {e}")
        # Fallback to mock data
        return {
            "orderbook": generate_mock_orderbook(ticker),
            "mock_mode": True,
            "error": str(e)
        }

@app.get("/market/{ticker}/candlesticks")
async def get_candlesticks(
    ticker: str,
    start_days_ago: int = Query(7, description="Days ago to start from"),
    period_interval: int = Query(60, description="Interval in minutes (1, 60, or 1440)")
):
    """Get candlestick data for market"""
    try:
        # Calculate timestamps
        end_ts = int(time.time())
        start_ts = end_ts - (start_days_ago * 24 * 60 * 60)
        
        if use_mock_data or not kalshi_client:
            # Generate mock candlestick data
            interval_seconds = period_interval * 60
            candlesticks = []
            current_ts = start_ts
            
            while current_ts < end_ts:
                seed = hash(ticker + str(current_ts))
                base_price = 50 + (seed % 40)
                
                open_price = base_price
                close_price = base_price + ((seed % 10) - 5)
                high_price = max(open_price, close_price) + (abs(seed) % 5)
                low_price = min(open_price, close_price) - (abs(seed) % 5)
                volume = 100 + (abs(seed) % 500)
                
                candlesticks.append({
                    "ts": current_ts,
                    "open": max(1, open_price),
                    "high": max(1, high_price), 
                    "low": max(1, low_price),
                    "close": max(1, close_price),
                    "volume": volume
                })
                current_ts += interval_seconds
            
            return {
                "candlesticks": candlesticks,
                "ticker": ticker,
                "period_interval": period_interval,
                "mock_mode": True
            }
        
        # Use real Kalshi data
        candlestick_data = await kalshi_client.get_candlesticks(
            ticker=ticker, 
            period_interval=period_interval, 
            start_ts=start_ts, 
            end_ts=end_ts
        )
        
        if candlestick_data:
            return {
                **candlestick_data,
                "mock_mode": False
            }
        else:
            # Fallback to mock data if Kalshi API fails
            raise HTTPException(status_code=503, detail="Unable to fetch candlestick data")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_candlesticks: {e}")
        # Return mock data as fallback
        end_ts = int(time.time())
        start_ts = end_ts - (start_days_ago * 24 * 60 * 60)
        return {
            "candlesticks": [],
            "ticker": ticker,
            "period_interval": period_interval,
            "mock_mode": True,
            "error": str(e)
        }

if __name__ == "__main__":
    # Load environment from parent directory
    from dotenv import load_dotenv
    load_dotenv("../.env")
    
    print("🚀 Starting Simple Kalshi Terminal API...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")