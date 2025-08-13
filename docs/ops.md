# Operations, Logging, and Monitoring

This document defines the operational requirements for running the terminal in production, including logging standards, metrics collection, health monitoring, and alerting.

## Logging Strategy

### Log Levels and Usage
```python
LOG_LEVELS = {
    "DEBUG": "Development debugging, verbose adapter messages",
    "INFO": "Normal operations, trade execution, market updates", 
    "WARNING": "Degraded performance, approaching limits, recoverable errors",
    "ERROR": "Failed operations, connection issues, order rejections",
    "CRITICAL": "System failures, data corruption, manual intervention required"
}
```

### Structured Logging Format
```json
{
    "timestamp": "2025-01-15T14:23:45.123456Z",
    "level": "INFO",
    "service": "order_router",
    "trace_id": "abc123def456",
    "message": "Paired order executed successfully",
    "data": {
        "pair_id": "fed_rate_mar_25",
        "kalshi_order_id": "K123456",
        "polymarket_order_id": "P789012",
        "edge_cents": 320,
        "quantity": 500,
        "net_profit_cents": 1600,
        "execution_time_ms": 1234
    },
    "tags": ["arbitrage", "execution", "fed_rate"]
}
```

### Log Categories

#### Adapter Logs
```python
# Connection events
{"service": "kalshi_adapter", "event": "websocket_connected", "latency_ms": 123}
{"service": "polymarket_adapter", "event": "websocket_disconnected", "reason": "timeout"}

# Market data
{"service": "kalshi_adapter", "event": "book_update", "market_id": "FED-25MAR19", "levels": 5}
{"service": "normalizer", "event": "book_normalized", "venue": "kalshi", "outcome_id": "yes"}

# Health monitoring
{"service": "kalshi_adapter", "event": "latency_update", "p50_ms": 45, "p95_ms": 120}
{"service": "polymarket_adapter", "event": "feed_stale", "staleness_seconds": 15}
```

#### Order Management Logs
```python
# Order lifecycle
{"service": "order_router", "event": "order_submitted", "venue": "kalshi", "order_id": "K123"}
{"service": "order_router", "event": "order_filled", "venue": "kalshi", "fill_qty": 200}
{"service": "order_router", "event": "order_cancelled", "venue": "kalshi", "reason": "timeout"}

# Paired execution
{"service": "order_router", "event": "pair_plan_created", "strategy": "make_kalshi_take_poly"}
{"service": "order_router", "event": "pair_execution_started", "timeout_ms": 60000}
{"service": "order_router", "event": "pair_execution_completed", "success": true}
```

#### Risk Management Logs
```python
# Limit monitoring
{"service": "risk_manager", "event": "position_limit_check", "utilization": 0.85}
{"service": "risk_manager", "event": "daily_turnover_check", "used": 18500, "limit": 25000}

# Circuit breakers
{"service": "risk_manager", "event": "circuit_breaker_triggered", "reason": "daily_loss_limit"}
{"service": "risk_manager", "event": "trading_halted", "trigger": "venue_disconnect"}
```

### Log Rotation and Retention
```python
LOG_ROTATION = {
    "file_size_mb": 100,        # Rotate at 100MB
    "retention_days": 30,       # Keep 30 days of logs
    "compression": "gzip",      # Compress rotated logs
    "backup_count": 5           # Keep 5 backup files
}
```

## Metrics Collection

### Key Performance Indicators (KPIs)
```python
BUSINESS_METRICS = {
    "daily_pnl": "Net P&L for current trading day",
    "total_trades": "Number of completed arbitrage pairs",
    "average_edge_captured": "Average profit per trade in cents",
    "fill_rate": "Percentage of orders that execute successfully",
    "average_holding_time": "Time between paired order legs",
    "position_utilization": "Percentage of risk limits utilized"
}
```

### Technical Metrics
```python
TECHNICAL_METRICS = {
    "feed_latency_p50": "50th percentile feed latency in milliseconds",
    "feed_latency_p95": "95th percentile feed latency in milliseconds", 
    "order_response_time": "Time from order submission to acknowledgment",
    "book_update_frequency": "Updates per second for each venue",
    "websocket_reconnections": "Number of reconnection events",
    "memory_usage_mb": "Process memory usage in megabytes",
    "cpu_usage_percent": "CPU utilization percentage"
}
```

### Custom Metrics Implementation
```python
from prometheus_client import Counter, Histogram, Gauge, Summary

# Business metrics
trades_total = Counter('trades_total', 'Total completed trades', ['venue', 'outcome'])
pnl_total = Counter('pnl_cents_total', 'Total P&L in cents', ['venue'])
edge_captured = Histogram('edge_captured_cents', 'Edge captured per trade')

# Technical metrics  
feed_latency = Histogram('feed_latency_seconds', 'Feed latency', ['venue'])
order_response_time = Histogram('order_response_seconds', 'Order response time', ['venue'])
active_positions = Gauge('active_positions', 'Number of active positions')
```

## Health Monitoring

### Service Health Checks
```python
@dataclass
class HealthStatus:
    service: str
    status: str              # "healthy" | "degraded" | "down"
    last_check: datetime
    details: dict
    dependencies: list[str]

async def check_adapter_health(venue: str) -> HealthStatus:
    checks = {
        "websocket_connected": await check_websocket_status(venue),
        "recent_data": await check_recent_book_updates(venue), 
        "latency_acceptable": await check_feed_latency(venue),
        "error_rate_low": await check_error_rate(venue)
    }
    
    status = "healthy" if all(checks.values()) else "degraded"
    if not checks["websocket_connected"]:
        status = "down"
        
    return HealthStatus(
        service=f"{venue}_adapter",
        status=status,
        last_check=datetime.utcnow(),
        details=checks,
        dependencies=["redis", "venue_api"]
    )
```

### Dependency Monitoring
```python
DEPENDENCIES = {
    "redis": {
        "type": "cache",
        "check_interval": 10,
        "timeout": 5,
        "critical": True
    },
    "postgres": {
        "type": "database", 
        "check_interval": 30,
        "timeout": 10,
        "critical": True
    },
    "kalshi_api": {
        "type": "external",
        "check_interval": 5,
        "timeout": 2,
        "critical": True
    },
    "polymarket_api": {
        "type": "external",
        "check_interval": 5, 
        "timeout": 2,
        "critical": True
    }
}
```

### System Resource Monitoring
```python
def collect_system_metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_usage_mb": psutil.virtual_memory().used / 1024 / 1024,
        "disk_usage_percent": psutil.disk_usage('/').percent,
        "network_connections": len(psutil.net_connections()),
        "open_files": len(psutil.Process().open_files()),
        "load_average": os.getloadavg()[0]  # 1-minute load average
    }
```

## Alerting Rules

### Critical Alerts (Immediate Response)
```python
CRITICAL_ALERTS = {
    "service_down": {
        "condition": "service_status == 'down' for > 30s",
        "notification": ["pager", "slack", "email"],
        "escalation": "immediate"
    },
    "data_corruption": {
        "condition": "schema_validation_errors > 0",
        "notification": ["pager", "slack"], 
        "escalation": "immediate"
    },
    "position_breach": {
        "condition": "position_exposure > max_limit * 1.1",
        "notification": ["pager", "slack"],
        "escalation": "immediate"
    },
    "loss_limit_breach": {
        "condition": "daily_loss > max_daily_loss",
        "notification": ["pager", "slack"],
        "escalation": "immediate"
    }
}
```

### Warning Alerts (Monitor Closely)
```python
WARNING_ALERTS = {
    "high_latency": {
        "condition": "feed_latency_p95 > 2000ms for > 2min",
        "notification": ["slack"],
        "escalation": "15min"
    },
    "approaching_limits": {
        "condition": "position_utilization > 0.85",
        "notification": ["slack"],
        "escalation": "30min"
    },
    "low_fill_rate": {
        "condition": "fill_rate < 0.7 over 1hour",
        "notification": ["slack"],
        "escalation": "1hour"
    },
    "stale_data": {
        "condition": "time_since_last_update > 30s",
        "notification": ["slack"],
        "escalation": "2min"
    }
}
```

### Info Alerts (Awareness Only)
```python
INFO_ALERTS = {
    "new_opportunities": {
        "condition": "new_arbitrage_edge > threshold",
        "notification": ["slack"],
        "escalation": "none"
    },
    "market_changes": {
        "condition": "spec_validation_changed",
        "notification": ["slack"],
        "escalation": "none"
    },
    "performance_milestones": {
        "condition": "daily_pnl > milestone_threshold",
        "notification": ["slack"],
        "escalation": "none"
    }
}
```

## Data Recording and Replay

### Raw Feed Recording
```python
@dataclass
class RawMessage:
    timestamp_ns: int           # Nanosecond precision
    venue: str                  # "kalshi" | "polymarket"
    message_type: str           # "book_snapshot" | "book_update" | "trade"
    market_id: str              # Venue-specific market ID
    raw_payload: dict           # Original message from venue
    normalized_payload: dict    # Our canonical format
    
def record_message(message: RawMessage):
    # Write to Parquet file (hourly rotation)
    filename = f"raw_feed_{message.venue}_{datetime.utcnow().strftime('%Y%m%d_%H')}.parquet"
    append_to_parquet(filename, message)
```

### Trade Recording
```python
@dataclass
class TradeRecord:
    trade_id: str
    timestamp_ns: int
    pair_id: str
    strategy: str               # "make_kalshi_take_poly"
    kalshi_order: OrderRecord
    polymarket_order: OrderRecord
    edge_cents: int             # Expected edge
    realized_edge_cents: int    # Actual edge after execution
    fees_cents: int
    slippage_cents: int
    execution_time_ms: int
    success: bool
    failure_reason: str = None
```

### Replay Infrastructure  
```python
class ReplayEngine:
    def __init__(self, start_time: datetime, end_time: datetime):
        self.start_time = start_time
        self.end_time = end_time
        self.message_queue = []
        
    async def load_messages(self) -> list[RawMessage]:
        # Load from Parquet files in time range
        # Sort by timestamp
        # Return chronologically ordered messages
        pass
        
    async def replay_session(self, speed_multiplier: float = 1.0):
        # Feed messages at original timing (or faster)
        # Allow strategy testing against historical data
        # Generate performance comparison report
        pass
```

## Performance Monitoring

### Latency Tracking
```python
class LatencyTracker:
    def __init__(self):
        self.timers = {}
        
    def start_timer(self, operation: str, trace_id: str):
        self.timers[trace_id] = {
            "operation": operation,
            "start_ns": time.time_ns()
        }
        
    def end_timer(self, trace_id: str) -> int:
        if trace_id in self.timers:
            duration_ns = time.time_ns() - self.timers[trace_id]["start_ns"]
            operation = self.timers[trace_id]["operation"]
            
            # Record metric
            LATENCY_HISTOGRAM.labels(operation=operation).observe(duration_ns / 1e9)
            
            # Log if slow
            if duration_ns > 1e9:  # > 1 second
                logger.warning(f"Slow operation: {operation} took {duration_ns/1e6:.1f}ms")
                
            del self.timers[trace_id]
            return duration_ns
```

### Memory and Resource Tracking
```python
def monitor_resources():
    process = psutil.Process()
    
    metrics = {
        "memory_rss_mb": process.memory_info().rss / 1024 / 1024,
        "memory_vms_mb": process.memory_info().vms / 1024 / 1024,
        "cpu_percent": process.cpu_percent(),
        "num_threads": process.num_threads(),
        "num_fds": process.num_fds(),
        "num_connections": len(process.connections())
    }
    
    # Alert if approaching limits
    if metrics["memory_rss_mb"] > 1000:  # > 1GB
        logger.warning(f"High memory usage: {metrics['memory_rss_mb']:.1f}MB")
        
    if metrics["num_fds"] > 500:  # > 500 file descriptors
        logger.warning(f"High FD usage: {metrics['num_fds']}")
        
    return metrics
```

## Deployment and Environment Management

### Environment Configuration
```python
ENVIRONMENTS = {
    "development": {
        "log_level": "DEBUG",
        "metrics_enabled": False,
        "trade_execution": False,
        "database": "sqlite:///dev.db"
    },
    "staging": {
        "log_level": "INFO", 
        "metrics_enabled": True,
        "trade_execution": False,  # Paper trading only
        "database": "postgresql://staging_db"
    },
    "production": {
        "log_level": "INFO",
        "metrics_enabled": True,
        "trade_execution": True,
        "database": "postgresql://prod_db"
    }
}
```

### Health Check Endpoints
```python
@app.get("/health")
async def health_check():
    """Basic liveness check"""
    return {"status": "ok", "timestamp": datetime.utcnow()}

@app.get("/health/detailed")
async def detailed_health():
    """Comprehensive health status"""
    checks = await run_all_health_checks()
    
    return {
        "status": "healthy" if all_healthy(checks) else "degraded",
        "timestamp": datetime.utcnow(),
        "services": checks,
        "dependencies": await check_dependencies(),
        "metrics": await get_current_metrics()
    }

@app.get("/ready")
async def readiness_check():
    """Ready to handle traffic"""
    ready = await check_readiness()
    
    if not ready:
        raise HTTPException(status_code=503, detail="Service not ready")
        
    return {"status": "ready", "timestamp": datetime.utcnow()}
```

### Graceful Shutdown
```python
async def graceful_shutdown():
    logger.info("Starting graceful shutdown")
    
    # Stop accepting new trades
    await order_router.stop_new_orders()
    
    # Cancel open orders
    await order_router.cancel_all_orders()
    
    # Close WebSocket connections
    await adapter_manager.disconnect_all()
    
    # Flush logs and metrics
    await log_manager.flush()
    await metrics_manager.flush()
    
    logger.info("Graceful shutdown complete")
```