"""
Web research helpers (no API key required):
- jina_fetch(url)      : read any URL as clean text via Jina Reader (r.jina.ai)
- github_search(query) : GitHub repository search (recent / most-starred)
- github_trending()    : trending repos (created recently, sorted by stars)

Optional: set GITHUB_TOKEN env var to raise GitHub rate limits.
Focus areas for this bot: crypto + software development.
"""

import os
import re
import time
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import requests
import feedparser

logger = logging.getLogger(__name__)

JINA = "https://r.jina.ai/"
GITHUB_SEARCH = "https://api.github.com/search/repositories"

_UA = "Mozilla/5.0 (compatible; TrappistAI/1.0)"


def jina_fetch(url: str, max_chars: int = 2500) -> str:
    """Read a URL as clean Markdown text via Jina Reader. Returns text or None.
    Works for normal pages AND JS pages like x.com profiles/search."""
    if not url:
        return None
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(
            JINA + url,
            headers={"User-Agent": _UA, "X-Return-Format": "markdown"},
            timeout=20,
        )
        r.raise_for_status()
        txt = (r.text or "").strip()
        return txt[:max_chars] if txt else None
    except Exception as e:
        logger.warning("Jina fetch failed for %s: %s", url, e)
        return None


def _gh_headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": _UA}
    tok = os.getenv("GITHUB_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _fmt_repos(items: list, limit: int) -> str:
    lines = []
    for it in items[:limit]:
        desc = (it.get("description") or "").replace("\n", " ")[:140]
        lines.append(
            f"- {it.get('full_name')} ⭐{it.get('stargazers_count', 0)} "
            f"[{it.get('language') or '—'}] — {desc} "
            f"{it.get('html_url')} (updated {str(it.get('pushed_at',''))[:10]})"
        )
    return "\n".join(lines) if lines else None


def github_search(query: str, limit: int = 5, recent_days: int = 0) -> str:
    """Search GitHub repositories. recent_days>0 restricts to recently pushed repos.
    Returns a context block with sources, or None."""
    q = query.strip()
    if recent_days > 0:
        since = (datetime.now(timezone.utc) - timedelta(days=recent_days)).strftime("%Y-%m-%d")
        q = f"{q} pushed:>{since}"
    try:
        r = requests.get(
            GITHUB_SEARCH,
            params={"q": q, "sort": "stars", "order": "desc", "per_page": limit},
            headers=_gh_headers(),
            timeout=12,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        body = _fmt_repos(items, limit)
        if body:
            return f"GITHUB SEARCH for '{query}' (most-starred, real results with links):\n" + body
    except Exception as e:
        logger.warning("GitHub search failed for %r: %s", query, e)
    return None


def github_trending(topic: str = "", days: int = 14, limit: int = 6) -> str:
    """Approximate GitHub trending: repos created in the last `days`, sorted by stars.
    Optional topic filter (e.g. 'crypto', 'ai'). Returns a context block or None."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    q = (f"{topic} " if topic else "") + f"created:>{since}"
    try:
        r = requests.get(
            GITHUB_SEARCH,
            params={"q": q.strip(), "sort": "stars", "order": "desc", "per_page": limit},
            headers=_gh_headers(),
            timeout=12,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        body = _fmt_repos(items, limit)
        if body:
            label = f" ({topic})" if topic else ""
            return f"GITHUB TRENDING{label} — top new repos (last {days}d):\n" + body
    except Exception as e:
        logger.warning("GitHub trending failed: %s", e)
    return None


# ─── General web/news search (ANY topic, not just crypto) ────────────────────

# Info-seeking intent triggers (FR/EN)
_INFO_TRIGGERS = (
    "parle moi de", "parle-moi de", "que peux tu", "que peut tu", "que penses tu de",
    "c'est quoi", "cest quoi", "qui est", "qui sont", "quoi de neuf", "info sur",
    "infos sur", "actu de", "actualité", "actualite", "raconte", "dis moi",
    "tell me about", "what about", "who is", "what is", "what's new", "news about",
)


def has_info_intent(text: str) -> bool:
    low = text.lower()
    return any(t in low for t in _INFO_TRIGGERS)


# Google News locale params per UI language → returns local-language results.
_NEWS_LOCALES = {
    "fr": ("fr", "FR", "FR:fr"),
    "en": ("en-US", "US", "US:en"),
    "es": ("es", "ES", "ES:es"),
    "de": ("de", "DE", "DE:de"),
    "it": ("it", "IT", "IT:it"),
    "pt": ("pt-BR", "BR", "BR:pt-419"),
}


def web_news(query: str, limit: int = 5, lang: str = "en") -> str:
    """Recent news about ANY topic via Google News RSS (people, teams, events...).
    `lang` (e.g. 'fr', 'en') selects the locale so a French user gets French sources.
    Returns a context block with sources, or None."""
    if not query:
        return None
    q = quote_plus(query)
    hl, gl, ceid = _NEWS_LOCALES.get((lang or "en")[:2].lower(), _NEWS_LOCALES["en"])
    url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:limit]:
            title = str(getattr(e, "title", "")).strip()
            if not title:
                continue
            link = str(getattr(e, "link", ""))
            # Include the article description so the LLM grounds on real content
            # instead of inventing facts (scores, line-ups, winners...).
            raw = str(getattr(e, "summary", getattr(e, "description", "")))
            desc = re.sub(r"<[^>]*>", "", raw)
            desc = re.sub(r"\s+", " ", desc).strip()
            block = f"- {title}"
            if desc:
                block += f"\n  {desc[:220]}"
            block += f"\n  {link}"
            items.append(block)
        if items:
            return (
                f"WEB NEWS about '{query}' (Google News, recent — ground your answer ONLY "
                f"on these titles/descriptions; if a specific fact/result is not written "
                f"here, say you don't have it — do NOT invent):\n"
                + "\n".join(items[:limit])
            )
    except Exception as e:
        logger.warning("web_news failed for %r: %s", query, e)
    return None
