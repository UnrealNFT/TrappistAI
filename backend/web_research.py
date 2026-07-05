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

import requests

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
