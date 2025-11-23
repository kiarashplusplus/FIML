-- Database initialization script for PostgreSQL + TimescaleDB

-- Enable TimescaleDB extension (optional - only for production)
-- CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create enum types
CREATE TYPE asset_type AS ENUM ('equity', 'crypto', 'forex', 'commodity', 'index', 'etf', 'option', 'future');
CREATE TYPE data_type AS ENUM ('price', 'ohlcv', 'fundamentals', 'technical', 'sentiment', 'news', 'macro', 'correlation', 'risk');
CREATE TYPE task_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

-- Assets table
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    asset_type asset_type NOT NULL,
    market VARCHAR(10) NOT NULL,
    exchange VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, exchange)
);

CREATE INDEX idx_assets_symbol ON assets(symbol);
CREATE INDEX idx_assets_type ON assets(asset_type);

-- Price cache (L2 cache with TimescaleDB)
CREATE TABLE IF NOT EXISTS price_cache (
    time TIMESTAMPTZ NOT NULL,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    provider VARCHAR(50) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    change DOUBLE PRECISION,
    change_percent DOUBLE PRECISION,
    volume BIGINT,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    session_metadata JSONB,
    PRIMARY KEY (time, asset_id, provider)
);

-- Convert to hypertable (TimescaleDB only)
-- SELECT create_hypertable('price_cache', 'time', if_not_exists => TRUE);

-- Create retention policy (keep data for 90 days) (TimescaleDB only)
-- SELECT add_retention_policy('price_cache', INTERVAL '90 days', if_not_exists => TRUE);

-- OHLCV cache
CREATE TABLE IF NOT EXISTS ohlcv_cache (
    time TIMESTAMPTZ NOT NULL,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    provider VARCHAR(50) NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT,
    timeframe VARCHAR(10) NOT NULL,
    PRIMARY KEY (time, asset_id, provider, timeframe)
);

-- SELECT create_hypertable('ohlcv_cache', 'time', if_not_exists => TRUE);
-- SELECT add_retention_policy('ohlcv_cache', INTERVAL '365 days', if_not_exists => TRUE);

-- Fundamentals cache
CREATE TABLE IF NOT EXISTS fundamentals_cache (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    provider VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ttl_seconds INTEGER DEFAULT 3600,
    UNIQUE(asset_id, provider)
);

CREATE INDEX idx_fundamentals_timestamp ON fundamentals_cache(timestamp);

-- Generic cache for key-value storage
CREATE TABLE IF NOT EXISTS generic_cache (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ttl_seconds INTEGER DEFAULT 3600
);

CREATE INDEX idx_generic_cache_timestamp ON generic_cache(timestamp);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    status task_status NOT NULL DEFAULT 'pending',
    inputs JSONB NOT NULL,
    result JSONB,
    progress DOUBLE PRECISION DEFAULT 0.0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    estimated_completion TIMESTAMPTZ
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_type ON tasks(type);

-- Provider health metrics
CREATE TABLE IF NOT EXISTS provider_health (
    time TIMESTAMPTZ NOT NULL,
    provider_name VARCHAR(50) NOT NULL,
    is_healthy BOOLEAN NOT NULL,
    uptime_percent DOUBLE PRECISION,
    avg_latency_ms DOUBLE PRECISION,
    success_rate DOUBLE PRECISION,
    error_count INTEGER DEFAULT 0,
    PRIMARY KEY (time, provider_name)
);

-- SELECT create_hypertable('provider_health', 'time', if_not_exists => TRUE);
-- SELECT add_retention_policy('provider_health', INTERVAL '30 days', if_not_exists => TRUE);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    assets JSONB NOT NULL,
    context JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_sessions_active ON sessions(is_active);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Event stream table
CREATE TABLE IF NOT EXISTS events (
    time TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    severity VARCHAR(20),
    data JSONB NOT NULL,
    PRIMARY KEY (time, event_type, asset_id)
);

-- SELECT create_hypertable('events', 'time', if_not_exists => TRUE);
-- SELECT add_retention_policy('events', INTERVAL '30 days', if_not_exists => TRUE);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT
);

-- SELECT create_hypertable('audit_log', 'time', if_not_exists => TRUE);
-- SELECT add_retention_policy('audit_log', INTERVAL '365 days', if_not_exists => TRUE);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some seed data for testing
INSERT INTO assets (symbol, name, asset_type, market, exchange, currency) VALUES
    ('AAPL', 'Apple Inc.', 'equity', 'US', 'NASDAQ', 'USD'),
    ('TSLA', 'Tesla Inc.', 'equity', 'US', 'NASDAQ', 'USD'),
    ('BTC', 'Bitcoin', 'crypto', 'CRYPTO', 'binance', 'USD'),
    ('ETH', 'Ethereum', 'crypto', 'CRYPTO', 'binance', 'USD')
ON CONFLICT DO NOTHING;
