-- Crypto News Database Schema (Render-compatible - no vector extension)
-- For TrappistAI real-time crypto news integration
-- Compatible with PostgreSQL 12+

-- Drop existing table if needed (careful in production!)
-- DROP TABLE IF EXISTS crypto_news CASCADE;

-- Main crypto news table
CREATE TABLE IF NOT EXISTS crypto_news (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(512) UNIQUE NOT NULL,  -- URL hash or unique identifier
    source VARCHAR(100) NOT NULL,              -- CoinTelegraph, CoinDesk, etc.
    
    -- English content
    title_en TEXT NOT NULL,
    description_en TEXT,
    summary_en TEXT,                           -- Ollama-generated summary
    
    -- French translations
    title_fr TEXT,
    description_fr TEXT,
    summary_fr TEXT,
    
    link TEXT NOT NULL,                        -- Original article URL
    pub_date TIMESTAMP,                        -- Original publication date
    fetched_at TIMESTAMP DEFAULT NOW(),        -- When we fetched it
    
    hashtags TEXT[],                           -- Array of hashtags/topics
    posted BOOLEAN DEFAULT FALSE,              -- Posted to Telegram?
    
    -- Full-text search vector (auto-updated by trigger)
    search_vector TSVECTOR
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_crypto_news_source ON crypto_news(source);
CREATE INDEX IF NOT EXISTS idx_crypto_news_pub_date ON crypto_news(pub_date DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_news_fetched_at ON crypto_news(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_news_posted ON crypto_news(posted);

-- Full-text search index (GIN for fast search)
CREATE INDEX IF NOT EXISTS idx_crypto_news_search ON crypto_news USING GIN(search_vector);

-- Trigger function to auto-update search_vector
CREATE OR REPLACE FUNCTION crypto_news_search_vector_update() RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title_en, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.summary_en, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.description_en, '')), 'C') ||
        setweight(to_tsvector('french', COALESCE(NEW.title_fr, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.summary_fr, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update search_vector on INSERT/UPDATE
DROP TRIGGER IF EXISTS crypto_news_search_vector_trigger ON crypto_news;
CREATE TRIGGER crypto_news_search_vector_trigger
    BEFORE INSERT OR UPDATE ON crypto_news
    FOR EACH ROW
    EXECUTE FUNCTION crypto_news_search_vector_update();

-- View for recent news (last 24 hours)
CREATE OR REPLACE VIEW recent_crypto_news AS
SELECT 
    id,
    source,
    title_en,
    summary_en,
    link,
    pub_date,
    fetched_at,
    hashtags
FROM crypto_news
WHERE fetched_at > NOW() - INTERVAL '24 hours'
ORDER BY pub_date DESC;

-- Grant permissions (if using specific user roles)
-- GRANT ALL ON crypto_news TO trappistai_user;
-- GRANT ALL ON SEQUENCE crypto_news_id_seq TO trappistai_user;
