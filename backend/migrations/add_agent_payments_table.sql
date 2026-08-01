-- Agent x402 payments table
-- Tracks native-CSPR agent payments so that a single deploy hash cannot be
-- replayed across multiple generation requests.
CREATE TABLE IF NOT EXISTS agent_payments (
    id SERIAL PRIMARY KEY,
    deploy_hash VARCHAR(128) UNIQUE NOT NULL,
    wallet_address VARCHAR(128) NOT NULL,
    amount_cspr NUMERIC(20, 9) NOT NULL,
    amount_motes BIGINT NOT NULL,
    resource VARCHAR(32) NOT NULL,
    cost_usd NUMERIC(10, 4) NOT NULL,
    generated_url TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'settled',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_payments_wallet ON agent_payments(wallet_address);
CREATE INDEX IF NOT EXISTS idx_agent_payments_resource ON agent_payments(resource);
