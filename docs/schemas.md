# Canonical Data Schemas

All data flowing through the system uses these canonical schemas. Adapters normalize venue-specific data to these formats.

## Core Entities

### Venue
```python
{
    "id": str,                    # "kalshi" | "polymarket"
    "name": str,                  # "Kalshi" | "Polymarket"
    "fee_schedule": dict,         # See fee calculation rules
    "tick_size": int,             # Minimum price increment (cents)
    "lot_size": int,              # Minimum quantity increment
    "maker_fee": float,           # Default maker fee coefficient
    "taker_fee": float,           # Default taker fee coefficient
    "rounding_rule": str          # "up" | "down" | "nearest"
}
```

### Market
```python
{
    "venue_id": str,              # Reference to venue
    "market_id": str,             # Venue-specific market identifier
    "title": str,                 # Human-readable title
    "description": str,           # Full market description
    "resolution_source": str,     # URL or description of resolution source
    "resolution_ts": int,         # Unix timestamp (UTC) when market resolves
    "timezone": str,              # Timezone for resolution (e.g., "US/Eastern")
    "currency": str,              # "USD"
    "outcomes": list[Outcome],    # List of tradeable outcomes
    "created_ts": int,            # Market creation timestamp
    "status": str                 # "active" | "resolved" | "cancelled"
}
```

### Outcome
```python
{
    "id": str,                    # Unique outcome identifier within market
    "label": str,                 # "YES" | "NO" | specific answer
    "type": str,                  # "binary" | "categorical"
    "mapping_tags": dict          # Structured tags for matching
    # Example mapping_tags:
    # {
    #   "company": "google",
    #   "model": "gemini-2.5-pro", 
    #   "metric": "revenue",
    #   "period": "2025-Q1",
    #   "threshold": "100B"
    # }
}
```

### Book
```python
{
    "market_id": str,             # Market identifier
    "outcome_id": str,            # Outcome identifier
    "venue_id": str,              # Venue identifier
    "ts_ns": int,                 # Nanosecond timestamp
    "side": str,                  # "bid" | "ask"
    "levels": list[Level],        # Ordered price levels
    "best_bid": int,              # Best bid price in cents (None if no bids)
    "best_ask": int,              # Best ask price in cents (None if no asks)
    "mid_px": float,              # Mid price in cents (None if no market)
    "sequence": int               # Sequence number for ordering
}
```

### Level
```python
{
    "px_cents": int,              # Price in cents (0-10000 for 0-100%)
    "qty": int,                   # Quantity available
    "venue_order_id": str         # Optional: venue order ID at this level
}
```

### Trade
```python
{
    "venue_id": str,              # Venue where trade occurred
    "market_id": str,             # Market identifier
    "outcome_id": str,            # Outcome identifier
    "trade_id": str,              # Venue-specific trade ID
    "side": str,                  # "buy" | "sell"
    "px_cents": int,              # Execution price in cents
    "qty": int,                   # Executed quantity
    "fee_cents": int,             # Fee paid in cents
    "liquidity_flag": str,        # "maker" | "taker"
    "ts_ns": int,                 # Execution timestamp (nanoseconds)
    "order_id": str               # Optional: associated order ID
}
```

### Order
```python
{
    "client_order_id": str,       # Our internal order ID
    "venue_order_id": str,        # Venue's order ID (set after submission)
    "venue_id": str,              # Target venue
    "market_id": str,             # Market identifier
    "outcome_id": str,            # Outcome identifier
    "side": str,                  # "buy" | "sell"
    "type": str,                  # "limit" | "market"
    "px_cents": int,              # Limit price in cents
    "qty": int,                   # Order quantity
    "tif": str,                   # "GTC" | "IOC" | "FOK"
    "status": str,                # "pending" | "open" | "filled" | "cancelled" | "rejected"
    "filled_qty": int,            # Quantity filled so far
    "avg_fill_px": float,         # Average fill price in cents
    "created_ts": int,            # Order creation timestamp
    "updated_ts": int             # Last status update timestamp
}
```

### Fill
```python
{
    "fill_id": str,               # Unique fill identifier
    "order_id": str,              # Associated order ID
    "venue_id": str,              # Execution venue
    "market_id": str,             # Market identifier
    "outcome_id": str,            # Outcome identifier
    "side": str,                  # "buy" | "sell"
    "px_cents": int,              # Fill price in cents
    "qty": int,                   # Fill quantity
    "fee_cents": int,             # Fee for this fill
    "liquidity_flag": str,        # "maker" | "taker"
    "ts_ns": int                  # Fill timestamp (nanoseconds)
}
```

### Ledger Entry
```python
{
    "entry_id": str,              # Unique ledger entry ID
    "venue_id": str,              # Venue where change occurred
    "ts_ns": int,                 # Transaction timestamp
    "delta_cash_cents": int,      # Cash change in cents (can be negative)
    "delta_shares": dict,         # Share changes by outcome_id
    "fee_cents": int,             # Fee component of this entry
    "reason": str,                # "fill" | "deposit" | "withdrawal" | "settlement"
    "link_id": str,               # Reference to order/fill/etc
    "notes": str                  # Optional additional context
}
```

### Position
```python
{
    "venue_id": str,              # Venue where position is held
    "market_id": str,             # Market identifier
    "outcome_id": str,            # Outcome identifier
    "net_qty": int,               # Net position quantity (positive = long)
    "avg_cost_cents": float,      # Average cost basis in cents
    "mtm_px_cents": int,          # Mark-to-market price in cents
    "realized_pnl_cents": int,    # Realized P&L in cents
    "unrealized_pnl_cents": int,  # Unrealized P&L in cents
    "last_updated_ts": int        # Last position update timestamp
}
```

## Price Conventions

- **Storage**: All prices stored as integers in cents (0-10000 representing 0-100%)
- **Display**: Convert to user-friendly formats in UI
- **Probability Conversion**: `probability = price_cents / 100.0`
- **Complement Pricing**: `complement_price = 10000 - price_cents`

## Message Types

### Market Data Messages
```python
{
    "type": "book_snapshot" | "book_update" | "trade",
    "venue_id": str,
    "data": Book | Trade,
    "ts_received_ns": int         # When we received this message
}
```

### Order Management Messages  
```python
{
    "type": "order_ack" | "order_reject" | "fill" | "cancel_ack",
    "venue_id": str,
    "data": Order | Fill | dict,
    "ts_received_ns": int
}
```

### System Health Messages
```python
{
    "type": "venue_status" | "latency_update",
    "venue_id": str,
    "status": "healthy" | "degraded" | "disconnected",
    "latency_ms": float,
    "ts_ns": int
}
```

## Validation Rules

1. **Price Bounds**: All prices must be 0 ≤ px_cents ≤ 10000
2. **Quantity**: All quantities must be positive integers
3. **Timestamps**: All timestamps in nanoseconds since Unix epoch
4. **IDs**: All IDs must be non-empty strings
5. **Enums**: All enum fields must match specified values exactly

## Schema Evolution

- Fields can be added with default values
- Fields cannot be removed without migration
- Enum values can be added but not removed
- Type changes require new schema version