-- Initial database schema for Kalshi Terminal
-- Run on PostgreSQL 15+

-- Create database if not exists (handled by docker-compose)
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Venues table
CREATE TABLE venues (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    fee_schedule JSONB NOT NULL DEFAULT '{}',
    tick_size INTEGER NOT NULL DEFAULT 1,
    lot_size INTEGER NOT NULL DEFAULT 1,
    maker_fee DECIMAL(6,4) NOT NULL DEFAULT 0.0000,
    taker_fee DECIMAL(6,4) NOT NULL DEFAULT 0.0000,
    rounding_rule VARCHAR(20) NOT NULL DEFAULT 'up',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Markets table
CREATE TABLE markets (
    venue_id VARCHAR(50) NOT NULL REFERENCES venues(id),
    market_id VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    resolution_source TEXT,
    resolution_ts TIMESTAMPTZ,
    timezone VARCHAR(50),
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    outcomes JSONB NOT NULL DEFAULT '[]',
    mapping_tags JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (venue_id, market_id)
);

-- Orders table
CREATE TABLE orders (
    client_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_order_id VARCHAR(100),
    venue_id VARCHAR(50) NOT NULL REFERENCES venues(id),
    market_id VARCHAR(100) NOT NULL,
    outcome_id VARCHAR(100) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    type VARCHAR(10) NOT NULL CHECK (type IN ('limit', 'market')),
    px_cents INTEGER NOT NULL CHECK (px_cents >= 0 AND px_cents <= 10000),
    qty INTEGER NOT NULL CHECK (qty > 0),
    tif VARCHAR(10) NOT NULL DEFAULT 'GTC',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    filled_qty INTEGER NOT NULL DEFAULT 0,
    avg_fill_px DECIMAL(8,2) DEFAULT NULL,
    created_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pair_id UUID DEFAULT NULL,
    FOREIGN KEY (venue_id, market_id) REFERENCES markets(venue_id, market_id)
);

-- Fills table
CREATE TABLE fills (
    fill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(client_order_id),
    venue_id VARCHAR(50) NOT NULL REFERENCES venues(id),
    market_id VARCHAR(100) NOT NULL,
    outcome_id VARCHAR(100) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    px_cents INTEGER NOT NULL CHECK (px_cents >= 0 AND px_cents <= 10000),
    qty INTEGER NOT NULL CHECK (qty > 0),
    fee_cents INTEGER NOT NULL DEFAULT 0,
    liquidity_flag VARCHAR(10) NOT NULL CHECK (liquidity_flag IN ('maker', 'taker')),
    ts_ns BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ledger table
CREATE TABLE ledger (
    entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_id VARCHAR(50) NOT NULL REFERENCES venues(id),
    ts_ns BIGINT NOT NULL,
    delta_cash_cents INTEGER NOT NULL,
    delta_shares JSONB NOT NULL DEFAULT '{}',
    fee_cents INTEGER NOT NULL DEFAULT 0,
    reason VARCHAR(50) NOT NULL,
    link_id UUID,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Positions table
CREATE TABLE positions (
    venue_id VARCHAR(50) NOT NULL REFERENCES venues(id),
    market_id VARCHAR(100) NOT NULL,
    outcome_id VARCHAR(100) NOT NULL,
    net_qty INTEGER NOT NULL DEFAULT 0,
    avg_cost_cents DECIMAL(8,2) DEFAULT NULL,
    mtm_px_cents INTEGER DEFAULT NULL,
    realized_pnl_cents INTEGER NOT NULL DEFAULT 0,
    unrealized_pnl_cents INTEGER NOT NULL DEFAULT 0,
    last_updated_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (venue_id, market_id, outcome_id),
    FOREIGN KEY (venue_id, market_id) REFERENCES markets(venue_id, market_id)
);

-- Duplicate pairs table
CREATE TABLE duplicate_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kalshi_market_id VARCHAR(100) NOT NULL,
    polymarket_market_id VARCHAR(100) NOT NULL,
    similarity_score DECIMAL(4,3) NOT NULL CHECK (similarity_score >= 0 AND similarity_score <= 1),
    spec_ok BOOLEAN NOT NULL DEFAULT FALSE,
    confidence DECIMAL(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    checks JSONB NOT NULL DEFAULT '[]',
    notes TEXT,
    override_type VARCHAR(20) CHECK (override_type IN ('force', 'blacklist')),
    last_updated_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(kalshi_market_id, polymarket_market_id)
);

-- System health table
CREATE TABLE system_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('healthy', 'degraded', 'down')),
    details JSONB NOT NULL DEFAULT '{}',
    check_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Configuration table
CREATE TABLE configuration (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Indexes for performance
CREATE INDEX idx_orders_venue_status ON orders(venue_id, status);
CREATE INDEX idx_orders_created_ts ON orders(created_ts);
CREATE INDEX idx_orders_pair_id ON orders(pair_id) WHERE pair_id IS NOT NULL;

CREATE INDEX idx_fills_order_id ON fills(order_id);
CREATE INDEX idx_fills_ts_ns ON fills(ts_ns);
CREATE INDEX idx_fills_venue_market ON fills(venue_id, market_id);

CREATE INDEX idx_ledger_venue_ts ON ledger(venue_id, ts_ns);
CREATE INDEX idx_ledger_reason ON ledger(reason);

CREATE INDEX idx_positions_venue ON positions(venue_id);
CREATE INDEX idx_positions_updated ON positions(last_updated_ts);

CREATE INDEX idx_duplicate_pairs_spec_ok ON duplicate_pairs(spec_ok);
CREATE INDEX idx_duplicate_pairs_updated ON duplicate_pairs(last_updated_ts);

CREATE INDEX idx_system_health_service_ts ON system_health(service, check_ts);

CREATE INDEX idx_markets_venue_status ON markets(venue_id, status);
CREATE INDEX idx_markets_resolution_ts ON markets(resolution_ts);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_venues_updated_at BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data
INSERT INTO venues (id, name, fee_schedule, maker_fee, taker_fee) VALUES 
('kalshi', 'Kalshi', '{"taker": 0.07, "maker_default": 0.0, "maker_special": 0.0175}', 0.0000, 0.0700),
('polymarket', 'Polymarket', '{"trading_fee": 0.0}', 0.0000, 0.0000);

-- Initial configuration
INSERT INTO configuration (key, value, description) VALUES
('risk_limits', '{"max_position_per_event": 2000, "max_daily_turnover": 25000, "max_total_exposure": 20000}', 'Risk management limits'),
('edge_thresholds', '{"kalshi_taker": 350, "kalshi_maker": 250, "kalshi_maker_fee": 400, "polymarket": 200}', 'Minimum edge thresholds in cents'),
('fee_overrides', '{"kalshi_maker_fee_markets": []}', 'Markets where Kalshi maker fees apply'),
('matching_config', '{"similarity_threshold": 0.75, "auto_match_confidence": 0.75}', 'Market matching configuration');