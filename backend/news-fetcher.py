"""
Crypto News RSS Fetcher for TrappistAI
Fetches 20+ crypto RSS sources and stores in PostgreSQL
Can be run as:
  1. Standalone script (cron job)
  2. Background service (systemd)
  3. Integrated in FastAPI (startup event)
"""
import asyncio
import hashlib
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

import requests
import feedparser
from deep_translator import GoogleTranslator

# Import TrappistAI database connection
from db import get_db_pool


# === 20 CRYPTO RSS SOURCES ===
NEWS_SOURCES = [
    {"name": "CoinTelegraph", "rss": "https://cointelegraph.com/rss", "use_proxy": True},
    {"name": "CoinDesk", "rss": "https://www.coindesk.com/arc/outboundfeeds/rss/", "use_proxy": True},
    {"name": "Decrypt", "rss": "https://decrypt.co/feed", "use_proxy": True},
    {"name": "The Block", "rss": "https://www.theblock.co/rss.xml", "use_proxy": True},
    {"name": "Bitcoin Magazine", "rss": "https://bitcoinmagazine.com/.rss/full/", "use_proxy": True},
    {"name": "CryptoSlate", "rss": "https://cryptoslate.com/feed/", "use_proxy": True},
    {"name": "Bitcoinist", "rss": "https://bitcoinist.com/feed/", "use_proxy": True},
    {"name": "NewsBTC", "rss": "https://www.newsbtc.com/feed/", "use_proxy": True},
    {"name": "CryptoNews", "rss": "https://cryptonews.com/news/feed/", "use_proxy": False},
    {"name": "Bitcoin.com", "rss": "https://news.bitcoin.com/feed/", "use_proxy": True},
    {"name": "BeInCrypto", "rss": "https://beincrypto.com/feed/", "use_proxy": True},
    {"name": "AMBCrypto", "rss": "https://ambcrypto.com/feed/", "use_proxy": True},
    {"name": "The Guardian", "rss": "https://www.theguardian.com/technology/cryptocurrencies/rss", "use_proxy": True},
    {"name": "Forbes Crypto", "rss": "https://www.forbes.com/crypto-blockchain/feed/", "use_proxy": True},
    {"name": "CNBC Crypto", "rss": "https://www.cnbc.com/id/10000115/device/rss/rss.html", "use_proxy": True},
    {"name": "Blockchain.News", "rss": "https://blockchain.news/RSS", "use_proxy": True},
    {"name": "CryptoDaily", "rss": "https://cryptodaily.co.uk/feed", "use_proxy": True},
    {"name": "Coin Journal", "rss": "https://coinjournal.net/feed/", "use_proxy": True},
]

CORS_PROXY = "https://api.allorigins.win/raw?url="


def clean_content(text: str) -> str:
    """Clean HTML tags, images, links from RSS content."""
    if not text:
        return ""
    text = re.sub(r"<img[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<a[^>]*>.*?</a>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"https?://[^\s]*\.(jpg|jpeg|png|gif|webp)[^\s]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[Image:.*?\]", "", text)
    text = re.sub(r"Read more.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text.strip()


def generate_article_id(link: str, title: str) -> str:
    """Generate unique article ID from link + title."""
    return hashlib.md5(f"{link}{title}".encode()).hexdigest()


def parse_feed(xml_content: str, source_name: str) -> List[Dict]:
    """Parse RSS feed and return cleaned articles."""
    try:
        feed = feedparser.parse(xml_content)
        if not feed.entries:
            return []

        articles = []
        for entry in feed.entries[:5]:  # Max 5 per source
            description = clean_content(str(getattr(entry, "description", "")))
            title = getattr(entry, "title", "No title")
            link = getattr(entry, "link", "")

            if len(description.strip()) < 20 or "image" in title.lower():
                continue

            article = {
                "id": generate_article_id(link, title),
                "title": title,
                "description": description,
                "link": link,
                "pub_date": getattr(entry, "published", ""),
                "source": source_name,
            }
            articles.append(article)

        return articles
    except Exception as e:
        print(f"❌ Parse error for {source_name}: {e}")
        return []


def fetch_rss_source(source: Dict) -> List[Dict]:
    """Fetch one RSS source with retry logic."""
    try:
        if source["use_proxy"]:
            url = CORS_PROXY + source["rss"]
        else:
            url = source["rss"]

        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        articles = parse_feed(response.text, source["name"])
        print(f"✅ {source['name']}: {len(articles)} articles")
        return articles

    except Exception as e:
        print(f"❌ {source['name']}: {e}")
        return []


def summarize_with_ollama(article: Dict) -> Optional[Dict]:
    """Summarize article with Ollama Llama3.2 (local)."""
    try:
        prompt = f"""You are a crypto journalist. Analyze this article and create a quality summary.

ARTICLE:
Title: {article["title"]}
Description: {article["description"][:500]}
Source: {article["source"]}

STRICT RULES:
1. Write a catchy English title (clear, concise, engaging)
2. Write a SHORT summary (2 sentences max)
3. Add a complementary description (1 sentence that adds info)
4. Generate 3-4 relevant crypto hashtags
5. Write as ORIGINAL content (never mention source name)

JSON RESPONSE FORMAT:
{{
    "title_en": "catchy title",
    "description_en": "complementary info",
    "summary": "short summary in 2 sentences",
    "hashtags": ["#Tag1", "#Tag2", "#Tag3"]
}}

Respond ONLY with JSON:"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2:latest", "prompt": prompt, "stream": False, "options": {"temperature": 0.7}},
            timeout=120,
        )

        if response.status_code != 200:
            return None

        content = response.json().get("response", "").strip()

        # Clean JSON
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Extract JSON with better regex (handle nested braces)
        json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to fix common issues
            content = content.replace('\n', ' ').replace('  ', ' ')
            return json.loads(content)

    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        return None


def translate_to_french(result_en: Dict) -> Dict:
    """Translate English content to French using Google Translate."""
    try:
        translator = GoogleTranslator(source='en', target='fr')
        return {
            "title_fr": translator.translate(result_en["title_en"]),
            "description_fr": translator.translate(result_en["description_en"]),
            "summary_fr": translator.translate(result_en["summary"]),
        }
    except:
        return {
            "title_fr": result_en["title_en"],
            "description_fr": result_en.get("description_en", ""),
            "summary_fr": result_en.get("summary", ""),
        }


async def store_article_in_db(article: Dict, pool):
    """Store article in PostgreSQL."""
    try:
        # Summarize with Ollama
        summary_result = summarize_with_ollama(article)
        if not summary_result:
            print(f"⚠️ Skipping (no summary): {article['title'][:50]}")
            return False

        # Translate to French
        fr_result = translate_to_french(summary_result)

        # Parse pub_date
        pub_date = None
        if article.get("pub_date"):
            try:
                from dateutil import parser
                parsed_date = parser.parse(article["pub_date"])
                # Make timezone-aware if naive
                if parsed_date.tzinfo is None:
                    import datetime
                    parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                pub_date = parsed_date
            except:
                pass

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO crypto_news (
                    article_id, source, title_en, description_en, summary_en,
                    title_fr, description_fr, summary_fr, link, pub_date, hashtags
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (article_id) DO NOTHING
            """, 
                article["id"],
                article["source"],
                summary_result["title_en"],
                summary_result.get("description_en", ""),
                summary_result.get("summary", ""),
                fr_result["title_fr"],
                fr_result["description_fr"],
                fr_result["summary_fr"],
                article["link"],
                pub_date,
                summary_result.get("hashtags", [])
            )
        
        print(f"✅ Stored: {summary_result['title_en'][:50]}")
        return True

    except Exception as e:
        print(f"❌ DB error: {e}")
        return False


async def fetch_and_store_news():
    """Main function: Fetch all RSS sources and store in database."""
    print("🚀 Starting crypto news fetch cycle...")
    start_time = time.time()

    # Fetch all RSS sources in parallel
    all_articles = []
    for source in NEWS_SOURCES:
        articles = fetch_rss_source(source)
        all_articles.extend(articles)
    
    print(f"\n📰 Total articles fetched: {len(all_articles)}")

    if not all_articles:
        print("⚠️ No articles fetched")
        return

    # Connect to database
    pool = await get_db_pool()

    # Store articles (with rate limiting for Ollama)
    stored_count = 0
    for i, article in enumerate(all_articles):
        success = await store_article_in_db(article, pool)
        if success:
            stored_count += 1
        
        # Rate limit: 2 seconds between Ollama requests
        if i < len(all_articles) - 1:
            await asyncio.sleep(2)

    elapsed = time.time() - start_time
    print(f"\n✅ Fetch cycle complete!")
    print(f"   Stored: {stored_count}/{len(all_articles)} articles")
    print(f"   Time: {elapsed:.1f}s")


# === COMMAND LINE INTERFACE ===
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # Run as daemon (fetch every 5 minutes)
        print("🔄 Running as daemon (fetch every 5 minutes)")
        while True:
            asyncio.run(fetch_and_store_news())
            print("⏰ Sleeping 5 minutes...\n")
            time.sleep(300)
    else:
        # Run once
        asyncio.run(fetch_and_store_news())
