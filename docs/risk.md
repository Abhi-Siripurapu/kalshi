# Risk Management Policy

This document defines the exact risk thresholds, position limits, and guardrails that will be enforced in the order router. These limits are designed to prevent catastrophic losses while allowing profitable arbitrage.

## Position Limits

### Per-Event Exposure
```python
MAX_EXPOSURE_PER_EVENT = {
    "default": 2000,      # $2,000 default per market/event
    "macro": 5000,        # $5,000 for Fed/CPI/macro events  
    "sports": 3000,       # $3,000 for major sports
    "earnings": 2500,     # $2,500 for earnings
    "crypto": 1500,       # $1,500 for crypto price bets
    "weather": 1000,      # $1,000 for weather events
    "political": 2000     # $2,000 for political events
}
```

### Per-Venue Limits
```python
MAX_EXPOSURE_PER_VENUE = {
    "kalshi": 15000,      # $15,000 max exposure on Kalshi
    "polymarket": 10000   # $10,000 max exposure on Polymarket
}
```

### Daily Turnover
```python
MAX_DAILY_TURNOVER = 25000  # $25,000 gross daily volume
MAX_DAILY_TRADES = 100      # Maximum 100 individual trades per day
```

### Portfolio Level
```python
MAX_TOTAL_EXPOSURE = 20000     # $20,000 total across all positions
MAX_UNREALIZED_LOSS = 5000     # Close positions if unrealized loss > $5,000
MAX_DAILY_LOSS = 2000          # Stop trading if daily loss > $2,000
```

## Edge Thresholds

### Minimum Required Edge
```python
EDGE_THRESHOLDS = {
    "kalshi_taker_required": {
        "min_edge_cents": 350,    # 3.5¢ minimum for taker legs
        "min_edge_bps": 35        # 35 basis points minimum
    },
    "kalshi_maker_no_fee": {
        "min_edge_cents": 250,    # 2.5¢ minimum when no maker fee
        "min_edge_bps": 25        # 25 basis points minimum  
    },
    "kalshi_maker_with_fee": {
        "min_edge_cents": 400,    # 4.0¢ minimum when maker fee applies
        "min_edge_bps": 40        # 40 basis points minimum
    },
    "polymarket_only": {
        "min_edge_cents": 200,    # 2.0¢ minimum (no fees)
        "min_edge_bps": 20        # 20 basis points minimum
    }
}
```

### Dynamic Thresholds
```python
def calculate_edge_threshold(market_category: str, time_to_resolution: int) -> int:
    base_threshold = EDGE_THRESHOLDS["kalshi_taker_required"]["min_edge_cents"]
    
    # Increase threshold as resolution approaches
    if time_to_resolution < 3600:  # < 1 hour
        base_threshold *= 2.0
    elif time_to_resolution < 86400:  # < 1 day  
        base_threshold *= 1.5
    elif time_to_resolution < 604800:  # < 1 week
        base_threshold *= 1.2
    
    # Adjust by market category risk
    risk_multipliers = {
        "macro": 1.0,      # Fed/CPI are low risk
        "sports": 1.1,     # Slightly higher risk
        "earnings": 1.3,   # Earnings can be volatile
        "crypto": 1.5,     # High volatility
        "political": 1.4,  # Event risk
        "weather": 1.2     # Measurement risk
    }
    
    return int(base_threshold * risk_multipliers.get(market_category, 1.0))
```

## Execution Timeouts

### Order Timeouts
```python
ORDER_TIMEOUTS = {
    "maker_rest_timeout": 60,     # 60s max for maker orders to rest
    "taker_execution_timeout": 10, # 10s max for taker execution
    "cancel_timeout": 5,          # 5s max for cancel requests
    "fill_confirmation_timeout": 15 # 15s max to confirm fills
}
```

### Market Conditions
```python
EXECUTION_GUARDS = {
    "max_spread_bps": 500,        # Don't trade if spread > 5%
    "min_depth_per_leg": 100,     # Minimum $100 depth per price level
    "max_price_staleness": 5,     # Don't trade on prices older than 5s
    "max_latency_ms": 2000        # Don't trade if feed latency > 2s
}
```

## Slippage Protection

### Book Impact Analysis
```python
def calculate_slippage_cost(levels: list[Level], target_qty: int) -> int:
    """Calculate expected slippage cost in cents"""
    total_cost = 0
    remaining_qty = target_qty
    
    for level in sorted(levels, key=lambda x: x.px_cents):
        if remaining_qty <= 0:
            break
            
        fill_qty = min(remaining_qty, level.qty)
        total_cost += fill_qty * level.px_cents
        remaining_qty -= fill_qty
    
    if remaining_qty > 0:
        return float('inf')  # Insufficient liquidity
    
    avg_px = total_cost / target_qty
    best_px = levels[0].px_cents
    slippage_cents = avg_px - best_px
    
    return int(slippage_cents)
```

### Slippage Limits
```python
MAX_SLIPPAGE = {
    "per_leg_cents": 50,          # Max 0.5¢ slippage per leg
    "per_leg_bps": 25,            # Max 25 basis points slippage
    "total_trade_cents": 75       # Max 0.75¢ total slippage impact
}
```

## Pre-Resolution Risk

### Time-Based Restrictions
```python
def is_near_resolution_restricted(resolution_ts: int) -> bool:
    time_to_resolution = resolution_ts - int(time.time())
    
    # No new positions within 2 hours of resolution
    if time_to_resolution < 7200:
        return True
    
    # Reduced position sizes within 24 hours  
    if time_to_resolution < 86400:
        return "reduce_size"
        
    return False
```

### Enhanced Edge Requirements
```python
def get_near_resolution_edge_multiplier(time_to_resolution: int) -> float:
    if time_to_resolution < 3600:     # < 1 hour
        return 3.0
    elif time_to_resolution < 7200:   # < 2 hours
        return 2.0  
    elif time_to_resolution < 86400:  # < 1 day
        return 1.5
    else:
        return 1.0
```

## Circuit Breakers

### Trading Halts
```python
CIRCUIT_BREAKERS = {
    "daily_loss_halt": 2000,      # Stop trading if daily loss > $2,000
    "consecutive_losses": 5,       # Stop after 5 consecutive losing trades
    "venue_disconnect": True,      # Stop if venue adapter disconnects
    "stale_data_halt": 30,         # Stop if no book updates for 30s
    "high_latency_halt": 5000      # Stop if latency > 5s
}
```

### Auto-Resume Conditions
```python
def can_resume_trading() -> bool:
    checks = [
        daily_loss_under_limit(),
        venue_adapters_healthy(),
        book_data_fresh(),
        latency_acceptable(),
        manual_override_not_set()
    ]
    return all(checks)
```

## Position Management

### Automatic Unwinding
```python
UNWIND_TRIGGERS = {
    "unrealized_loss_threshold": 5000,    # Unwind if unrealized loss > $5,000
    "position_age_days": 7,               # Unwind positions older than 7 days
    "venue_disconnection": True,          # Unwind if venue goes offline
    "spec_invalidation": True             # Unwind if market pairing becomes invalid
}
```

### Unwind Strategy
```python
def unwind_position(position: Position) -> UnwindPlan:
    # Prefer closing via same venue if possible
    # Use market orders if necessary to exit quickly
    # Accept larger fees to reduce position risk
    # Log all unwind decisions for analysis
    pass
```

## Real-Time Monitoring

### Risk Alerts
```python
ALERT_THRESHOLDS = {
    "approaching_position_limit": 0.8,    # Alert at 80% of position limit
    "approaching_daily_limit": 0.9,       # Alert at 90% of daily turnover
    "unrealized_loss_warning": 3000,      # Warn if unrealized loss > $3,000
    "edge_deterioration": 100,             # Alert if edge drops by 1¢
    "latency_degradation": 1000           # Alert if latency > 1s
}
```

### Health Checks
```python
def perform_risk_health_check() -> RiskStatus:
    return RiskStatus(
        position_utilization=calculate_position_utilization(),
        daily_turnover_utilization=calculate_daily_utilization(),
        largest_single_exposure=get_largest_exposure(),
        unrealized_pnl=calculate_unrealized_pnl(),
        venue_connectivity=check_venue_health(),
        edge_opportunities=count_available_edges(),
        timestamp=time.time()
    )
```

## Configuration Management

### Environment-Based Limits
```python
RISK_CONFIGS = {
    "paper": {
        # Use same limits but with paper trading
        "max_total_exposure": 20000,
        "trade_execution": "simulated"
    },
    "sandbox": {
        # Reduced limits for sandbox testing
        "max_total_exposure": 1000,
        "max_daily_turnover": 2000,
        "trade_execution": "sandbox"
    },
    "live": {
        # Full production limits
        "max_total_exposure": 20000,
        "max_daily_turnover": 25000,
        "trade_execution": "live"
    }
}
```

### Override Capabilities
```python
class RiskOverride:
    """Temporary risk limit overrides with expiration"""
    override_type: str              # "increase_limit" | "disable_check"
    original_value: float
    override_value: float
    reason: str
    expires_at: int
    authorized_by: str
```

## Compliance and Reporting

### Daily Risk Report
```python
@dataclass
class DailyRiskReport:
    date: str
    total_trades: int
    gross_turnover: float
    net_pnl: float
    largest_position: float
    max_unrealized_loss: float
    risk_limit_breaches: list[str]
    average_edge_captured: float
    venue_uptime: dict[str, float]
```

### Audit Trail
- All risk limit breaches logged with context
- Position changes tracked with reasons
- Edge threshold adjustments documented
- Manual overrides require approval and expiration

## Testing and Validation

### Stress Testing
- Simulate large adverse moves in all positions
- Test circuit breaker activation and recovery
- Validate position limit enforcement
- Test unwind procedures under stress

### Backtesting Integration
- Apply risk limits to historical scenarios
- Measure impact of risk controls on profitability
- Optimize thresholds based on historical data
- Test edge deterioration scenarios