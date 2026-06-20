-- Crypto News Articles for AI Assistant
-- Store RSS articles for real-time search and RAG

CREATE TABLE IF NOT EXISTS crypto_news (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(500) UNIQUE NOT NULL,  -- RSS entry.id or link hash
    source VARCHAR(100) NOT NULL,  -- CoinTelegraph, CoinDesk, etc.
    
    -- English content
    title_en TEXT NOT NULL,
    description_en TEXT,
    summary_en TEXT,
    
    -- French translation
    title_fr TEXT,
    description_fr TEXT,
    summary_fr TEXT,
    
    -- Metadata
    link TEXT NOT NULL,
    pub_date TIMESTAMP,
    hashtags TEXT[],
    
    -- For semantic search (optional - future)
    embedding VECTOR(1536),  -- OpenAI embeddings or similar
    
    -- Tracking
    fetched_at TIMESTAMP DEFAULT NOW(),
    posted_telegram BOOLEAN DEFAULT FALSE,
    posted_at TIMESTAMP,
    
    -- Full text search
    search_vector tsvector
);

-- Indexes for fast search
CREATE INDEX idx_news_source ON crypto_news(source);
CREATE INDEX idx_news_pub_date ON crypto_news(pub_date DESC);
CREATE INDEX idx_news_fetched ON crypto_news(fetched_at DESC);
CREATE INDEX idx_news_posted ON crypto_news(posted_telegram);

-- Full-text search index (PostgreSQL)
CREATE INDEX idx_news_search ON crypto_news USING GIN(search_vector);

-- Auto-update search_vector on INSERT/UPDATE
CREATE OR REPLACE FUNCTION crypto_news_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title_en, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description_en, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.summary_en, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER crypto_news_search_vector_trigger
BEFORE INSERT OR UPDATE ON crypto_news
FOR EACH ROW EXECUTE FUNCTION crypto_news_search_vector_update();

-- View for recent news (last 24h)
CREATE OR REPLACE VIEW recent_crypto_news AS
SELECT 
    id, source, title_en, title_fr, summary_en, summary_fr, 
    link, pub_date, hashtags, fetched_at
FROM crypto_news
WHERE fetched_at > NOW() - INTERVAL '24 hours'
ORDER BY pub_date DESC;

COMMENT ON TABLE crypto_news IS 'Crypto news articles from 20+ RSS sources for AI assistant RAG';
