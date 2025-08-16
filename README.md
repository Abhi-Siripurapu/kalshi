# 🏛️ Kalshi Terminal

A clean, simple real-time prediction markets terminal for Kalshi.

## 🚀 Quick Start

1. **Setup Environment**
   ```bash
   # Copy your Kalshi private key to project root
   cp /path/to/your/kalshi-key.pem ./kalshi-key.pem
   
   # Create environment file
   cat > .env << EOF
   KALSHI_API_KEY=your_api_key_here
   KALSHI_PRIVATE_KEY_PATH=./kalshi-key.pem
   KALSHI_ENVIRONMENT=prod
   EOF
   ```

2. **Install Dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Start Terminal**
   ```bash
   ./start.sh
   ```

4. **Open in Browser**
   - Terminal UI: http://localhost:3000
   - API Docs: http://localhost:8000/docs

## 📁 Project Structure

```
kalshi/
├── README.md                 # This file
├── CLAUDE.md                # Development guide
├── start.sh                 # Start all services
├── stop.sh                  # Stop all services
├── requirements.txt         # Python dependencies
├── kalshi-key.pem          # Your Kalshi private key
├── .env                    # Environment variables
├── backend/                # Server components
│   ├── simple_api.py       # REST API server
│   ├── simple_kalshi_client.py  # Kalshi API client
│   ├── simple_websocket_client.py  # WebSocket client
│   └── real_time_bridge.py # Real-time data bridge
├── frontend/               # UI components
│   └── ui/
│       └── index.html      # Terminal interface
└── scripts/               # Utility scripts
    ├── simple_adapter.py   # Legacy adapter
    ├── simple_ws_server.py # Mock WebSocket server
    └── debug_websocket_auth.py  # Debug tools
```

## ✨ Features

- **Real-time Market Data** - Live prices and orderbooks via WebSocket
- **Multi-outcome Markets** - Proper grouping and display of complex markets
- **Price Analytics** - Charts, VWAP, volume profiles, movement alerts
- **Liquidity Visualization** - Heatmaps for both binary and multi-outcome markets
- **Market Search & Filtering** - Find markets by category or search terms

## 🔧 Services

- **API Server** (port 8000) - REST endpoints for market data
- **WebSocket Bridge** (port 8001) - Real-time data streaming
- **Terminal UI** (port 3000) - Web-based trading interface

## 📊 Market Types

- **Binary Markets** - YES/NO predictions with orderbook display
- **Multi-outcome Markets** - Multiple exclusive outcomes with probability view

## 🛠️ Development

See [CLAUDE.md](CLAUDE.md) for detailed development guidance and architectural decisions.

## 🎯 Usage

1. Browse markets in the left panel
2. Select a market to view details and charts
3. Use search and category filters to find specific markets
4. View real-time price updates and analytics
5. Monitor orderbook depth and liquidity