"""
Crypto News Search for TrappistAI Bot
Provides semantic search capabilities for stored articles
"""
import asyncpg
from typing import List, Dict, Optional
from datetime import datetime, timedelta


async def search_news_fulltext(
    query: str, 
    pool: asyncpg.Pool, 
    limit: int = 5,
    language: str = "en"
) -> List[Dict]:
    """
    Full-text search in crypto news using PostgreSQL tsvector.
    
    Args:
        query: Search query (e.g., "Bitcoin regulation", "Ethereum upgrade")
        pool: Database connection pool
        limit: Max results to return
        language: 'en' or 'fr'
    
    Returns:
        List of matching articles with relevance score
    """
    try:
        title_col = "title_fr" if language == "fr" else "title_en"
        summary_col = "summary_fr" if language == "fr" else "summary_en"
        desc_col = "description_fr" if language == "fr" else "description_en"

        async with pool.acquire() as conn:
            results = await conn.fetch(f"""
                SELECT 
                    id,
                    source,
                    {title_col} as title,
                    {summary_col} as summary,
                    {desc_col} as description,
                    link,
                    pub_date,
                    hashtags,
                    ts_rank(search_vector, plainto_tsquery('english', $1)) as relevance
                FROM crypto_news
                WHERE search_vector @@ plainto_tsquery('english', $1)
                ORDER BY relevance DESC, pub_date DESC
                LIMIT $2
            """, query, limit)

            return [dict(row) for row in results]

    except Exception as e:
        print(f"❌ Search error: {e}")
        return []


async def get_recent_news(
    pool: asyncpg.Pool,
    hours: int = 24,
    limit: int = 10,
    language: str = "en"
) -> List[Dict]:
    """Get recent crypto news from last X hours."""
    try:
        title_col = "title_fr" if language == "fr" else "title_en"
        summary_col = "summary_fr" if language == "fr" else "summary_en"

        async with pool.acquire() as conn:
            results = await conn.fetch(f"""
                SELECT 
                    id,
                    source,
                    {title_col} as title,
                    {summary_col} as summary,
                    link,
                    pub_date,
                    hashtags
                FROM crypto_news
                WHERE fetched_at > NOW() - INTERVAL '{hours} hours'
                ORDER BY pub_date DESC
                LIMIT $1
            """, limit)

            return [dict(row) for row in results]

    except Exception as e:
        print(f"❌ Recent news error: {e}")
        return []


async def get_news_by_topic(
    topic: str,
    pool: asyncpg.Pool,
    limit: int = 5,
    language: str = "en"
) -> List[Dict]:
    """
    Get news by specific crypto topic.
    
    Topics: bitcoin, ethereum, defi, nft, regulation, mining, etc.
    """
    # Topic keywords mapping
    topic_keywords = {
        "bitcoin": ["bitcoin", "btc", "satoshi", "lightning network"],
        "ethereum": ["ethereum", "eth", "vitalik", "eip", "merge"],
        "defi": ["defi", "decentralized finance", "uniswap", "aave", "compound"],
        "nft": ["nft", "non-fungible", "opensea", "collectible", "digital art"],
        "regulation": ["regulation", "sec", "law", "legal", "compliance"],
        "mining": ["mining", "hashrate", "miner", "proof of work"],
        "stablecoin": ["stablecoin", "usdt", "usdc", "dai", "tether"],
        "altcoin": ["altcoin", "solana", "cardano", "polkadot", "avalanche"],
    }

    keywords = topic_keywords.get(topic.lower(), [topic])
    query = " | ".join(keywords)  # OR search
    
    return await search_news_fulltext(query, pool, limit, language)


async def format_news_for_chat(articles: List[Dict], max_articles: int = 3) -> str:
    """
    Format news articles for chat response.
    
    Returns formatted string ready for bot response.
    """
    if not articles:
        return "❌ No recent news found on this topic."

    response = "📰 **Latest Crypto News:**\n\n"
    
    for i, article in enumerate(articles[:max_articles], 1):
        title = article.get("title", "No title")
        summary = article.get("summary", "")
        source = article.get("source", "Unknown")
        link = article.get("link", "")
        
        response += f"**{i}. {title}**\n"
        if summary:
            response += f"{summary}\n"
        response += f"_Source: {source}_ | [Read more]({link})\n\n"

    return response


async def get_news_summary_for_ai(
    query: str,
    pool: asyncpg.Pool,
    max_context: int = 3
) -> str:
    """
    Get news context for AI assistant (RAG).
    Returns concise text block for LLM context.
    """
    articles = await search_news_fulltext(query, pool, limit=max_context)
    
    if not articles:
        return ""

    context = "RECENT CRYPTO NEWS CONTEXT:\n\n"
    for article in articles:
        context += f"Title: {article['title']}\n"
        context += f"Summary: {article['summary']}\n"
        context += f"Source: {article['source']}\n"
        context += "---\n"

    return context


# === EXAMPLE USAGE ===
async def test_search():
    """Test search functionality."""
    from db import get_db_pool
    
    pool = await get_db_pool()
    
    # Test 1: Full-text search
    print("🔍 Search: 'Bitcoin regulation'")
    results = await search_news_fulltext("Bitcoin regulation", pool, limit=3)
    for r in results:
        print(f"  - {r['title']} (relevance: {r['relevance']:.2f})")
    
    # Test 2: Recent news
    print("\n📰 Recent news (last 24h):")
    recent = await get_recent_news(pool, hours=24, limit=5)
    for r in recent:
        print(f"  - {r['title']}")
    
    # Test 3: Topic search
    print("\n🏷️ Topic: DeFi")
    defi_news = await get_news_by_topic("defi", pool, limit=3)
    for r in defi_news:
        print(f"  - {r['title']}")
    
    # Test 4: Format for chat
    print("\n💬 Formatted for chat:")
    formatted = await format_news_for_chat(results, max_articles=2)
    print(formatted)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search())
