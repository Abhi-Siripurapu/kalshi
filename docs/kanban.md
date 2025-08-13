# 6-Day Build Kanban Board

## Day 1 - Foundations ✅ COMPLETED

### DONE ✅
- [x] Architecture decisions (DECISIONS.md)
- [x] Repo scaffolding and directory structure
- [x] Docker-compose setup with services
- [x] Canonical data schemas (docs/schemas.md)
- [x] Fee calculation rules and test cases (docs/fees.md)
- [x] Market matching policy (docs/matching.md)
- [x] Target market coverage plan (docs/coverage.md)
- [x] Risk management policies (docs/risk.md)
- [x] UI wireframes and specifications (docs/ui.md)
- [x] Operations and monitoring plan (docs/ops.md)
- [x] Environment configuration (.env.example)
- [x] Database schema (deploy/init.sql)

### Key Decisions Made
- Stack: Python/FastAPI + React/TypeScript + Redis + PostgreSQL
- Process architecture: Separate adapters + core API + UI
- Risk limits: $20K total exposure, $2K per event
- Edge thresholds: 2.5-4.0¢ depending on venue/fees
- 8 target markets identified for initial coverage

---

## Day 2 - Market Data Online

### TODO 📋
- [ ] **Kalshi Adapter Implementation**
  - [ ] WebSocket connection with authentication
  - [ ] Market discovery and subscription
  - [ ] Book snapshot + diff handling
  - [ ] Normalization to canonical schema
  - [ ] Health monitoring and reconnection
  - [ ] Redis publishing of normalized books

- [ ] **Polymarket Adapter Implementation**
  - [ ] API/WS connection setup (custodial or wallet)
  - [ ] Market discovery and subscription
  - [ ] Book data normalization
  - [ ] Health monitoring
  - [ ] Redis publishing

- [ ] **Core Infrastructure**
  - [ ] Redis book cache implementation
  - [ ] Parquet recorder for raw feeds
  - [ ] Basic API endpoints for book data
  - [ ] WebSocket server for UI updates

- [ ] **UI - Pairs Dashboard**
  - [ ] Connect to API via WebSocket
  - [ ] Display live pairs table
  - [ ] Show venue status indicators
  - [ ] Real-time price updates

### Acceptance Criteria
- Both adapters connect and maintain live books
- UI shows top-of-book within 500ms
- Feed latency < 1s consistently
- Books survive disconnect/reconnect

---

## Day 3 - Matching + Edge Calculation

### TODO 📋
- [ ] **Duplicate Matcher**
  - [ ] Candidate generation pipeline
  - [ ] Spec validation rules implementation
  - [ ] Manual override system (force/blacklist)
  - [ ] Confidence scoring algorithm
  - [ ] PostgreSQL persistence

- [ ] **Fee Engine**
  - [ ] Kalshi fee calculation with rounding
  - [ ] Polymarket fee handling (zero)
  - [ ] Per-market override support
  - [ ] Unit tests for all fee scenarios

- [ ] **Edge Calculator**
  - [ ] Net edge after fees and slippage
  - [ ] Depth-aware capacity calculation
  - [ ] Threshold enforcement
  - [ ] Real-time recalculation

- [ ] **UI Enhancements**
  - [ ] Spec validation indicators
  - [ ] Edge and capacity columns
  - [ ] Filtering and sorting
  - [ ] Pair detail modal

### Acceptance Criteria
- Matcher finds 3+ valid pairs from target markets
- Fee calculations match venue statements exactly
- Edge thresholds correctly filter opportunities
- UI shows profitable opportunities clearly

---

## Day 4 - Order Router (Paper Mode)

### TODO 📋
- [ ] **Order Management**
  - [ ] Order submission to both venues
  - [ ] Fill tracking and updates
  - [ ] Cancel/replace functionality
  - [ ] Status synchronization

- [ ] **Paired Execution Engine**
  - [ ] Make/take strategy implementation
  - [ ] Timeout and cancellation logic
  - [ ] Partial fill handling
  - [ ] Risk limit enforcement

- [ ] **Position & P&L System**
  - [ ] Position tracking per venue/outcome
  - [ ] P&L calculation (realized/unrealized)
  - [ ] Ledger entry creation
  - [ ] Portfolio aggregation

- [ ] **Paper Trading Mode**
  - [ ] Simulated fills against live books
  - [ ] Realistic latency simulation
  - [ ] Paper P&L tracking

- [ ] **UI - Orders & Positions**
  - [ ] Orders screen with live updates
  - [ ] Positions screen with P&L
  - [ ] Trade execution interface

### Acceptance Criteria
- Paper mode executes paired orders correctly
- Position tracking is accurate
- P&L calculations match expectations
- UI provides full order lifecycle visibility

---

## Day 5 - Live Trading Smoke Test

### TODO 📋
- [ ] **Live Trading Setup**
  - [ ] Sandbox/testnet configuration
  - [ ] Real API key integration
  - [ ] Small position size limits
  - [ ] Enhanced logging for debugging

- [ ] **Execution Testing**
  - [ ] Execute 1-2 small paired trades
  - [ ] Verify fees match calculations
  - [ ] Test cancellation scenarios
  - [ ] Validate rounding behavior

- [ ] **Monitoring & Alerting**
  - [ ] Real-time latency monitoring
  - [ ] Position limit alerts
  - [ ] Error notification system
  - [ ] Circuit breaker testing

- [ ] **Replay System**
  - [ ] Capture trading session data
  - [ ] Replay engine implementation
  - [ ] Strategy backtesting capability

### Acceptance Criteria
- Successfully execute paired trade on sandbox
- Fees match venue statements within 1¢
- Circuit breakers trigger correctly
- Replay produces identical results

---

## Day 6 - Polish and Demo

### TODO 📋
- [ ] **Hardening**
  - [ ] Connection resilience testing
  - [ ] Rate limiting implementation
  - [ ] Idempotency for critical operations
  - [ ] Comprehensive error handling

- [ ] **UI Polish**
  - [ ] Edge history charts/sparklines
  - [ ] Alert notification system
  - [ ] Settings panel completion
  - [ ] Mobile responsiveness

- [ ] **Documentation**
  - [ ] API documentation
  - [ ] User guide/walkthrough
  - [ ] Deployment instructions
  - [ ] Troubleshooting guide

- [ ] **Demo Preparation**
  - [ ] Screen recording of key workflows
  - [ ] Performance metrics dashboard
  - [ ] Sample arbitrage scenarios
  - [ ] Risk management demonstration

### Acceptance Criteria
- System runs stably for 4+ hours
- UI responsive and professional
- Demo showcases complete workflow
- Documentation enables others to run/extend

---

## Risk Mitigation

### Potential Blockers
- **API Rate Limits**: Implement proper throttling
- **WebSocket Instability**: Robust reconnection logic
- **Market Data Quality**: Validation and filtering
- **Venue Differences**: Careful spec matching
- **Performance Issues**: Profiling and optimization

### Contingency Plans
- **Day 2 Behind**: Focus on one venue first
- **Day 3 Behind**: Manual pair configuration
- **Day 4 Behind**: Paper mode only
- **Day 5 Behind**: Skip live trading
- **Day 6 Behind**: Minimal viable demo

### Success Metrics
- **Technical**: 95% uptime, <500ms latency
- **Business**: 3+ valid pairs, >75% fill rate
- **User**: Complete workflow demonstration
- **Deployment**: Docker-compose up success

---

## Daily Standup Template

### What was completed yesterday?
### What will be worked on today?
### Any blockers or risks?
### Dependencies needed from others?

---

## Definition of Done

### For Each Feature
- [ ] Code implemented and tested
- [ ] Documentation updated
- [ ] Error handling complete
- [ ] Performance acceptable
- [ ] UI/UX polished
- [ ] Integration tested

### For Day Completion
- [ ] All TODO items completed or consciously deferred
- [ ] Acceptance criteria met
- [ ] Next day's work can begin
- [ ] No critical blockers remain
- [ ] Demo-ready state achieved