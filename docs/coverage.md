# Target Market Coverage

This document defines the first 8-10 markets we'll monitor for arbitrage opportunities. Each market is selected for high liquidity, clear resolution criteria, and likely cross-venue presence.

## Selection Criteria

1. **Spec-Identical**: Must resolve identically across venues
2. **High Volume**: Regular trading activity on both venues
3. **Clear Resolution**: Unambiguous resolution source and criteria
4. **Time Horizon**: Mix of short-term (days) and medium-term (months)
5. **Category Diversity**: Spread across macro, tech, politics, sports

## Target Markets

### 1. Federal Reserve Rate Decisions
**Event**: March 2025 FOMC Meeting
- **Kalshi ID**: `FED-25MAR19` (example)
- **Polymarket**: Search for "Fed rate March 2025"
- **Resolution Source**: Federal Reserve official announcement
- **Resolution Time**: March 19, 2025, ~2:00 PM ET
- **Outcome Type**: Binary (rate cut vs no cut)
- **Spec Match**: ✅ Identical FOMC decision criteria
- **Expected Volume**: High (macro event)

### 2. Consumer Price Index (CPI) 
**Event**: January 2025 CPI Report (December data)
- **Kalshi ID**: `CPI-25JAN15` (example)
- **Polymarket**: Search for "CPI December 2024"
- **Resolution Source**: Bureau of Labor Statistics (BLS.gov)
- **Resolution Time**: January 15, 2025, 8:30 AM ET
- **Outcome Type**: Binary or bins (above/below threshold)
- **Spec Match**: ✅ Same BLS data source, same measurement
- **Expected Volume**: High (macro event)

### 3. AI Model Performance
**Event**: GPT-5 Release by End of Q1 2025
- **Kalshi ID**: TBD
- **Polymarket**: Search for "GPT-5 2025 Q1"
- **Resolution Source**: Official OpenAI announcement
- **Resolution Time**: March 31, 2025, 11:59 PM PT
- **Outcome Type**: Binary (released vs not released)
- **Spec Match**: ⚠️ Need to verify identical release criteria
- **Expected Volume**: Medium-High (tech interest)

### 4. Earnings Results
**Event**: NVIDIA Q4 2024 Earnings Beat
- **Kalshi ID**: TBD
- **Polymarket**: Search for "NVIDIA earnings Q4"
- **Resolution Source**: NVIDIA official earnings call/SEC filing
- **Resolution Time**: Late January/Early February 2025
- **Outcome Type**: Binary (beat consensus vs miss)
- **Spec Match**: ⚠️ Need identical consensus definition
- **Expected Volume**: High (popular stock)

### 5. Weather Events
**Event**: Temperature Records in Major Cities
- **Kalshi ID**: TBD
- **Polymarket**: Weather category
- **Resolution Source**: National Weather Service (NOAA)
- **Resolution Time**: Various dates
- **Outcome Type**: Binary (record high/low vs not)
- **Spec Match**: ✅ Same NOAA measurement stations
- **Expected Volume**: Medium

### 6. Cryptocurrency Prices
**Event**: Bitcoin Price Above $150K by End of Q1 2025
- **Kalshi ID**: TBD
- **Polymarket**: Search for "Bitcoin 150k Q1"
- **Resolution Source**: Specific exchange price (need to match)
- **Resolution Time**: March 31, 2025, 11:59 PM UTC
- **Outcome Type**: Binary (above vs below threshold)
- **Spec Match**: ⚠️ Must use identical price source
- **Expected Volume**: High

### 7. Political Events
**Event**: US Government Shutdown in 2025
- **Kalshi ID**: TBD
- **Polymarket**: Search for "government shutdown 2025"
- **Resolution Source**: Official government status
- **Resolution Time**: Various (when funding expires)
- **Outcome Type**: Binary (shutdown vs funded)
- **Spec Match**: ✅ Clear government operational status
- **Expected Volume**: High during funding debates

### 8. Sports Outcomes
**Event**: Super Bowl LIX Winner
- **Kalshi ID**: TBD
- **Polymarket**: NFL category
- **Resolution Source**: Official NFL/game result
- **Resolution Time**: February 9, 2025
- **Outcome Type**: Categorical (team selection)
- **Spec Match**: ✅ Same game, same official result
- **Expected Volume**: Very High

## Market Configuration

### Mapping Tags Structure
```json
{
    "fed_rate": {
        "category": "macro",
        "subcategory": "monetary_policy", 
        "entity": "federal_reserve",
        "event_type": "rate_decision",
        "meeting_date": "2025-03-19"
    },
    "cpi": {
        "category": "macro",
        "subcategory": "inflation",
        "entity": "bls",
        "event_type": "data_release",
        "data_period": "2024-12",
        "measurement": "mom" | "yoy"
    },
    "earnings": {
        "category": "corporate",
        "subcategory": "earnings",
        "entity": "nvidia",
        "period": "2024-Q4",
        "metric": "beat_consensus"
    }
}
```

### Priority Order (Implementation)
1. **Fed Rate** - Highest priority, clear resolution
2. **CPI** - High volume, spec-identical across venues
3. **Super Bowl** - Time-bounded, massive volume
4. **NVIDIA Earnings** - Popular, liquid
5. **Bitcoin Price** - High volatility, active trading
6. **Government Shutdown** - Event-driven opportunity
7. **Weather Records** - Lower volume but good testing
8. **AI Model Release** - Tech community interest

## Validation Checklist

For each target market, verify:
- [ ] Both venues offer this market type
- [ ] Resolution criteria are identical
- [ ] Resolution source is the same
- [ ] Timing matches exactly (timezone considered)
- [ ] Historical volume indicates liquidity
- [ ] No venue-specific disclaimers that create differences

## Market Discovery Process

### Daily Monitoring
1. Check Kalshi new markets API
2. Monitor Polymarket recent markets
3. Cross-reference against target categories
4. Run matching algorithm on new discoveries
5. Update target list with promising markets

### Market Intelligence Sources
- Kalshi market calendar
- Polymarket trending markets
- Economic calendar (Fed meetings, CPI releases)
- Earnings calendar (major tech companies)
- Sports schedules (NFL, NBA playoffs)
- Political event calendar (elections, policy deadlines)

## Risk Assessment Per Market

### Low Risk
- Fed rate decisions (binary, clear resolution)
- CPI releases (objective BLS data)
- Sports outcomes (official game results)

### Medium Risk  
- Earnings beats (consensus definition varies)
- Weather records (measurement station differences)
- Government shutdowns (definition edge cases)

### Higher Risk
- AI model releases (subjective "release" criteria)
- Crypto prices (exchange price variations)
- Political events (interpretation differences)

## Success Metrics

- **Coverage Rate**: % of target markets with active pairs
- **Spec Accuracy**: % of identified pairs that are truly identical
- **Volume Capture**: % of available arbitrage volume captured
- **Latency**: Time from market appearance to pair identification
- **False Positive Rate**: Pairs identified but not truly identical

## Next Steps for Implementation

1. **API Integration**: Connect to both venue APIs for market discovery
2. **Market Scraping**: Build scrapers for market lists and details
3. **Matching Pipeline**: Implement the matching algorithm from docs/matching.md
4. **Manual Verification**: Human review of first 20-30 pairs
5. **Automated Monitoring**: Set up alerts for new markets in target categories