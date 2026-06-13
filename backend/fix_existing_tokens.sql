-- Fix existing RWA tokens that don't have ownership entries
-- Run this on Render PostgreSQL console

-- Give 100% ownership to creators of tokens without ownership
INSERT INTO rwa_ownership (token_id, wallet_address, shares_owned)
SELECT 
    token_id, 
    wallet_address, 
    100 as shares_owned
FROM rwa_tokens
WHERE token_id NOT IN (
    SELECT DISTINCT token_id FROM rwa_ownership
)
ON CONFLICT (token_id, wallet_address) DO NOTHING;

-- Verify fix
SELECT 
    t.token_id,
    t.wallet_address,
    t.asset_type,
    t.prompt,
    COALESCE(o.shares_owned, 0) as shares_owned
FROM rwa_tokens t
LEFT JOIN rwa_ownership o ON t.token_id = o.token_id AND t.wallet_address = o.wallet_address
ORDER BY t.token_id;
