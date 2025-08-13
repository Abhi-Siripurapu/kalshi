# Kalshi Terminal - Day 2 Complete! 🚀

A professional prediction markets terminal starting with Kalshi market data streaming.

## ✅ Day 2 Status - Market Data Online

### What's Working
- **Kalshi WebSocket Adapter**: Authenticated connection with auto-reconnect
- **Real-time Market Data**: Live orderbook snapshots and updates  
- **Health Monitoring**: Latency tracking and connection status
- **Data Pipeline**: Redis caching + Parquet recording for replay
- **Live UI**: React dashboard showing real-time books and events
- **API Layer**: FastAPI with WebSocket broadcasting

### Quick Start

1. **Get Your Kalshi API Key**
   - Go to Kalshi demo/prod account
   - Navigate to Account & security → API Keys
   - Download your private key as `kalshi-key.pem`

2. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your KALSHI_API_KEY (already set to your key)
   # Put your kalshi-key.pem file in the project root
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   cd ui && npm install
   ```

4. **Test Kalshi Adapter (Standalone)**
   ```bash
   python start_kalshi_adapter.py
   ```
   You should see:
   - ✅ WebSocket connection
   - 📊 Market discovery 
   - 📖 Live orderbook data
   - 💗 Health reports

5. **Start Full System**
   ```bash
   # Terminal 1: Start Redis
   redis-server

   # Terminal 2: Start API
   cd api && python main.py

   # Terminal 3: Start UI  
   cd ui && npm run dev

   # Terminal 4: Start adapter
   python main.py
   ```

6. **Access UI**
   - Open http://localhost:3000
   - Should show live Kalshi data streaming

## What You'll See

### System Status
- API: Connected/Healthy
- Kalshi: Connected with live latency metrics
- Redis: Book caching working

### Live Order Books
- Real-time YES/NO books for active markets
- Best bid/ask prices updating live
- Staleness warnings if data stops

### Event Stream
- Market discovery events
- Book snapshot updates
- Health monitoring
- Connection status changes

## Architecture

```
[Kalshi API] ──WebSocket──> [Kalshi Adapter] ──> [Redis Cache] ──> [API] ──WebSocket──> [UI]
                                   │                    │
                                   └──> [Parquet Recorder]
```

## Day 2 Acceptance Criteria ✅

- [x] Kalshi adapter connects and stays connected
- [x] Books stream with <500ms latency  
- [x] Redis holds latest books
- [x] Parquet recorder captures all events
- [x] UI shows live venue status and books
- [x] Health monitoring with latency metrics
- [x] Auto-reconnect on disconnect
- [x] Replay capability (recorded data)

## Next: Day 3 Tasks

- [ ] Polymarket adapter (waiting for your docs)
- [ ] Duplicate market matching engine
- [ ] Fee-adjusted edge calculation
- [ ] Cross-venue pair detection
- [ ] Manual override system (force/blacklist pairs)

## Troubleshooting

**"KALSHI_API_KEY not found"**
- Set your API key in `.env` file

**"Private key file not found"**  
- Download from Kalshi and save as `kalshi-key.pem`

**"WebSocket connection failed"**
- Check your API key is valid
- Verify you're using the demo environment
- Check network connectivity

**"No market data"**
- Markets may be closed/inactive
- Check Kalshi website for active markets
- Adapter auto-discovers available markets

## Files Created Today

- `adapters/kalshi/` - Complete Kalshi integration
- `core/state/redis_store.py` - Redis caching layer
- `core/recorder/parquet_recorder.py` - Event recording
- `api/main.py` - Enhanced API with WebSocket
- `ui/src/App.tsx` - Live data dashboard
- `main.py` - Service orchestrator