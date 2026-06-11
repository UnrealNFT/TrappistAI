-- Migration: Add Telegram linking columns and verification table
-- Run this on your PostgreSQL database

-- Add Telegram columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS telegram_user_id BIGINT,
ADD COLUMN IF NOT EXISTS telegram_verified BOOLEAN DEFAULT FALSE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_username);

-- Create telegram_verification table for linking codes
CREATE TABLE IF NOT EXISTS telegram_verification (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) NOT NULL,
    telegram_username VARCHAR(255) NOT NULL,
    verification_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telegram_verification_wallet ON telegram_verification(wallet_address);
CREATE INDEX IF NOT EXISTS idx_telegram_verification_code ON telegram_verification(verification_code);

-- Clean up expired codes (optional, can be run periodically)
-- DELETE FROM telegram_verification WHERE expires_at < NOW() AND verified = FALSE;
