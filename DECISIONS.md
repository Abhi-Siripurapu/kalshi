# Architecture Decisions

## Stack Choices

### Backend
- **Language**: Python 3.11+
- **API Framework**: FastAPI (async support, auto-docs, type hints)
- **WebSocket**: FastAPI WebSocket support + uvicorn
- **HTTP Client**: aiohttp for venue API calls
- **Process Management**: asyncio + separate processes for adapters

### Frontend  
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite (fast dev/build)
- **UI Library**: Tailwind CSS + shadcn/ui components
- **State**: Zustand (simple, TypeScript-friendly)
- **WebSocket**: native WebSocket API

### Data Layer
- **Cache**: Redis (latest books, fast reads)
- **Database**: PostgreSQL (orders, fills, positions, config)
- **Time Series**: Parquet files (raw feed capture for replay)
- **Pub/Sub**: Redis pub/sub for inter-service messaging

### Infrastructure
- **Containerization**: Docker + docker-compose
- **Process Supervision**: docker-compose (dev), systemd (prod)
- **Environment**: .env files + python-dotenv
- **Time**: UTC everywhere, NTP sync required

## Process Architecture

```
[Kalshi Adapter] ──┐
                   ├─── Redis Cache ──── [Core API] ──── [UI]
[Polymarket Adapter] ─┘       │              │
                              │              │
                    [Recorder] ┘              └─── [Order Router]
                                                        │
                                                   PostgreSQL
```

### Services
1. **Kalshi Adapter**: WS connection, book normalization, Redis publish
2. **Polymarket Adapter**: Same pattern, different venue
3. **Core API**: FastAPI server, business logic, WebSocket to UI
4. **Order Router**: Paired execution engine (separate process)
5. **UI**: React SPA served by Vite
6. **Recorder**: Parquet logging for replay

## Why These Choices

- **Python**: Strong data handling, good venue API libraries, team familiarity
- **FastAPI**: Type safety, async performance, automatic API docs
- **Redis**: Sub-millisecond book lookups, pub/sub for real-time
- **PostgreSQL**: ACID compliance for money, excellent JSON support
- **React + Vite**: Fast development, great TypeScript support
- **Docker**: Consistent environments, easy deployment

## Development Flow

1. Each adapter runs independently, publishes to Redis
2. Core API subscribes to Redis, serves WebSocket + REST to UI  
3. Order Router reads from Redis, writes to PostgreSQL
4. UI connects via WebSocket for real-time data

## Non-Goals (Out of Scope)

- Microservices complexity (monorepo with focused processes)
- Complex orchestration (K8s, etc.)
- Multi-region deployment
- High-frequency trading optimizations