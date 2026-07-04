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
}

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


def format_price_context(text: str) -> str:
    """Detect coins in the text, fetch live prices, and return a context string
    ready to inject into the LLM system prompt. Returns None if nothing found."""
    ids = detect_coins(text)
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
        sym = _DISPLAY.get(cid, cid.upper())
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
