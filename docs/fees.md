# Fee Calculation Rules

All fee calculations must be deterministic and match venue statements exactly. This document specifies the exact formulas and rounding behavior for each venue.

## Kalshi Fee Structure

### Base Formula
```
fee_cents = ceil(coeff × price_dollars × (1 - price_dollars) × quantity × 100)
```

Where:
- `coeff` = coefficient (maker or taker)
- `price_dollars` = price as decimal (0.0 to 1.0)
- `quantity` = number of contracts
- `ceil()` = round up to nearest integer
- Result in cents

### Coefficients
- **Taker Fee**: 0.07 (7%)
- **Maker Fee**: 
  - Most series: 0.00 (0%)
  - Specific series: 0.0175 (1.75%)

### Per-Market Overrides
Maintain a configuration list of markets where maker fees apply:
```json
{
  "maker_fee_markets": [
    "INXD-25JAN31",
    "FED-25MAR19",
    "specific_series_pattern"
  ]
}
```

### Rounding Rules
- **Per-fill rounding**: Each individual fill rounded up separately
- **Fewer fills preferred**: One 100-lot fill costs less than ten 10-lot fills
- **Minimum fee**: 1 cent per fill

## Polymarket Fee Structure

### Trading Fees
```
fee_cents = 0
```
No trading fees on Polymarket.

### Notes
- Gas costs and USDC approval costs are out-of-scope
- Rail fees (if any) are handled externally

## Implementation Functions

### Core Fee Calculator
```python
def calculate_fee_cents(venue_id: str, side: str, px_cents: int, qty: int, market_id: str = None) -> int:
    """
    Calculate fee in cents for a trade.
    
    Args:
        venue_id: "kalshi" | "polymarket"
        side: "maker" | "taker" 
        px_cents: Price in cents (0-10000)
        qty: Quantity of contracts
        market_id: Market identifier for fee overrides
        
    Returns:
        Fee in cents (integer)
    """
```

### Helper Functions
```python
def net_cost_cents(buys: list[Trade], sells: list[Trade], fees: list[int]) -> int:
    """Calculate net cost including fees"""

def net_edge_cents(cheap_px: int, dear_px: int, cheap_fee: int, dear_fee: int) -> int:
    """Calculate net edge after fees"""

def slippage_adjusted_edge(book_levels: list[Level], target_qty: int) -> int:
    """Calculate edge accounting for market depth"""
```

## Test Cases

### Kalshi Taker Fees
| Price (¢) | Qty | Price ($) | Fee Formula | Expected (¢) |
|-----------|-----|-----------|-------------|---------------|
| 4900 | 100 | 0.49 | ceil(0.07×0.49×0.51×100×100) | 175 |
| 5000 | 100 | 0.50 | ceil(0.07×0.50×0.50×100×100) | 175 |
| 5100 | 100 | 0.51 | ceil(0.07×0.51×0.49×100×100) | 175 |
| 2500 | 50 | 0.25 | ceil(0.07×0.25×0.75×50×100) | 66 |
| 7500 | 10 | 0.75 | ceil(0.07×0.75×0.25×10×100) | 14 |
| 1000 | 1 | 0.10 | ceil(0.07×0.10×0.90×1×100) | 1 |

### Kalshi Maker Fees (1.75% series)
| Price (¢) | Qty | Price ($) | Fee Formula | Expected (¢) |
|-----------|-----|-----------|-------------|---------------|
| 4900 | 100 | 0.49 | ceil(0.0175×0.49×0.51×100×100) | 44 |
| 5000 | 100 | 0.50 | ceil(0.0175×0.50×0.50×100×100) | 44 |
| 5100 | 100 | 0.51 | ceil(0.0175×0.51×0.49×100×100) | 44 |

### Kalshi Maker Fees (0% series)
| Price (¢) | Qty | Price ($) | Fee Formula | Expected (¢) |
|-----------|-----|-----------|-------------|---------------|
| 4900 | 100 | 0.49 | 0 | 0 |
| 5000 | 100 | 0.50 | 0 | 0 |
| ANY | ANY | ANY | 0 | 0 |

### Polymarket Fees
| Price (¢) | Qty | Side | Expected (¢) |
|-----------|-----|------|---------------|
| ANY | ANY | ANY | 0 |

### Edge Cases
| Scenario | Input | Expected | Notes |
|----------|-------|----------|-------|
| Minimum trade | 1¢, 1 qty | 1¢ | Always at least 1¢ fee |
| Maximum price | 9999¢, 100 qty | 1¢ | Near-certain outcome |
| Zero price | 1¢, 100 qty | 1¢ | Near-impossible outcome |
| Large quantity | 5000¢, 10000 qty | 1750¢ | Bulk trade |

## Validation Requirements

1. **Unit Tests**: All test cases above must pass exactly
2. **Rounding Verification**: Manual calculation matches venue statements
3. **Performance**: Fee calculation < 1ms for typical trades
4. **Deterministic**: Same inputs always produce same outputs
5. **Range Validation**: Inputs must be within valid bounds

## Configuration Management

### Fee Schedule Updates
```python
FEE_CONFIG = {
    "kalshi": {
        "taker_coeff": 0.07,
        "maker_coeff_default": 0.00,
        "maker_coeff_special": 0.0175,
        "special_markets": [
            "INXD-25JAN31",
            "FED-25MAR19"
        ]
    },
    "polymarket": {
        "trading_fee": 0.0
    }
}
```

### Runtime Overrides
Support for temporary fee schedule changes:
```python
def set_fee_override(venue_id: str, market_id: str, maker_coeff: float, taker_coeff: float):
    """Temporarily override fees for specific market"""
```

## Monitoring and Alerts

1. **Fee Accuracy**: Alert if calculated fees deviate from venue statements
2. **Performance**: Alert if fee calculation takes > 10ms
3. **Configuration**: Alert on fee schedule changes
4. **Edge Validation**: Alert if net edge calculation seems incorrect

## Future Considerations

- Support for fee rebates/rewards programs
- Dynamic fee schedules based on volume
- Cross-venue fee optimization strategies
- Tax implications of fee structures