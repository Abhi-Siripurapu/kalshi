# CLAUDE.md - Kalshi Terminal Project

This file provides comprehensive guidance for Claude Code when working with this Kalshi prediction markets terminal.

## Project Overview

This is a real-time prediction markets terminal that displays live data from Kalshi. The system has been completely refactored from a complex, over-engineered architecture to a simple, atomic approach that works reliably.

## Current Architecture (Working State)

The system follows a clean, minimal architecture:

```
[Kalshi API] -> [Simple API Server] -> [Simple HTML UI]
```

### Key Components

1. **Simple Kalshi Client** (`simple_kalshi_client.py`)
   - Pure REST API integration with proper authentication
   - No WebSocket complexity (yet)
   - Clean error handling and graceful fallbacks

2. **Simple API Server** (`simple_api.py`)
   - FastAPI server with CORS enabled
   - Endpoints: `/`, `/health`, `/markets`, `/market/{ticker}`, `/market/{ticker}/orderbook`
   - Graceful fallback to mock data when Kalshi API unavailable
   - No Redis dependencies, no complex middleware

3. **Simple UI** (`ui/index.html`)
   - Pure HTML/CSS/JavaScript - NO build tools, NO TypeScript, NO frameworks
   - Auto-refreshing every 10 seconds via REST API polling
   - Clean terminal-style dark theme

## Environment Setup

### Required Environment Variables
```bash
KALSHI_API_KEY=your_api_key_here
KALSHI_PRIVATE_KEY_PATH=./kalshi-key.pem
KALSHI_ENVIRONMENT=prod
```

### Private Key File
- Must have `kalshi-key.pem` file in project root
- This is the RSA private key for Kalshi API authentication

### Python Environment
- Uses `uv` for dependency management
- Always run `source .venv/bin/activate` before Python commands
- Dependencies: fastapi, uvicorn, aiohttp, cryptography, python-dotenv

## Development Workflow

### Starting the System
```bash
# 1. Activate Python environment
source .venv/bin/activate

# 2. Start API server (background)
python simple_api.py &

# 3. Start UI server (background)
cd ui && python -m http.server 3000 &

# 4. Access terminal at http://localhost:3000
```

### Testing Components Individually
```bash
# Test Kalshi client
python simple_kalshi_client.py

# Test API endpoints
curl http://localhost:8000/markets?limit=5
curl http://localhost:8000/market/TICKER/orderbook
```

## What Was Wrong Before

The original codebase had major architectural issues:

1. **Over-engineered Dependencies**: Complex Redis/WebSocket chains that all had to work perfectly
2. **Fragile Event Flow**: Events flowing through multiple transformers, any failure broke everything
3. **Build Tool Issues**: TypeScript config problems, Vite caching, multiple dev servers on same port
4. **Complex State Management**: Multiple adapters, normalizers, publishers creating confusion

## Current Working State

**✅ WORKING:**
- REST API integration with Kalshi
- Real market data display (20+ active markets)
- Market selection and orderbook viewing
- Auto-refresh every 10 seconds
- Clean, responsive UI

**✅ COMPLETED:**
- REST API integration with Kalshi ✅
- Real market data display (12,000+ active markets) ✅
- Market selection and orderbook viewing ✅
- Auto-refresh every 10 seconds ✅
- Clean, responsive UI ✅
- **🔥 BREAKTHROUGH: WebSocket authentication solved!** ✅
- **🔥 Real-time Kalshi WebSocket data streaming!** ✅
- **🔥 Complete real-time bridge** (942+ markets streaming live) ✅
- **🔥 Working prediction markets terminal with live data** ✅
- **🔥 NEW: Complete UI redesign with table-based interface** ✅
- **🔥 NEW: Infinite scroll for 12,000+ markets** ✅
- **🔥 NEW: Market categorization and search functionality** ✅
- **🔥 NEW: Comprehensive market caching system with pagination** ✅
- **🔥 NEW: Separate market detail pages** ✅
- **🔥 NEW: Repository reorganization and cleanup** ✅

**✅ COMPLETED (Current Session):**
- **Multi-outcome market grouping**: ✅ Fixed - Markets are now properly grouped by event_ticker (e.g., "Oviedo vs Real Madrid" shows as one entry with outcome indicator)
- **Market detail statistics display**: ✅ Fixed - Bid/ask prices and liquidity now show real data instead of dashes
- **Individual outcome analytics**: ✅ Fixed - "View Analytics →" buttons now load real Chart.js charts with candlestick data instead of placeholder text
- **Analytics recreation**: ✅ Complete - Full analytics system with Chart.js showing price action, bid-ask spreads, and volume/open interest
- **Multi-outcome navigation**: ✅ Working - Clicking grouped markets properly navigates to detail pages with all outcomes listed

**📋 IMMEDIATE NEXT STEPS:**
1. **Test end-to-end functionality**: Validate that all market types (single-outcome, multi-outcome) work correctly from markets table → detail page → individual outcome analytics  
2. **Validate authentication**: Ensure Kalshi API credentials are properly loaded (currently working via manual export)

**📋 ENHANCEMENT PHASE (Future):**
- Add real-time orderbook subscriptions for selected markets via WebSocket
- Implement candlestick/OHLC data collection and display  
- Build interactive charts and visualizations using real-time WebSocket data
- Add advanced market analytics (volume trends, price history, volatility)
- Implement advanced charting (price charts, volume charts, order flow)
- Optional Redis caching layer for performance optimization

## Next Implementation Steps

### Phase 1: Atomic WebSocket Client
1. Create minimal WebSocket client that ONLY handles Kalshi WebSocket connection
2. Test subscription to single market orderbook updates
3. Ensure reconnection and error handling works

### Phase 2: WebSocket Integration
1. Add WebSocket endpoint to simple API server
2. Bridge Kalshi WebSocket data to browser clients
3. Update UI to connect to WebSocket for real-time updates

### Phase 3: Enhanced Features
1. Add Redis caching for performance (optional)
2. Add market analytics and charting
3. Add trade execution capabilities (if needed)

## Critical Lessons Learned

### UI Development
- **NEVER use complex build tools until basic functionality works**
- **Pure HTML/CSS/JS is often better than React/TypeScript for terminals**
- **Always check what's actually running on ports with `ss -tulpn | grep :3000`**
- **Kill old processes explicitly before starting new ones**

### API Development
- **Start with REST, add WebSockets later**
- **Always provide mock data fallback for development**
- **CORS is essential for browser development**
- **FastAPI's automatic docs at `/docs` are invaluable**

### Authentication ⚠️ CRITICAL DISCOVERY
- **🚨 Kalshi REST API**: Uses MILLISECONDS timestamp (`time.time() * 1000`)
- **🚨 Kalshi WebSocket**: Uses SECONDS timestamp (`time.time()`) - DOCUMENTATION IS WRONG!
- **Official Kalshi docs incorrectly state WebSocket needs milliseconds - it actually needs seconds**
- **RSA-PSS signing with SHA256 is required for both**
- **Private key must be in PEM format**
- **WebSocket works on Production environment, not demo**

## File Structure
```
kalshi/
├── CLAUDE.md                      # This file  
├── README.md                      # User documentation
├── .env                           # Environment variables
├── kalshi-key.pem                # Private key for Kalshi API
├── start.sh                       # Start all services
├── stop.sh                        # Stop all services
├── requirements.txt               # Python dependencies
├── backend/                       # Server components
│   ├── simple_api.py              # FastAPI server with REST endpoints
│   ├── simple_kalshi_client.py    # 🔥 WORKING Kalshi REST client
│   ├── simple_websocket_client.py # 🔥 WORKING Kalshi WebSocket client
│   └── real_time_bridge.py        # 🔥 LIVE bridge: Kalshi WebSocket → UI
├── frontend/                      # UI components
│   └── ui/
│       └── index.html             # 🔥 LIVE terminal with real Kalshi data
└── scripts/                       # Utility scripts
    ├── simple_adapter.py          # Legacy adapter
    ├── simple_ws_server.py        # Mock WebSocket server (backup)
    └── debug_websocket_auth.py    # WebSocket auth debugger tool
```

## Development Commands

### Most Important Commands
```bash
# Start everything (recommended)
./start.sh

# Stop everything  
./stop.sh

# Manual startup (for development)
source .venv/bin/activate
cd backend && python simple_api.py &
cd backend && python real_time_bridge.py &
cd frontend/ui && python -m http.server 3000 &

# Check what's running
ss -tulpn | grep :3000
ss -tulpn | grep :8000
ss -tulpn | grep :8001

# Test API
curl http://localhost:8000/markets?limit=3
curl http://localhost:8000/
```

## Future Development Notes

### When Adding WebSockets
- **Test WebSocket connection separately FIRST**
- **Use simple echo server to verify browser WebSocket works**
- **Add WebSocket as enhancement, keep REST API as fallback**
- **Implement proper reconnection logic with exponential backoff**

### When Adding Redis
- **Make it completely optional - system should work without it**
- **Use it only for caching, not as a dependency**
- **Add clear fallback paths when Redis is unavailable**

### When Scaling
- **Keep the atomic principle - each component should work independently**
- **Add complexity incrementally, test each step**
- **Always maintain the simple HTML UI as a debugging tool**

## Debugging Tips

### UI Not Updating
1. Check browser console for JavaScript errors
2. Verify API is running: `curl http://localhost:8000/`
3. Check CORS headers in browser network tab
4. Kill all localhost processes and restart

### API Not Working
1. Check if running: `curl http://localhost:8000/health`
2. Verify environment variables: `python -c "import os; print(os.getenv('KALSHI_API_KEY'))"`
3. Test Kalshi API directly: `python simple_kalshi_client.py`

### Markets Not Loading
1. Check API response: `curl http://localhost:8000/markets?limit=1`
2. Verify Kalshi credentials are valid
3. Check if mock mode is enabled (should show `"mock_mode": false`)

### Starting System (Updated Commands)
```bash
# Kill everything and restart clean
pkill -f "python.*simple_api.py"
pkill -f "python.*http.server"

# Start backend API (from project root) - WITH CREDENTIALS FROM .env
cd backend && source ../.venv/bin/activate && python simple_api.py &

# Start frontend UI (from project root)
cd frontend/ui && python -m http.server 3000 &

# Access UI
# Main markets table: http://localhost:3000/markets.html  
# Market detail: http://localhost:3000/detail.html?ticker=MARKET_TICKER
# Atomic test: http://localhost:3000/test_detail.html
```

### Current Session Status
- ✅ 12,000+ markets loading successfully
- ✅ Real Kalshi data (not mock mode)
- ✅ Table-based UI with infinite scroll working
- 🚧 Multi-outcome markets showing as duplicates (need grouping fix)
- 🚧 Market detail statistics not displaying (debugging in progress)
- 📝 Files modified this session:
  - `/home/rapu/kalshi/frontend/ui/detail.html` (added debugging, fixed formatPrice)
  - `/home/rapu/kalshi/frontend/ui/markets.html` (partial groupMultiOutcomeMarkets function)
  - `/home/rapu/kalshi/frontend/ui/test_detail.html` (atomic test page created)

## Success Metrics

The system is working correctly when:
- ✅ API returns real market data (not mock)
- ✅ UI displays 20+ markets on load
- ✅ Market selection shows orderbook data
- ✅ Auto-refresh updates every 10 seconds
- ✅ No errors in browser console
- ✅ Clean, responsive terminal interface
- ✅ **WebSocket connects to Kalshi and streams real ticker data**
- ✅ **Live market updates flow to UI in real-time**

## 🔥 WebSocket Breakthrough Details

After extensive debugging, we discovered that Kalshi's WebSocket documentation is **incorrect**:

### What Kalshi Docs Say (WRONG):
```
KALSHI-ACCESS-TIMESTAMP: unix_timestamp_in_milliseconds
```

### What Actually Works:
```python
# REST API - uses milliseconds
timestamp = str(int(time.time() * 1000))

# WebSocket - uses seconds (NOT milliseconds!)
timestamp = str(int(time.time()))
```

### Working WebSocket Connection:
```python
from simple_websocket_client import SimpleKalshiWebSocketClient

client = SimpleKalshiWebSocketClient(api_key, private_key_path)
await client.connect()  # ✅ Works!
await client.subscribe_to_ticker()  # ✅ Real-time data!
```

This atomic approach has proven successful - maintain this simplicity as complexity is added back incrementally.