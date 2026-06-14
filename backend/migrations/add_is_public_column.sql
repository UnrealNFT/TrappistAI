-- Add is_public column to rwa_tokens table for community sharing
ALTER TABLE rwa_tokens 
ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;

-- Create index for faster queries on public items
CREATE INDEX IF NOT EXISTS idx_rwa_tokens_is_public 
ON rwa_tokens(is_public, created_at DESC);

-- Update existing items to be private by default
UPDATE rwa_tokens 
SET is_public = FALSE 
WHERE is_public IS NULL;
