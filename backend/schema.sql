-- TrappistAI Database Schema
-- PostgreSQL 14+

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) UNIQUE NOT NULL,
    tokens INTEGER DEFAULT 0,
    telegram_username VARCHAR(255),
    telegram_user_id BIGINT,
    telegram_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_wallet ON users(wallet_address);
CREATE INDEX idx_users_telegram ON users(telegram_username);

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

-- RWA Tokens table (AI assets tokenized as NFTs)
CREATE TABLE IF NOT EXISTS rwa_tokens (
    token_id BIGSERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) NOT NULL,
    asset_type VARCHAR(20) NOT NULL,  -- 'image', 'music', '3d'
    ipfs_hash VARCHAR(100) NOT NULL,
    asset_url TEXT NOT NULL,
    prompt TEXT,
    model VARCHAR(100),
    telegram_user_id BIGINT,
    cspr_tx_hash VARCHAR(100),
    metadata JSONB,  -- Additional metadata (dimensions, duration, etc)
    fractional BOOLEAN DEFAULT FALSE,
    total_shares INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rwa_wallet ON rwa_tokens(wallet_address);
CREATE INDEX idx_rwa_telegram ON rwa_tokens(telegram_user_id);
CREATE INDEX idx_rwa_type ON rwa_tokens(asset_type);
CREATE INDEX idx_rwa_created ON rwa_tokens(created_at DESC);

-- Telegram verification table for linking accounts
CREATE TABLE IF NOT EXISTS telegram_verification (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) NOT NULL,
    telegram_username VARCHAR(255) NOT NULL,
    verification_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_telegram_verification_wallet ON telegram_verification(wallet_address);
CREATE INDEX idx_telegram_verification_code ON telegram_verification(verification_code);

-- Telegram username → user_id mapping for bot and webhook
CREATE TABLE IF NOT EXISTS telegram_usernames (
    username VARCHAR(255) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_telegram_usernames_user_id ON telegram_usernames(user_id);

-- Example data (optional)
-- INSERT INTO users (wallet_address, tokens) VALUES 
-- ('0123456789abcdef0123456789abcdef01234567', 1000);
