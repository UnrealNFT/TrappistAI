"""
Lightweight on-demand crypto headlines (feedparser only).
Kept separate from news_fetcher.py so the bot's live-news fallback never breaks
if heavy deps (deep_translator, asyncpg, db) fail to import in production.
"""

import re
from typing import Optional
from urllib.parse import quote_plus

import feedparser


def _clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_live_headlines(keyword: Optional[str] = None, limit: int = 5) -> Optional[str]:
    """On-demand RSS headlines (no DB, no LLM). If keyword is given, Google News is
    queried for it (best per-coin relevance) and generic feeds are filtered on it.
    Returns a context string for the LLM, or None."""
    feeds = []  # (name, url, pre_filtered)
    if keyword:
        q = quote_plus(f"{keyword} crypto")
        feeds.append((
            "Google News",
            f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en",
            True,
        ))
    feeds += [
        ("CryptoNews", "https://cryptonews.com/news/feed/", False),
        ("CoinTelegraph", "https://cointelegraph.com/rss", False),
        ("Decrypt", "https://decrypt.co/feed", False),
        ("BeInCrypto", "https://beincrypto.com/feed/", False),
        ("U.Today", "https://u.today/rss", False),
        ("CryptoSlate", "https://cryptoslate.com/feed/", False),
        ("NewsBTC", "https://www.newsbtc.com/feed/", False),
        ("CryptoPotato", "https://cryptopotato.com/feed/", False),
    ]
    kw = keyword.lower().strip() if keyword else None
    # Collect matching items PER feed, then round-robin so the final list is
    # DIVERSE across sources (previously the first feed filled every slot).
    per_feed = []
    for name, url, pre_filtered in feeds:
        got = []
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:20]:
                title = str(getattr(e, "title", "")).strip()
                if not title:
                    continue
                if kw and not pre_filtered:
                    summary = _clean(str(getattr(e, "summary", getattr(e, "description", ""))))
                    if kw not in title.lower() and kw not in summary.lower():
                        continue
                link = str(getattr(e, "link", ""))
                got.append(f"- {title} (Source: {name}) {link}".strip())
                if len(got) >= 3:
                    break
        except Exception as exc:
            print(f"⚠️ live headlines {name} failed: {exc}")
        if got:
            per_feed.append(got)
    # Round-robin: one from each source per pass → maximum source diversity.
    items = []
    seen = set()
    for depth in range(3):
        for feed_items in per_feed:
            if depth < len(feed_items):
                it = feed_items[depth]
                if it not in seen:
                    seen.add(it)
                    items.append(it)
                    if len(items) >= limit:
                        break
        if len(items) >= limit:
            break
    if not items:
        return None
    label = f" about '{keyword}'" if keyword else ""
    return f"RECENT CRYPTO HEADLINES{label} (live RSS, real-time):\n" + "\n".join(items[:limit])
