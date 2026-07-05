"""
Real-time crypto prices via CoinGecko (free, no API key).
Used to give the TrappistAI bot live market awareness.

Public API:
- detect_coins(text)         -> list of CoinGecko ids mentioned in the text
- get_prices(ids)            -> dict {id: {usd, change_24h, market_cap, volume_24h}}
- format_price_context(text) -> ready-to-inject string for the LLM (or None)
"""

import re
import time
import logging
import requests

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# name / ticker -> CoinGecko id
COIN_MAP = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum", "ether": "ethereum",
    "solana": "solana", "sol": "solana",
    "casper": "casper-network", "cspr": "casper-network", "casper network": "casper-network",
    "cardano": "cardano", "ada": "cardano",
    "ripple": "ripple", "xrp": "ripple",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "polkadot": "polkadot", "dot": "polkadot",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "polygon": "matic-network", "matic": "matic-network", "pol": "matic-network",
    "chainlink": "chainlink", "link": "chainlink",
    "litecoin": "litecoin", "ltc": "litecoin",
    "tron": "tron", "trx": "tron",
    "shiba": "shiba-inu", "shib": "shiba-inu", "shiba inu": "shiba-inu",
    "binance": "binancecoin", "bnb": "binancecoin",
    "toncoin": "the-open-network", "ton": "the-open-network",
    "sui": "sui",
    "aptos": "aptos", "apt": "aptos",
    "arbitrum": "arbitrum", "arb": "arbitrum",
    "optimism": "optimism", "op": "optimism",
    "near": "near",
    "cosmos": "cosmos", "atom": "cosmos",
    "uniswap": "uniswap", "uni": "uniswap",
    "pepe": "pepe",
    "monero": "monero", "xmr": "monero",
    "stellar": "stellar", "xlm": "stellar",
    "hedera": "hedera-hashgraph", "hbar": "hedera-hashgraph",
    "filecoin": "filecoin", "fil": "filecoin",
    "multiversx": "elrond-erd-2", "elrond": "elrond-erd-2", "egld": "elrond-erd-2",
    "sei": "sei-network",
    "injective": "injective-protocol", "inj": "injective-protocol",
    "render": "render-token", "rndr": "render-token",
    "fantom": "fantom", "ftm": "fantom", "sonic": "sonic-3",
    "algorand": "algorand", "algo": "algorand",
    "tezos": "tezos", "xtz": "tezos",
    "vechain": "vechain", "vet": "vechain",
    "theta": "theta-token",
    "immutable": "immutable-x", "imx": "immutable-x",
    "kaspa": "kaspa", "kas": "kaspa",
    "ondo": "ondo-finance",
    "jupiter": "jupiter-exchange-solana", "jup": "jupiter-exchange-solana",
    "worldcoin": "worldcoin-wld", "wld": "worldcoin-wld",
    "aave": "aave",
    "maker": "maker", "mkr": "maker",
    "fetch": "fetch-ai", "fet": "fetch-ai", "artificial superintelligence": "fetch-ai",
    "bonk": "bonk",
    "wif": "dogwifcoin", "dogwifhat": "dogwifcoin",
    "floki": "floki",
    "sandbox": "the-sandbox", "sand": "the-sandbox",
    "decentraland": "decentraland", "mana": "decentraland",
    "axie": "axie-infinity", "axs": "axie-infinity",
    "gala": "gala",
    "chiliz": "chiliz", "chz": "chiliz",
    "eos": "eos",
    "iota": "iota",
    "neo": "neo",
    "dydx": "dydx-chain",
    "ethena": "ethena", "ena": "ethena",
    "pyth": "pyth-network",
    "jasmy": "jasmycoin",
    "flow": "flow",
    "quant": "quant-network", "qnt": "quant-network",
}

# Nice display symbols for the context string
_DISPLAY = {
    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "casper-network": "CSPR",
    "cardano": "ADA", "ripple": "XRP", "dogecoin": "DOGE", "polkadot": "DOT",
    "avalanche-2": "AVAX", "matic-network": "POL", "chainlink": "LINK",
    "litecoin": "LTC", "tron": "TRX", "shiba-inu": "SHIB", "binancecoin": "BNB",
    "the-open-network": "TON", "sui": "SUI", "aptos": "APT", "arbitrum": "ARB",
    "optimism": "OP", "near": "NEAR", "cosmos": "ATOM", "uniswap": "UNI",
    "pepe": "PEPE", "monero": "XMR", "stellar": "XLM", "hedera-hashgraph": "HBAR",
    "filecoin": "FIL",
    "elrond-erd-2": "EGLD", "sei-network": "SEI", "injective-protocol": "INJ",
    "render-token": "RNDR", "fantom": "FTM", "sonic-3": "S", "algorand": "ALGO",
    "tezos": "XTZ", "vechain": "VET", "theta-token": "THETA", "immutable-x": "IMX",
    "kaspa": "KAS", "ondo-finance": "ONDO", "jupiter-exchange-solana": "JUP",
    "worldcoin-wld": "WLD", "aave": "AAVE", "maker": "MKR", "fetch-ai": "FET",
    "bonk": "BONK", "dogwifcoin": "WIF", "floki": "FLOKI", "the-sandbox": "SAND",
    "decentraland": "MANA", "axie-infinity": "AXS", "gala": "GALA", "chiliz": "CHZ",
    "eos": "EOS", "iota": "IOTA", "neo": "NEO", "dydx-chain": "DYDX",
    "ethena": "ENA", "pyth-network": "PYTH", "jasmycoin": "JASMY", "flow": "FLOW",
    "quant-network": "QNT",
}


def _display_symbol(cid: str) -> str:
    """Clean display symbol for a CoinGecko id (map first, else strip suffixes)."""
    if cid in _DISPLAY:
        return _DISPLAY[cid]
    s = cid
    for suf in ("-network", "-token", "-protocol", "-finance", "-erd-2",
                "-exchange-solana", "-2", "-3", "-coin"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    return s.upper()

# Simple in-memory cache: {frozenset(ids): (timestamp, data)}
_CACHE = {}
_TTL = 30  # seconds


def detect_coins(text: str, limit: int = 3) -> list:
    """Return CoinGecko ids for coins mentioned in the text (word-boundary match)."""
    low = text.lower()
    found = []
    # Longest keys first so 'shiba inu' / 'casper network' beat single words
    for key in sorted(COIN_MAP, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", low):
            cid = COIN_MAP[key]
            if cid not in found:
                found.append(cid)
        if len(found) >= limit:
            break
    return found


# Words that signal the user is asking about price / market of the current coin
_PRICE_INTENT = (
    "price", "prix", "cours", "combien", "worth", "value", "valeur", "how much",
    "pump", "dump", "chart", "graph", "graphique", "market cap", "marketcap",
    "mcap", "volume", "ath", "bull", "bear", "up", "down", "moon",
)


def has_price_intent(text: str) -> bool:
    low = text.lower()
    for w in _PRICE_INTENT:
        if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low):
            return True
    return False


def get_prices(ids: list) -> dict:
    """Fetch USD price + 24h change + market cap + volume for the given CoinGecko ids."""
    if not ids:
        return {}
    key = frozenset(ids)
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < _TTL:
        return cached[1]
    try:
        r = requests.get(
            COINGECKO_URL,
            params={
                "ids": ",".join(ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
            timeout=10,
        )
        r.raise_for_status()
        raw = r.json()
        data = {}
        for cid, v in raw.items():
            data[cid] = {
                "usd": v.get("usd"),
                "change_24h": v.get("usd_24h_change"),
                "market_cap": v.get("usd_market_cap"),
                "volume_24h": v.get("usd_24h_vol"),
            }
        _CACHE[key] = (now, data)
        return data
    except Exception as e:
        logger.warning("CoinGecko price fetch failed: %s", e)
        return {}


def _fmt_usd(n) -> str:
    if n is None:
        return "?"
    if n >= 1:
        return f"${n:,.2f}"
    return f"${n:.6f}".rstrip("0").rstrip(".")


def _fmt_big(n) -> str:
    if n is None:
        return "?"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if n >= div:
            return f"${n/div:.2f}{unit}"
    return f"${n:,.0f}"


def format_prices(ids: list) -> str:
    """Fetch + format live prices for the given CoinGecko ids. Returns None if none."""
    if not ids:
        return None
    prices = get_prices(ids)
    if not prices:
        return None
    lines = []
    for cid in ids:
        p = prices.get(cid)
        if not p or p.get("usd") is None:
            continue
        sym = _display_symbol(cid)
        chg = p.get("change_24h")
        arrow = "🟢" if (chg or 0) >= 0 else "🔴"
        chg_str = f"{chg:+.2f}%" if chg is not None else "n/a"
        lines.append(
            f"{arrow} {sym}: {_fmt_usd(p['usd'])} ({chg_str} 24h) · "
            f"MC {_fmt_big(p.get('market_cap'))} · Vol {_fmt_big(p.get('volume_24h'))}"
        )
    if not lines:
        return None
    return "LIVE PRICES (CoinGecko, real-time):\n" + "\n".join(lines)


def format_price_context(text: str) -> str:
    """Detect coins in the text, fetch live prices, and return a context string
    ready to inject into the LLM system prompt. Returns None if nothing found."""
    return format_prices(detect_coins(text))


# ─── Dynamic resolution for coins NOT in COIN_MAP (any token) ─────────────────

COINGECKO_SEARCH = "https://api.coingecko.com/api/v3/search"
DEXSCREENER_SEARCH = "https://api.dexscreener.com/latest/dex/search"

# Cache CoinGecko search resolutions (query -> id or None) to avoid rate limits
_SEARCH_CACHE = {}

# Words to ignore when guessing which token the user asked about
_STOPWORDS = {
    "parle", "moi", "de", "du", "des", "le", "la", "les", "un", "une", "et",
    "aujourd", "hui", "prix", "cours", "combien", "vaut", "sur", "the", "a",
    "tell", "me", "about", "what", "is", "price", "of", "how", "much", "whats",
    "give", "show", "quel", "est", "quoi", "penses", "tu", "info", "infos",
    "actu", "news", "token", "coin", "crypto", "please", "stp", "dis",
}


def _coingecko_search(query: str) -> str:
    """Resolve any coin name/ticker to a CoinGecko id via the search API (cached)."""
    key = query.lower().strip()
    if key in _SEARCH_CACHE:
        return _SEARCH_CACHE[key]
    result = None
    try:
        r = requests.get(COINGECKO_SEARCH, params={"query": query}, timeout=10)
        r.raise_for_status()
        coins = r.json().get("coins", [])
        if coins:
            result = coins[0].get("id")
    except Exception as e:
        logger.warning("CoinGecko search failed for %r: %s", query, e)
        return None  # don't cache transient errors (e.g. 429)
    _SEARCH_CACHE[key] = result  # cache hits AND misses (None)
    return result


def _dexscreener_search(query: str) -> str:
    """Last-resort price for DEX-only tokens. Returns a formatted line or None."""
    try:
        r = requests.get(DEXSCREENER_SEARCH, params={"q": query}, timeout=10)
        r.raise_for_status()
        pairs = r.json().get("pairs") or []
        if not pairs:
            return None
        # Pick the most liquid pair
        pairs.sort(key=lambda p: (p.get("liquidity") or {}).get("usd", 0), reverse=True)
        p = pairs[0]
        base = p.get("baseToken", {}).get("symbol", query.upper())
        price = p.get("priceUsd")
        if not price:
            return None
        chg = (p.get("priceChange") or {}).get("h24")
        vol = (p.get("volume") or {}).get("h24")
        liq = (p.get("liquidity") or {}).get("usd")
        arrow = "🟢" if (chg or 0) >= 0 else "🔴"
        chg_str = f"{chg:+.2f}%" if chg is not None else "n/a"
        chain = p.get("chainId", "?")
        return (
            "LIVE PRICE (DexScreener, real-time DEX data):\n"
            f"{arrow} {base}: {_fmt_usd(float(price))} ({chg_str} 24h) · "
            f"Vol {_fmt_big(vol)} · Liq {_fmt_big(liq)} · chain: {chain}"
        )
    except Exception as e:
        logger.warning("DexScreener search failed for %r: %s", query, e)
    return None


def _candidate_terms(text: str) -> list:
    """Extract likely coin name/ticker candidates from a message."""
    words = re.findall(r"[a-z0-9]{2,}", text.lower())
    cands = [w for w in words if w not in _STOPWORDS]
    # Longest first (more specific), keep a few
    return sorted(set(cands), key=len, reverse=True)[:3]


# Talk-about triggers: only run the (network) dynamic search when the user
# clearly refers to a coin, to avoid searching on unrelated chit-chat.
_ASK_TRIGGERS = (
    "parle", "tell", "about", "info", "infos", "news", "actu", "penses",
    "dis", "explique", "explain", "cest quoi", "what is",
)


def should_resolve(text: str) -> bool:
    """True if we should attempt dynamic coin resolution (CoinGecko/DexScreener).
    Requires an explicit crypto/price/ask signal to avoid hammering the API on
    generic chit-chat ('alors', 'ok', 'incroyable' → no search)."""
    if has_price_intent(text):
        return True
    low = text.lower()
    if any(t in low for t in _ASK_TRIGGERS):
        return True
    # A bare '$TICKER' also counts as an explicit crypto reference
    if re.search(r"\$[a-z0-9]{2,10}", low):
        return True
    return False


def resolve_context(text: str):
    """Full market resolver. Returns (context_string_or_None, ids_list).
    1) known coins (COIN_MAP)  2) CoinGecko search  3) DexScreener fallback."""
    ids = detect_coins(text)
    if ids:
        return format_prices(ids), ids

    # Try to resolve an unknown coin the user asked about
    for cand in _candidate_terms(text):
        cid = _coingecko_search(cand)
        if cid:
            ctx = format_prices([cid])
            if ctx:
                return ctx, [cid]
    # DEX-only token fallback
    for cand in _candidate_terms(text):
        ctx = _dexscreener_search(cand)
        if ctx:
            return ctx, []  # no CoinGecko id to remember
    return None, []


# id -> best human search term (prefer longest single-word name, not the ticker)
_ID_TO_NAME = {}
for _k, _v in COIN_MAP.items():
    if " " in _k:
        continue  # avoid multi-word keys (bad for full-text AND queries)
    if _v not in _ID_TO_NAME or len(_k) > len(_ID_TO_NAME[_v]):
        _ID_TO_NAME[_v] = _k


def coin_name(cid: str) -> str:
    """Human-readable single-word name for a CoinGecko id (for news search)."""
    return _ID_TO_NAME.get(cid, cid.split("-")[0])


def news_query(text: str, ids: list = None) -> str:
    """Build a clean keyword for full-text news search.
    Uses the detected coin name (not the raw French/English sentence, which
    poisons plainto_tsquery with non-stopwords). Returns None if nothing usable."""
    if ids:
        return coin_name(ids[0])
    cands = _candidate_terms(text)
    return cands[0] if cands else None


# ─── Historical price research (CoinGecko market_chart) ──────────────────────

COINGECKO_CHART = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"

# History-question intent in FR/EN
_HISTORY_TRIGGERS = (
    "last time", "dernière fois", "derniere fois", "était à", "etait a",
    "when was", "il y a", "ago", "history", "historique", "y a combien",
    "atteint", "reached", "back then", "depuis quand", "since when",
    "il etait", "il était",
)

_HIST_CACHE = {}  # (id, days) -> (ts, [[ms, price], ...])


def has_history_intent(text: str) -> bool:
    low = text.lower()
    return any(t in low for t in _HISTORY_TRIGGERS)


def _parse_target_price(text: str):
    """Extract a target USD price from text like '62000', '62k', '$1.2', '0.5$'."""
    low = text.lower().replace(",", "")
    # 62k / 1.5k
    m = re.search(r"(\d+(?:\.\d+)?)\s*k\b", low)
    if m:
        return float(m.group(1)) * 1000
    # plain numbers (>= 0.0001), prefer ones near a $ or the largest
    nums = re.findall(r"\$?\s*(\d+(?:\.\d+)?)", low)
    vals = [float(x) for x in nums if x]
    vals = [v for v in vals if v >= 0.0001]
    return max(vals) if vals else None


def price_history(cid: str, days: int = 365):
    """CoinGecko daily price history: list of [timestamp_ms, price]. Cached 1h."""
    key = (cid, days)
    now = time.time()
    c = _HIST_CACHE.get(key)
    if c and now - c[0] < 3600:
        return c[1]
    try:
        r = requests.get(
            COINGECKO_CHART.format(id=cid),
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            timeout=15,
        )
        r.raise_for_status()
        prices = r.json().get("prices", [])
        _HIST_CACHE[key] = (now, prices)
        return prices
    except Exception as e:
        logger.warning("CoinGecko history failed for %s: %s", cid, e)
        return []


def last_time_near(cid: str, target: float, tol_pct: float = 3.0, days: int = 365):
    """Most recent date the coin traded within tol_pct% of `target`. Returns dict or None."""
    prices = price_history(cid, days)
    if not prices:
        return None
    tol = abs(target) * tol_pct / 100.0
    from datetime import datetime, timezone
    for ts, p in reversed(prices):  # most recent first
        if abs(p - target) <= tol:
            d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            return {"date": d.strftime("%Y-%m-%d"), "price": p, "target": target}
    # Not found in window → report min/max reached instead
    lows = min(prices, key=lambda x: x[1])
    highs = max(prices, key=lambda x: x[1])
    return {
        "not_found": True, "target": target, "days": days,
        "low": lows[1], "high": highs[1],
    }


def history_context(text: str, ids: list = None) -> str:
    """If the user asks a historical price question with a target value, return a
    context block from CoinGecko history. Returns None if not applicable."""
    if not has_history_intent(text):
        return None
    if not ids:
        ids = detect_coins(text)
    if not ids:
        return None
    cid = ids[0]
    sym = _display_symbol(cid)
    target = _parse_target_price(text)
    if target is None:
        return None
    res = last_time_near(cid, target, tol_pct=3.0, days=365)
    if not res:
        return None
    if res.get("not_found"):
        return (
            f"PRICE HISTORY ({sym}, CoinGecko, last 365 days): {sym} did NOT trade near "
            f"{_fmt_usd(target)} in the last year. 1y range: low {_fmt_usd(res['low'])}, "
            f"high {_fmt_usd(res['high'])}."
        )
    return (
        f"PRICE HISTORY ({sym}, CoinGecko): the most recent time {sym} was near "
        f"{_fmt_usd(target)} was on {res['date']} (actual {_fmt_usd(res['price'])}). "
        f"State this date and note it's based on daily historical data."
    )


