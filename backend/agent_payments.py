"""
Agent x402 payment layer for TrappistAI.

This module implements the server-side x402 protocol for AI agents that want
 to use TrappistAI generation services without buying a token credit pack.

Flow:
1. Agent POSTs /api/v1/agent/generate/image with no proof.
2. Server returns HTTP 402 + PAYMENT-REQUIRED header with a native-CSPR
   transfer requirement priced in USD and converted to CSPR in real time.
3. Agent signs and broadcasts a native CSPR transfer to TREASURY_WALLET for
   the exact amount shown, on mainnet (chain_name='casper').
4. Agent re-posts the same request with header PAYMENT-SIGNATURE containing
   base64({"deployJson": <signed deploy>, "wallet": <payer public key hex>}).
5. Server verifies the deploy on-chain, checks the amount and recipient,
   records the payment idempotently, and runs the generation.

This is intentionally separate from the human token-credit flow and from the
CEP-18/WCSPR x402 path so that nothing existing is touched.
"""
import os
import json
import base64
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

import httpx
from sqlalchemy import text
from urllib.parse import urlparse

from prices import get_cspr_usd_rate
from db import get_db_session


# ---------------------------------------------------------------------------
# DNS-over-HTTPS resolver (for environments with broken UDP DNS, e.g. Render)
# ---------------------------------------------------------------------------
_DOH_PROVIDERS = [
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query",
]


def _resolve_via_doh(hostname: str) -> Optional[str]:
    """Resolve a hostname A record using DNS-over-HTTPS over plain HTTP."""
    for provider in _DOH_PROVIDERS:
        try:
            r = httpx.get(
                provider,
                params={"name": hostname, "type": "A"},
                headers={"Accept": "application/dns-json"},
                timeout=15.0,
                follow_redirects=True,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("Status") != 0:
                continue
            answers = data.get("Answer", [])
            for answer in answers:
                if answer.get("type") == 1:
                    return answer["data"]
            # If no direct A record, follow the CNAME chain.
            for answer in answers:
                if answer.get("type") == 5:
                    ip = _resolve_via_doh(answer["data"].rstrip("."))
                    if ip:
                        return ip
        except Exception as e:
            print(f"⏳ DoH resolver {provider} failed for {hostname}: {e}")
    return None


def _resolve_hostname(hostname: str) -> Optional[str]:
    """Try system DNS, then DoH."""
    try:
        import socket
        socket.getaddrinfo(hostname, None)
        return None  # System DNS works, no IP override needed.
    except OSError:
        return _resolve_via_doh(hostname)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TREASURY_WALLET = os.getenv(
    "TREASURY_WALLET",
    "0202e5a88e2baf0306484eced583f8642902752668b4b91070dc2abd01d6304d2cd8",
).lower().strip()

# Must be mainnet for real money.
AGENT_CHAIN_NAME = os.getenv("AGENT_CHAIN_NAME", "casper")

CASPER_RPC_URL = os.getenv("CASPER_RPC_URL", "https://node.mainnet.casper.network/rpc")

# Fallback endpoints tried in order if the primary RPC fails to resolve.
# The last entry is the current IP of node.mainnet.casper.network for
# environments where DNS resolution is broken (e.g. some Render instances).
CASPER_RPC_FALLBACKS = [
    "https://api.mainnet.casper.network/rpc",
    "https://cspr.live/rpc",
    "https://rpc.mainnet.casper.network/rpc",
    "https://98.86.11.64/rpc",
]

# Prices in USD.  They are converted to CSPR at request time using CoinGecko.
AGENT_PRICING_USD: Dict[str, float] = {
    "image": 0.03,
    "music": 1.00,
    "3d": 2.00,
}

# Minimum CSPR price to avoid microscopic amounts if CSPR moons.
MIN_CSPR_PRICE: Dict[str, float] = {
    "image": 1.0,
    "music": 10.0,
    "3d": 20.0,
}

X402_VERSION = 1
X402_MEMO_PREFIX = "TrappistAI agent"


# ---------------------------------------------------------------------------
# Pricing helpers
# ---------------------------------------------------------------------------
def get_resource_price(resource: str) -> float:
    """Return the USD price for a resource."""
    if resource not in AGENT_PRICING_USD:
        raise ValueError(f"Unknown resource: {resource}")
    return AGENT_PRICING_USD[resource]


def usd_to_cspr(usd_amount: float) -> float:
    """Convert USD amount to CSPR using the live CoinGecko rate."""
    rate = get_cspr_usd_rate()
    if rate <= 0:
        raise ValueError("Invalid CSPR/USD rate")
    return usd_amount / rate


def get_price_cspr(resource: str) -> float:
    """Return the final CSPR price for a resource, floored by MIN_CSPR_PRICE."""
    usd = get_resource_price(resource)
    cspr = usd_to_cspr(usd)
    return max(cspr, MIN_CSPR_PRICE.get(resource, 0.0))


def cspr_to_motes(cs: float) -> str:
    """Return a string of motes (1 CSPR = 1e9 motes) without scientific notation."""
    return str(int(Decimal(str(cs)) * Decimal("1_000_000_000")))


# ---------------------------------------------------------------------------
# x402 challenge
# ---------------------------------------------------------------------------
def create_agent_challenge(resource: str, resource_url: str, description: str) -> str:
    """Build the base64-encoded PAYMENT-REQUIRED header for an agent request."""
    cspr = get_price_cspr(resource)
    amount_motes = cspr_to_motes(cspr)

    payload = {
        "x402Version": X402_VERSION,
        "error": "payment_required",
        "resource": {
            "url": resource_url,
            "description": description,
            "mimeType": "application/json",
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": f"casper:{AGENT_CHAIN_NAME}",
                "asset": "CSPR",
                "amount": amount_motes,
                "payTo": TREASURY_WALLET,
                "resource": resource_url,
                "description": description,
                "extra": {
                    "symbol": "CSPR",
                    "decimals": "9",
                    "usdPrice": str(get_resource_price(resource)),
                    "csprPrice": f"{cspr:.6f}",
                    "memo": f"{X402_MEMO_PREFIX}: {description}",
                },
            }
        ],
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def create_payment_response(deploy_hash: str, url: str, cost_cspr: float, cost_usd: float) -> str:
    """Build the base64-encoded PAYMENT-RESPONSE header returned on success."""
    payload = {
        "status": "settled",
        "transactionHash": deploy_hash,
        "resourceUrl": url,
        "costCspr": f"{cost_cspr:.6f}",
        "costUsd": f"{cost_usd:.6f}",
        "timestamp": int(datetime.utcnow().timestamp()),
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


# ---------------------------------------------------------------------------
# On-chain verification helpers
# ---------------------------------------------------------------------------
def _build_rpc_url(url: str) -> tuple[str, Optional[str]]:
    """
    Return the URL to use for the RPC call and an optional Host header override.
    If the system DNS cannot resolve the hostname, we resolve it via DNS-over-HTTPS
    and connect by IP while preserving the original Host header.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return url, None

    # If it's already an IP, no need to override.
    try:
        import socket
        socket.inet_aton(hostname)
        return url, None
    except OSError:
        pass

    ip = _resolve_hostname(hostname)
    if ip:
        netloc = f"{ip}:{parsed.port}" if parsed.port else ip
        replaced = parsed._replace(netloc=netloc).geturl()
        print(f"  Resolved {hostname} -> {ip} via DoH")
        return replaced, hostname
    return url, None


async def _rpc_call_single(url: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make a single JSON-RPC call to one Casper node URL."""
    call_url, host_override = _build_rpc_url(url)
    headers = {"Content-Type": "application/json"}
    if host_override:
        headers["Host"] = host_override

    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        r = await client.post(
            call_url,
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        )
        r.raise_for_status()
        data = r.json()
    if "error" in data:
        raise ValueError(data["error"].get("message", str(data["error"])))
    return data.get("result", {})


async def _rpc_call(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make a JSON-RPC call to the Casper node, falling back to alternate endpoints."""
    endpoints = [CASPER_RPC_URL] + CASPER_RPC_FALLBACKS
    last_error = None
    for url in endpoints:
        try:
            return await _rpc_call_single(url, method, params)
        except Exception as e:
            last_error = e
            print(f"⏳ RPC fallback {url} failed: {e}")
    raise last_error


def _extract_execution_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the execution_result dict, handling Casper 1.x and 2.0 formats."""
    if isinstance(result.get("execution_info"), dict):
        er = result["execution_info"].get("execution_result")
        if isinstance(er, dict):
            return er
    elif isinstance(result.get("execution_results"), list) and result["execution_results"]:
        first = result["execution_results"][0]
        if isinstance(first, dict):
            return first.get("result")
    return None


def _extract_transfer_amount(deploy: Dict[str, Any]) -> Optional[int]:
    """Return the transfer amount in motes from a native CSPR transfer deploy."""
    session = deploy.get("session", {})
    transfer = session.get("Transfer") or session.get("transfer")
    if not transfer or not isinstance(transfer, dict):
        return None
    args = transfer.get("args", [])
    for arg in args:
        if isinstance(arg, (list, tuple)) and len(arg) >= 2 and arg[0] == "amount":
            parsed = arg[1].get("parsed") if isinstance(arg[1], dict) else None
            if parsed is not None:
                return int(parsed)
    return None


def _extract_transfer_target(deploy: Dict[str, Any]) -> Optional[str]:
    """Return the target public key / hash of a native CSPR transfer deploy."""
    session = deploy.get("session", {})
    transfer = session.get("Transfer") or session.get("transfer")
    if not transfer or not isinstance(transfer, dict):
        return None
    args = transfer.get("args", [])
    for arg in args:
        if isinstance(arg, (list, tuple)) and len(arg) >= 2 and arg[0] == "target":
            parsed = arg[1].get("parsed") if isinstance(arg[1], dict) else None
            if parsed:
                return str(parsed).lower().strip()
    return None


def _extract_deploy_hash(deploy: Dict[str, Any]) -> Optional[str]:
    """Return the deploy hash from a deploy dict."""
    if isinstance(deploy.get("hash"), str):
        return deploy["hash"].lower().strip()
    return None


# ---------------------------------------------------------------------------
# Idempotency / persistence
# ---------------------------------------------------------------------------
def _is_payment_used(deploy_hash: str) -> bool:
    """Check whether a deploy hash has already been used for an agent payment."""
    clean_hash = deploy_hash.lower().strip().replace("hash-", "").replace("deploy-", "")
    with get_db_session() as conn:
        row = conn.execute(
            text("SELECT id FROM agent_payments WHERE deploy_hash = :tx LIMIT 1"),
            {"tx": clean_hash},
        ).fetchone()
        return row is not None


def _record_agent_payment(
    deploy_hash: str,
    wallet: str,
    amount_cspr: float,
    amount_motes: int,
    resource: str,
    cost_usd: float,
    url: str,
) -> None:
    """Record an agent payment idempotently."""
    clean_hash = deploy_hash.lower().strip().replace("hash-", "").replace("deploy-", "")
    with get_db_session() as conn:
        trans = conn.begin()
        try:
            conn.execute(
                text("""
                    INSERT INTO agent_payments
                        (deploy_hash, wallet_address, amount_cspr, amount_motes,
                         resource, cost_usd, generated_url, status, created_at)
                    VALUES (:tx, :wallet, :amount, :motes, :resource, :usd, :url,
                            'settled', CURRENT_TIMESTAMP)
                    ON CONFLICT (deploy_hash) DO NOTHING
                """),
                {
                    "tx": clean_hash,
                    "wallet": wallet.lower().strip(),
                    "amount": amount_cspr,
                    "motes": amount_motes,
                    "resource": resource,
                    "usd": cost_usd,
                    "url": url,
                },
            )
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise e


# ---------------------------------------------------------------------------
# Main settle function
# ---------------------------------------------------------------------------
async def settle_agent_payment(deploy_json: Dict[str, Any], wallet: str, resource: str) -> Dict[str, Any]:
    """
    Verify a native CSPR transfer on mainnet and return settlement metadata.

    Raises ValueError with a human-readable message if validation fails.
    """
    if not deploy_json or not wallet or not resource:
        raise ValueError("Missing deployJson, wallet, or resource")

    wallet = wallet.lower().strip()

    actual_deploy = deploy_json.get("deploy", deploy_json)

    # 1. Chain check
    chain_name = actual_deploy.get("header", {}).get("chain_name")
    if chain_name != AGENT_CHAIN_NAME:
        raise ValueError(f"Invalid chain: expected {AGENT_CHAIN_NAME}, got {chain_name}")

    # 2. Deploy hash & idempotency
    deploy_hash = _extract_deploy_hash(actual_deploy)
    if not deploy_hash:
        raise ValueError("Could not extract deploy hash")

    clean_hash = deploy_hash.replace("hash-", "").replace("deploy-", "")
    if _is_payment_used(clean_hash):
        raise ValueError("Deploy hash already used")

    # 3. Expected amount
    required_cspr = get_price_cspr(resource)
    required_motes = int(Decimal(str(required_cspr)) * Decimal("1_000_000_000"))

    # 4. Verify on-chain with polling (max ~75s)
    exec_result = None
    for attempt in range(1, 26):
        try:
            result = await _rpc_call("info_get_deploy", {"deploy_hash": clean_hash})
            er = _extract_execution_result(result)
            if isinstance(er, dict):
                exec_result = er
                break
        except Exception as fetch_err:
            print(f"⏳ Agent payment verify attempt {attempt}: {fetch_err}")
        await asyncio.sleep(3)

    if not isinstance(exec_result, dict):
        raise ValueError("Deploy not yet executed on-chain. Retry later.")

    # 5. Execution success check
    error_message = None
    v2 = exec_result.get("Version2")
    if isinstance(v2, dict):
        error_message = v2.get("error_message")
    elif "Failure" in exec_result:
        error_message = exec_result["Failure"].get("error_message", "Unknown error")

    if error_message:
        raise ValueError(f"Payment failed on-chain: {error_message}")

    # 6. Validate transfer amount & recipient
    deploy_from_chain = None
    if isinstance(result, dict):
        deploy_from_chain = result.get("deploy")

    if not deploy_from_chain:
        raise ValueError("Could not fetch deploy details from chain")

    amount_motes = _extract_transfer_amount(deploy_from_chain)
    if amount_motes is None:
        raise ValueError("Could not extract transfer amount from deploy")

    if amount_motes < required_motes:
        raise ValueError(
            f"Insufficient payment: sent {amount_motes} motes, "
            f"required {required_motes} motes"
        )

    target = _extract_transfer_target(deploy_from_chain)
    if not target:
        raise ValueError("Could not extract transfer target from deploy")

    # Target can be public key hex or account hash; compare both forms.
    treasury_forms = {TREASURY_WALLET}
    if target not in treasury_forms:
        # Allow account-hash- target matching the treasury account-hash if we could derive it.
        # For mainnet we currently require the exact treasury public key as target.
        raise ValueError(f"Invalid recipient: expected treasury wallet, got {target}")

    cost_usd = get_resource_price(resource)
    return {
        "deploy_hash": clean_hash,
        "amount_motes": amount_motes,
        "amount_cspr": amount_motes / 1e9,
        "required_cspr": required_cspr,
        "cost_usd": cost_usd,
        "wallet": wallet,
        "resource": resource,
    }
