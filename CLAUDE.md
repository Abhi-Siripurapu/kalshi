# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a prediction markets terminal that streams real-time data from multiple venues, starting with Kalshi. The system consists of venue adapters, a data processing pipeline, API layer, and a React-based dashboard UI.

## Architecture

The codebase follows a modular, event-driven architecture:

```
[Venue APIs] -> [Adapters] -> [State Store/Recorder] -> [API] -> [UI Dashboard]
                    |              |
                    v              v
               [Normalizers]   [Redis Cache]
                              [Parquet Files]
```

### Key Components

- **Adapters** (`adapters/`): Venue-specific connectors that handle authentication, WebSocket connections, and data normalization
- **Core** (`core/`): Shared infrastructure including state management, data recording, and business logic
- **API** (`api/`): FastAPI service that exposes WebSocket and REST endpoints for the UI
- **UI** (`ui/`): React + TypeScript dashboard with real-time data visualization

## Development Commands

### Python Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python test_simple.py          # Basic connection test
python test_ws_apikey.py       # WebSocket authentication test  
python test_ws_only.py         # WebSocket-only test

# Start individual services
python main.py                 # Full orchestrator
python start_kalshi_adapter.py # Standalone Kalshi adapter
cd api && python main.py       # API server only

# Environment setup
cp .env.example .env           # Copy environment template
# Edit .env with KALSHI_API_KEY and other config
```

### Frontend UI

```bash
cd ui
npm install                    # Install dependencies
npm run dev                   # Start development server
npm run build                 # Production build
npm run lint                  # TypeScript/ESLint checks
```

### Required Infrastructure

```bash
# Redis (required for state caching)
redis-server

# Optional: Docker services
docker-compose up -d          # Start Redis and other services
```

## Configuration

### Environment Variables

Key environment variables in `.env`:

- `KALSHI_API_KEY`: API key from Kalshi account
- `KALSHI_PRIVATE_KEY_PATH`: Path to `kalshi-key.pem` file (default: `./kalshi-key.pem`)
- `KALSHI_ENVIRONMENT`: Either `demo` or `prod` (default: `demo`)
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)
- `DATA_DIR`: Directory for Parquet data files (default: `./data`)
- `TARGET_MARKETS`: Comma-separated list of market tickers (auto-discovers if empty)

### Market Targeting

The system can auto-discover active markets or target specific ones via `TARGET_MARKETS`. Market data is cached in Redis and recorded to Parquet files for replay analysis.

## Data Flow & Normalization

Each venue adapter:
1. Connects via authenticated WebSocket
2. Subscribes to orderbook updates for target markets
3. Normalizes venue-specific messages to common event schema
4. Publishes events to Redis state store and Parquet recorder
5. Monitors connection health and latency

Events flow through the system as normalized objects with consistent schema across venues.

## Testing Strategy

- `test_simple.py`: Basic API connectivity and authentication
- `test_ws_apikey.py`: WebSocket connection with API key authentication
- `test_ws_only.py`: WebSocket-only data streaming

Run individual tests to verify specific components before starting the full system.

## Key Files

- `main.py`: Main orchestrator that coordinates all services
- `adapters/kalshi/adapter.py`: Primary Kalshi integration with health monitoring
- `adapters/kalshi/client.py`: WebSocket and REST API client for Kalshi
- `adapters/kalshi/normalizer.py`: Venue-specific to common event normalization
- `core/state/redis_store.py`: Redis caching layer for orderbook state
- `core/recorder/parquet_recorder.py`: Event recording for data persistence
- `api/main.py`: FastAPI server with WebSocket broadcasting
- `ui/src/App.tsx`: Main React dashboard component

## Development Workflow

1. Ensure Redis is running (`redis-server`)
2. Set up environment variables in `.env`
3. Test individual components with test scripts
4. Start services in order: Redis -> API -> UI -> Main orchestrator
5. Access dashboard at `http://localhost:3000`

The system is designed for extensibility - additional venue adapters follow the same pattern as the Kalshi implementation.