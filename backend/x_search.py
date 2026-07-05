"""
Lightweight X / Twitter search via Nitter RSS (no API key).
Nitter instances can be flaky, so we try several and degrade gracefully to None.
"""

from typing import Optional
from urllib.parse import quote_plus

import feedparser

# Public Nitter instances (order = preference). If all fail, returns None.
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://xcancel.com",
]


def _clean(t: str) -> str:
    return " ".join((t or "").split())[:280]


def search_x(query: str, limit: int = 5) -> Optional[str]:
    """Search recent tweets for `query`. Tries Nitter first, then falls back to
    Jina Reader on x.com search (more reliable). Returns a context string or None."""
    if not query:
        return None
    q = quote_plus(query)
    for base in NITTER_INSTANCES:
        try:
            feed = feedparser.parse(f"{base}/search/rss?f=tweets&q={q}")
            items = []
            for e in feed.entries[:limit + 5]:
                title = _clean(str(getattr(e, "title", "")))
                link = str(getattr(e, "link", ""))
                # Only keep real tweets (status links); skip instance error entries
                if not title or "/status/" not in link:
                    continue
                author = str(getattr(e, "author", "")).strip()
                link = link.replace(base, "https://x.com")
                items.append(f"- {author}: {title} {link}".strip())
            if items:
                return (
                    f"X/TWITTER SEARCH for '{query}' (recent posts, community):\n"
                    + "\n".join(items[:limit])
                )
        except Exception:
            continue
    # Fallback: Jina Reader reads the live x.com search page (JS rendered)
    try:
        from web_research import jina_fetch
        txt = jina_fetch(f"https://x.com/search?q={q}&f=live", max_chars=1800)
        if txt and len(txt) > 100:
            return (
                f"X/TWITTER SEARCH for '{query}' (via web reader, recent):\n"
                + txt.strip()[:1800]
            )
    except Exception:
        pass
    return None


def timeline_x(handle: str, limit: int = 5) -> Optional[str]:
    """Recent tweets from a specific @handle (official account). None if unavailable."""
    if not handle:
        return None
    h = handle.lstrip("@").strip()
    for base in NITTER_INSTANCES:
        try:
            feed = feedparser.parse(f"{base}/{h}/rss")
            items = []
            for e in feed.entries[:limit + 5]:
                title = _clean(str(getattr(e, "title", "")))
                link = str(getattr(e, "link", ""))
                if not title or "/status/" not in link:
                    continue
                link = link.replace(base, "https://x.com")
                items.append(f"- {title} {link}".strip())
            if items:
                return (
                    f"X/TWITTER — recent posts from @{h}:\n" + "\n".join(items[:limit])
                )
        except Exception:
            continue
    return None
