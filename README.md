# 🏛️ Kalshi Terminal

A modern, real-time prediction markets terminal for [Kalshi](https://kalshi.com). 

## ✨ Features

###  Real-Time Market Data
- **Live WebSocket streaming** from Kalshi API (12,000+ markets)
- **Real-time price updates** with sub-second latency
- **Order book depth** with bid/ask visualization
- **Market status tracking** (open, closed, settled)

###  Advanced Analytics
- **Interactive price charts** with Chart.js integration
- **Candlestick data** across multiple timeframes
- **Bid-ask spread analysis** and liquidity metrics
- **Volume and open interest tracking**
- **Historical price movement** with technical indicators

### Market Discovery
- **Smart search** across 12,000+ markets
- **Category filtering** (Politics, Sports, Crypto, Weather, etc.)
- **Multi-outcome market grouping** with outcome probability display
- **Market comparison tools** and correlation analysis



## Quick Start

### Prerequisites

- Python 3.8 or higher
- A Kalshi account with API access
- Your Kalshi private key file (`.pem` format)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/kalshi-terminal.git
   cd kalshi-terminal
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure API credentials**
   ```bash
   # Copy your Kalshi private key to project root
   cp /path/to/your/kalshi-key.pem ./kalshi-key.pem
   
   # Copy the example environment file and edit it with your credentials
   cp .env.example .env
   # Edit .env and replace 'your_api_key_here' with your actual Kalshi API key
   ```

4. **Start the terminal**
   ```bash
   chmod +x start.sh stop.sh
   ./start.sh
   ```

5. **Access the terminal**
   - **Main Terminal**: http://localhost:3000/markets.html
   - **API Documentation**: http://localhost:8000/docs
   - **WebSocket Bridge**: http://localhost:8001

## 📖 Usage Guide

### Browsing Markets
1. Open http://localhost:3000/markets.html
2. Use the search bar to find specific markets
3. Filter by categories using the filter buttons
4. Scroll through the infinite list of markets
5. Click on any market to view detailed analytics

### Market Analysis
- **Single Markets**: View price charts, order book, and trading statistics
- **Multi-Outcome Markets**: See all possible outcomes with probability distributions
- **Real-Time Updates**: Watch live price movements and order flow
- **Historical Data**: Analyze price trends across different timeframes

### API Access
- REST API available at http://localhost:8000
- WebSocket streaming at ws://localhost:8001/ws
- Full OpenAPI documentation at http://localhost:8000/docs

### Management Commands

The terminal includes several utility scripts for easy management:

```bash
./start.sh    # Start all services (API, WebSocket bridge, UI)
./stop.sh     # Stop all services
./status.sh   # Check service health and resource usage
./logs.sh     # View service logs (use ./logs.sh follow for real-time)
```

**Log Management:**
```bash
./logs.sh api      # View API server logs only
./logs.sh bridge   # View WebSocket bridge logs only  
./logs.sh ui       # View UI server logs only
./logs.sh all      # View all logs (default)
./logs.sh follow   # Follow all logs in real-time
```

## 🏗️ Architecture



```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Browser UI    │    │   FastAPI Server │    │   Kalshi API    │
│  (Port 3000)    │◄──►│   (Port 8000)    │◄──►│   (External)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ WebSocket Bridge │
                       │   (Port 8001)    │
                       └──────────────────┘
```

### Components

- **Frontend** (`frontend/ui/`): Pure HTML/CSS/JavaScript terminal interface
- **API Server** (`backend/simple_api.py`): REST endpoints for market data
- **Kalshi Client** (`backend/simple_kalshi_client.py`): Authentication and API integration
- **WebSocket Bridge** (`backend/real_time_bridge.py`): Real-time data streaming
- **Market Cache** (`backend/market_cache.py`): In-memory market data caching


## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KALSHI_API_KEY` | Your Kalshi API key | Required |
| `KALSHI_PRIVATE_KEY_PATH` | Path to your private key file | `./kalshi-key.pem` |
| `KALSHI_ENVIRONMENT` | API environment (prod/demo) | `prod` |

### Ports

| Service | Port | Description |
|---------|------|-------------|
| Terminal UI | 3000 | Web interface |
| REST API | 8000 | Market data API |
| WebSocket Bridge | 8001 | Real-time streaming |

## 🛠️ Development

### Running in Development Mode

```bash
# Start individual components for development
source .venv/bin/activate

# API Server (with auto-reload)
cd backend && uvicorn simple_api:app --reload --port 8000

# WebSocket Bridge
cd backend && python real_time_bridge.py

# Frontend (any static server)
cd frontend/ui && python -m http.server 3000
```

### Testing API Endpoints

```bash
# Test market data
curl http://localhost:8000/markets?limit=5

# Test specific market
curl http://localhost:8000/market/SOME-TICKER

# Test health check
curl http://localhost:8000/health
```



## Troubleshooting

### Common Issues

**Markets not loading:**
```bash
# Check if API server is running
curl http://localhost:8000/health

# Verify credentials
python -c "import os; print('API Key:', os.getenv('KALSHI_API_KEY'))"
```

**WebSocket connection failed:**
```bash
# Check if bridge is running
curl http://localhost:8001/

# Check firewall/port availability
ss -tulpn | grep :8001
```

**Authentication errors:**
- Ensure your `kalshi-key.pem` file is in the project root
- Verify your API key is correct in `.env`
- Check that you're using the production environment

### Logs and Debugging

```bash
# View all service logs
./logs.sh  # If available

# Check individual service status
ps aux | grep python

# Stop and restart cleanly
./stop.sh && ./start.sh
```

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status and information |
| `/health` | GET | Health check |
| `/markets` | GET | List all markets with filtering |
| `/market/{ticker}` | GET | Get specific market details |
| `/market/{ticker}/orderbook` | GET | Get market order book |
| `/market/{ticker}/candlesticks` | GET | Get price history |

### WebSocket Events

| Event Type | Description |
|------------|-------------|
| `connected` | Initial connection confirmation |
| `ticker` | Real-time price updates |
| `orderbook_snapshot` | Full order book state |
| `orderbook_delta` | Order book changes |


## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Kalshi](https://kalshi.com) for providing the prediction markets API
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Chart.js](https://www.chartjs.org/) for beautiful charts


**Happy Trading!** 
