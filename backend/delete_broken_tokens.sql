-- Delete broken RWA tokens #20 and #21 with malformed URLs
-- These tokens have URLs like "https://trappist.land/https" due to parsing bug

-- Check tokens before deletion
SELECT token_id, asset_type, asset_url, prompt, created_at 
FROM rwa_tokens 
WHERE token_id IN (20, 21);

-- Delete the broken tokens
DELETE FROM rwa_tokens 
WHERE token_id IN (20, 21);

-- Verify deletion
SELECT COUNT(*) as remaining_tokens FROM rwa_tokens;
