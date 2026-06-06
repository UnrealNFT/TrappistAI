-- TrappistAI Database Schema
-- PostgreSQL 14+

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) UNIQUE NOT NULL,
    tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_wallet ON users(wallet_address);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) NOT NULL,
    amount_cspr DECIMAL(18, 9) NOT NULL,
    tokens_purchased INTEGER NOT NULL,
    package_name VARCHAR(100),
    transaction_hash VARCHAR(255) UNIQUE NOT NULL,
    network VARCHAR(20) DEFAULT 'mainnet',
    status VARCHAR(20) DEFAULT 'pending',
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_wallet ON payments(wallet_address);
CREATE INDEX idx_payments_tx ON payments(transaction_hash);
CREATE INDEX idx_payments_status ON payments(status);

-- Generations table
CREATE TABLE IF NOT EXISTS generations (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- image, music, 3d, chat
    prompt TEXT,
    tokens_spent INTEGER NOT NULL,
    result_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_generations_wallet ON generations(wallet_address);
CREATE INDEX idx_generations_type ON generations(type);
CREATE INDEX idx_generations_created ON generations(created_at DESC);

-- Example data (optional)
-- INSERT INTO users (wallet_address, tokens) VALUES 
-- ('0123456789abcdef0123456789abcdef01234567', 1000);
