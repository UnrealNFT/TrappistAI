-- TrappistAI Marketplace Tables
-- Execute this on Render PostgreSQL Shell

-- RWA Marketplace Listings
CREATE TABLE IF NOT EXISTS rwa_listings (
    listing_id BIGSERIAL PRIMARY KEY,
    token_id BIGINT REFERENCES rwa_tokens(token_id) ON DELETE CASCADE,
    seller_wallet VARCHAR(255) NOT NULL,
    listing_type VARCHAR(20) NOT NULL DEFAULT 'fractional',
    parts_for_sale INTEGER NOT NULL,
    price_per_part DECIMAL(18, 9) NOT NULL,
    parts_sold INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_listings_token ON rwa_listings(token_id);
CREATE INDEX IF NOT EXISTS idx_listings_seller ON rwa_listings(seller_wallet);
CREATE INDEX IF NOT EXISTS idx_listings_status ON rwa_listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_created ON rwa_listings(created_at DESC);

-- RWA Ownership tracking (fractional)
CREATE TABLE IF NOT EXISTS rwa_ownership (
    ownership_id BIGSERIAL PRIMARY KEY,
    token_id BIGINT REFERENCES rwa_tokens(token_id) ON DELETE CASCADE,
    wallet_address VARCHAR(255) NOT NULL,
    shares_owned INTEGER NOT NULL,
    acquired_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(token_id, wallet_address)
);

CREATE INDEX IF NOT EXISTS idx_ownership_token ON rwa_ownership(token_id);
CREATE INDEX IF NOT EXISTS idx_ownership_wallet ON rwa_ownership(wallet_address);

-- RWA Transactions history
CREATE TABLE IF NOT EXISTS rwa_transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    token_id BIGINT REFERENCES rwa_tokens(token_id) ON DELETE CASCADE,
    listing_id BIGINT REFERENCES rwa_listings(listing_id) ON DELETE SET NULL,
    buyer_wallet VARCHAR(255) NOT NULL,
    seller_wallet VARCHAR(255) NOT NULL,
    parts_bought INTEGER NOT NULL,
    price_per_part DECIMAL(18, 9) NOT NULL,
    total_price DECIMAL(18, 9) NOT NULL,
    cspr_tx_hash VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_token ON rwa_transactions(token_id);
CREATE INDEX IF NOT EXISTS idx_transactions_buyer ON rwa_transactions(buyer_wallet);
CREATE INDEX IF NOT EXISTS idx_transactions_seller ON rwa_transactions(seller_wallet);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON rwa_transactions(created_at DESC);

-- Verify tables created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name LIKE 'rwa_%'
ORDER BY table_name;
