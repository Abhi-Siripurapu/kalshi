# UI/UX Wireframes and Specifications

This document defines the exact layouts, data flows, and interactions for each screen in the terminal. Focus on information density, real-time updates, and professional trading aesthetics.

## Global Layout

### Header Bar (Always Visible)
```
┌─ Kalshi Terminal ─────────────────────────────────────────────────────────┐
│ [🟢 Kalshi] [🟡 Polymarket] [🔴 Redis] │ Balance: $45,234 │ P&L: +$234 │ ⚙️ │
└───────────────────────────────────────────────────────────────────────────┘
```

**Components:**
- **Venue Status Indicators**: Green (connected), Yellow (degraded), Red (disconnected)
- **Real-time Balance**: Total available balance across venues
- **Session P&L**: Realized + unrealized P&L for current session
- **Settings Button**: Access to configuration panel

### Navigation Tabs
```
┌─ [📊 Pairs] [📋 Orders] [💰 Positions] [⚠️ Alerts] [📈 Analytics] ─────┐
```

## 1. Pairs Dashboard (Primary Screen)

### Layout Structure
```
┌─ Filter Bar ──────────────────────────────────────────────────────────┐
│ Category: [All ▼] │ Min Edge: [2.5¢] │ Spec OK: [✅] │ [🔄 Refresh] │
├─ Pairs Table ────────────────────────────────────────────────────────┤
│ Pair Name          │Edge│Cap│Spec│Age│ Kalshi      │ Polymarket   │▶│
│ Fed Rate Mar 2025  │3.2¢│2K │ ✅ │12s│ 52.1 → 51.8│ 48.9 → 49.2 │●│
│ CPI Jan Release    │4.1¢│1.5K│ ✅ │5s │ 67.2 → 66.8│ 63.1 → 63.7 │●│
│ NVIDIA Q4 Earnings │2.8¢│800│ ❓ │45s│ 41.3 → 41.1│ 38.5 → 38.9 │○│
│ Bitcoin >$150K Q1  │5.2¢│3K │ ✅ │2s │ 23.4 → 23.6│ 18.2 → 18.8 │●│
├─ Quick Stats ─────────────────────────────────────────────────────────┤
│ Active Pairs: 12 │ Avg Edge: 3.4¢ │ Total Capacity: $18.3K │ Opps: 4 │
└───────────────────────────────────────────────────────────────────────┘
```

### Column Definitions
- **Pair Name**: Market description (truncated, hover for full)
- **Edge**: Net edge in cents after fees and estimated slippage
- **Cap**: Available capacity (minimum depth across both legs)
- **Spec**: Spec match status (✅ Pass, ❓ Review, ❌ Fail)
- **Age**: Time since last price update
- **Venue Columns**: Best bid → best ask for each venue
- **Trade Button**: ● (enabled), ○ (disabled), - (no opportunity)

### Color Coding
- **Green rows**: Edge ≥ threshold, spec OK, ready to trade
- **Yellow rows**: Edge marginal or spec under review
- **Red rows**: Spec failed or stale data
- **Gray rows**: No current opportunity

### Sorting and Filtering
- **Default Sort**: By edge (descending)
- **Category Filter**: Macro, Tech, Sports, Politics, Crypto, Weather
- **Edge Filter**: Minimum edge threshold slider
- **Spec Filter**: Only show spec-validated pairs
- **Capacity Filter**: Minimum capacity threshold

### Real-time Updates
- **Price Updates**: WebSocket feed, highlight changed cells
- **Edge Recalculation**: Automatic when prices change
- **New Pairs**: Slide in at top with highlight animation
- **Removed Pairs**: Fade out over 2 seconds

## 2. Pair Detail View (Modal/Side Panel)

### Triggered By
- Click on any row in pairs table
- Click trade button (●)

### Layout Structure
```
┌─ Fed Rate March 2025 Decision ─────────────────────────────────── [×] ┐
├─ Market Info ──────────────────────────────────────────────────────────┤
│ Resolution: Fed announcement, Mar 19 2025, 2:00 PM ET                 │
│ Source: federalreserve.gov                                             │
│ Spec Match: ✅ Identical FOMC decision criteria                        │
├─ Live Books ───────────────────────────────────────────────────────────┤
│     Kalshi (YES)              │              Polymarket (YES)         │
│ Size │ Bid  │ Ask  │ Size     │     Size │ Bid  │ Ask  │ Size         │
│  500 │ 52.1 │ 52.4 │  200     │      300 │ 48.9 │ 49.2 │  450         │
│  200 │ 52.0 │ 52.5 │  300     │      150 │ 48.8 │ 49.3 │  200         │
│  100 │ 51.9 │ 52.6 │  150     │      100 │ 48.7 │ 49.4 │  300         │
├─ Trade Plan ───────────────────────────────────────────────────────────┤
│ Strategy: Make Kalshi @ 52.0¢, Take Polymarket @ 49.2¢                │
│ Size: [___500__] (max: 800 based on depth)                            │
│ Net Edge: 2.8¢ per share = $14.00 profit                             │
│ Timeout: [___60s___]                                                   │
│ Risk: Low │ Fees: K=$0, P=$0 │ Slippage: ~0.1¢                       │
├─ Execution ────────────────────────────────────────────────────────────┤
│ [Paper Trade] [Live Trade] [Add to Watchlist]                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Components
1. **Market Info**: Resolution details, source verification, spec status
2. **Live Books**: Side-by-side order books with depth
3. **Trade Plan**: Proposed execution strategy with size slider
4. **Risk Assessment**: Quick risk/reward summary
5. **Execution Buttons**: Paper, live, or watchlist options

### Size Slider Logic
- **Maximum**: Constrained by depth, position limits, risk limits
- **Suggested**: Optimal based on edge/risk ratio
- **Real-time Update**: Edge and profit recalculated as size changes

## 3. Orders Screen

### Layout Structure
```
┌─ Order Management ────────────────────────────────────────────────────┐
├─ Active Orders ───────────────────────────────────────────────────────┤
│ID │Pair│Side│Size│Price│Status │Filled│Age│Venue│     │Actions │
│123│Fed │Make│500 │52.0¢│Open   │0     │15s│Kalshi│     │[Cancel]│
│124│Fed │Take│500 │49.2¢│Pending│0     │2s │Poly  │     │[Wait]  │
│125│CPI │Make│300 │67.0¢│Partial│100   │45s│Kalshi│33%  │[Cancel]│
├─ Recent Fills ────────────────────────────────────────────────────────┤
│Time │Pair│Side │Size│Price│Fee│Flag │Venue │PnL  │
│14:23│Fed │Make │200 │52.1¢│$0 │Maker│Kalshi│     │
│14:23│Fed │Take │200 │49.1¢│$0 │Taker│Poly  │+$6.00│
│14:20│CPI │Make │150 │66.8¢│$0 │Maker│Kalshi│     │
│14:20│CPI │Take │150 │63.2¢│$0 │Taker│Poly  │+$5.40│
├─ Order Stats ─────────────────────────────────────────────────────────┤
│Today: 8 trades │ Fill Rate: 87% │ Avg Hold: 23s │ Failed: 1 │
└───────────────────────────────────────────────────────────────────────┘
```

### Order Status Colors
- **Green**: Successfully filled
- **Blue**: Open and working
- **Yellow**: Partially filled
- **Red**: Rejected or failed
- **Gray**: Cancelled

### Real-time Updates
- **Status Changes**: Instant updates via WebSocket
- **Fill Notifications**: Toast notifications for fills
- **Failed Orders**: Alert banner for failures

## 4. Positions Screen

### Layout Structure
```
┌─ Position Management ─────────────────────────────────────────────────┐
├─ Current Positions ───────────────────────────────────────────────────┤
│Pair            │Venue    │Side│Qty │Cost │Current│Unrealized│Days│
│Fed Rate Mar 25 │Kalshi   │Long│+200│52.1¢│52.3¢  │+$4.00    │0.1 │
│Fed Rate Mar 25 │Polymarket│Short│-200│49.1¢│49.0¢ │+$2.00    │0.1 │
│├─ Net Fed Rate │Combined │Net │±0  │—    │—     │+$6.00    │0.1 │
│CPI Jan Release │Kalshi   │Long│+100│66.8¢│67.1¢  │+$3.00    │0.3 │
│CPI Jan Release │Polymarket│Short│-100│63.2¢│63.5¢ │-$3.00    │0.3 │
│├─ Net CPI Jan  │Combined │Net │±0  │—    │—     │+$0.00    │0.3 │
├─ P&L Summary ─────────────────────────────────────────────────────────┤
│ Session │ Today │ Week │ Month │ All Time │
│ +$23.45 │ +$234 │ +$567│ +$1234│ +$1234   │
│ Realized: +$189.34 │ Unrealized: +$44.66 │ Fees Paid: $23.45 │
├─ Risk Metrics ────────────────────────────────────────────────────────┤
│ Gross Exposure: $12,345 │ Net Exposure: $234 │ Max Drawdown: -$45 │
│ Utilization: 62% of limits │ Largest Position: $2,345 (Fed Rate)   │
└───────────────────────────────────────────────────────────────────────┘
```

### Position Grouping
- **Individual Positions**: Per venue and outcome
- **Net Positions**: Paired positions combined
- **Portfolio View**: Aggregate risk metrics

### P&L Attribution
- **Realized**: From closed positions
- **Unrealized**: Mark-to-market on open positions  
- **Fees**: Total fees paid across venues
- **Time Periods**: Session, daily, weekly, monthly views

## 5. Alerts Screen

### Layout Structure
```
┌─ System Alerts ───────────────────────────────────────────────────────┐
├─ Active Alerts ───────────────────────────────────────────────────────┤
│⚠️ │14:23│Kalshi connection degraded (latency 2.1s)          │[Ack]│
│🔴 │14:20│Position limit approaching: 89% of Fed Rate limit   │[Ack]│
│🟡 │14:18│New arbitrage: Bitcoin >$150K (4.2¢ edge)          │[View]│
│ℹ️ │14:15│CPI market spec invalidated (measurement change)   │[Ack]│
├─ Alert History ───────────────────────────────────────────────────────┤
│Time │Level│Message                                          │Status│
│14:10│Info │Fed Rate pair edge increased to 3.8¢            │Ack   │
│14:05│Warn │Polymarket feed stale (15s since last update)   │Auto  │
│14:00│Error│Order #123 rejected: insufficient balance       │Ack   │
├─ Alert Settings ──────────────────────────────────────────────────────┤
│ Edge Opportunities: ✅ │ System Health: ✅ │ Position Limits: ✅    │
│ Order Updates: ✅      │ P&L Milestones: ❌ │ Market Changes: ✅     │
└───────────────────────────────────────────────────────────────────────┘
```

### Alert Categories
- **🔴 Critical**: System failures, position breaches
- **⚠️ Warning**: Degraded performance, approaching limits
- **🟡 Opportunity**: New arbitrage opportunities
- **ℹ️ Info**: General market updates, configuration changes

### Alert Actions
- **Acknowledge**: Mark as read
- **View**: Navigate to relevant screen
- **Snooze**: Temporarily suppress similar alerts
- **Auto-clear**: Alerts that resolve automatically

## 6. Settings Screen

### Layout Structure
```
┌─ Configuration ───────────────────────────────────────────────────────┐
├─ Risk Limits ─────────────────────────────────────────────────────────┤
│ Max Position per Event: [$2,000    ] │ Max Daily Turnover: [$25,000  ]│
│ Edge Thresholds:                                                       │
│   Kalshi Taker Required: [3.5¢] │ Kalshi Maker (no fee): [2.5¢]     │
│   Kalshi Maker (with fee): [4.0¢] │ Polymarket Only: [2.0¢]         │
├─ Venue Configuration ─────────────────────────────────────────────────┤
│ Kalshi API Key: [••••••••••••••••••••] │ Environment: [Sandbox ▼]   │
│ Polymarket Config: [••••••••••••••••••] │ Auth Method: [Custodial ▼] │
├─ Market Matching ─────────────────────────────────────────────────────┤
│ Auto-match Confidence: [75%] │ Manual Review Required: ✅            │
│ Similarity Threshold: [0.75] │ Spec Check Strictness: [High ▼]      │
├─ UI Preferences ──────────────────────────────────────────────────────┤
│ Theme: [Dark ▼] │ Refresh Rate: [1s ▼] │ Sound Alerts: ✅           │
│ Default Sort: [Edge ▼] │ Decimal Places: [1 ▼] │ Time Zone: [ET ▼] │
├─ Pair Overrides ──────────────────────────────────────────────────────┤
│ [Fed Rate Mar 25] → [0x1234...] │ Force Paired │ [Remove]            │
│ [CPI Blacklist ] → [0x5678...] │ Blacklisted  │ [Remove]            │
│ [+ Add Override]                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## Responsive Design

### Breakpoints
- **Large**: 1920px+ (full feature set)
- **Medium**: 1200-1919px (condensed columns)
- **Small**: 768-1199px (stacked layouts)
- **Mobile**: <768px (simplified views)

### Key Adaptations
- **Pairs Table**: Horizontally scrollable on medium/small
- **Detail Modal**: Full-screen on mobile
- **Order Book**: Single venue at a time on small screens
- **Charts**: Simplified on mobile

## Color Scheme (Dark Theme)

### Primary Colors
- **Background**: #0f172a (slate-900)
- **Surface**: #1e293b (slate-800)
- **Border**: #334155 (slate-700)
- **Text Primary**: #f8fafc (slate-50)
- **Text Secondary**: #94a3b8 (slate-400)

### Status Colors
- **Success/Green**: #10b981 (emerald-500)
- **Warning/Yellow**: #f59e0b (amber-500)
- **Error/Red**: #ef4444 (red-500)
- **Info/Blue**: #3b82f6 (blue-500)

### Data Visualization
- **Profit**: #10b981 (green)
- **Loss**: #ef4444 (red)
- **Neutral**: #6b7280 (gray-500)
- **Accent**: #8b5cf6 (violet-500)

## Performance Requirements

### Real-time Updates
- **Latency**: <100ms from feed to UI update
- **Frame Rate**: 60fps for animations
- **Memory**: <500MB total footprint
- **CPU**: <5% during normal operation

### Data Efficiency
- **WebSocket**: Incremental updates only
- **Compression**: gzip for all API responses
- **Caching**: Aggressive caching of static data
- **Pagination**: Large datasets paginated/virtualized