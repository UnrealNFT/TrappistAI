"""
Shared Casper JSON-RPC client with fallbacks and DNS-over-HTTPS support.

The sandboxed / cloud environments where TrappistAI runs sometimes have broken
UDP DNS.  When a hostname cannot be resolved by the OS, we resolve it via
DNS-over-HTTPS and connect by IP while sending the original Host header.
TLS verification is enabled for hostname-based URLs and disabled only for
bare-IP connections (where the certificate CN cannot match).
"""
import os
import socket
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx


# Curated public Casper mainnet RPC endpoints.  These are well-known hostnames
# maintained by the Casper Association / ecosystem.  Avoid hard-coding IPs:
# they go stale and stop serving the RPC path (as happened with the previous
# 52.44.180.130 / 98.86.11.64 fallbacks).
CSPR_MAINNET_RPCS = [
    "https://node.mainnet.casper.network/rpc",
    "https://rpc.mainnet.casperlabs.io/rpc",
    "https://rpc.casper.network/rpc",
    "https://casper-node.tor.us/rpc",
    "https://api.cspr.live/rpc",
]

CSPR_TESTNET_RPCS = [
    "https://node.testnet.casper.network/rpc",
    "https://rpc.testnet.casperlabs.io/rpc",
    "https://rpc.testnet.casper.network/rpc",
]

_DOH_PROVIDERS = [
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query",
]


def _is_ip(address: str) -> bool:
    """Return True if *address* is an IPv4/IPv6 literal."""
    try:
        socket.inet_pton(socket.AF_INET, address)
        return True
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, address)
        return True
    except OSError:
        return False


def _resolve_via_doh(hostname: str) -> Optional[str]:
    """Resolve a hostname A record using DNS-over-HTTPS."""
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
            # Follow CNAME chain if no direct A record.
            for answer in answers:
                if answer.get("type") == 5:
                    ip = _resolve_via_doh(answer["data"].rstrip("."))
                    if ip:
                        return ip
        except Exception as e:
            print(f"⏳ DoH resolver {provider} failed for {hostname}: {e}")
    return None


def _resolve_hostname(hostname: str) -> Optional[str]:
    """Try system DNS, then DoH.  Returns an IP if a bypass is needed."""
    try:
        socket.getaddrinfo(hostname, None)
        return None  # System DNS works; no override needed.
    except OSError:
        return _resolve_via_doh(hostname)


def _build_rpc_url(url: str) -> Tuple[str, Optional[str], bool]:
    """
    Return (request_url, host_header_override, verify_ssl).

    If the hostname resolves via system DNS we keep the original URL and verify
    TLS.  If system DNS is broken but DoH resolves the name, we connect by IP
    and preserve the Host header; TLS verification is disabled because the cert
    will not match the IP address.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return url, None, True

    if _is_ip(hostname):
        return url, None, False

    ip = _resolve_hostname(hostname)
    if ip:
        netloc = f"{ip}:{parsed.port}" if parsed.port else ip
        replaced = parsed._replace(netloc=netloc).geturl()
        print(f"  Resolved {hostname} -> {ip} via DoH")
        return replaced, hostname, False

    return url, None, True


def get_rpc_urls(network: str = "mainnet") -> List[str]:
    """Return the curated RPC list for *network* with optional env override."""
    env_var = "CASPER_RPC_URL" if network == "mainnet" else "CASPER_TESTNET_RPC"
    override = os.getenv(env_var, "").strip()
    base = list(CSPR_MAINNET_RPCS if network == "mainnet" else CSPR_TESTNET_RPCS)
    if override and override not in base:
        return [override] + base
    return base


async def rpc_call_single(
    url: str, method: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Make a single JSON-RPC call to one Casper node URL."""
    call_url, host_override, verify = _build_rpc_url(url)
    headers = {"Content-Type": "application/json"}
    if host_override:
        headers["Host"] = host_override

    async with httpx.AsyncClient(timeout=30.0, verify=verify) as client:
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


async def rpc_call(
    method: str,
    params: Dict[str, Any],
    *,
    network: str = "mainnet",
    custom_urls: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Make a JSON-RPC call to a Casper node, falling back to alternate endpoints.

    Args:
        method: JSON-RPC method name.
        params: JSON-RPC params dict.
        network: "mainnet" or "testnet".
        custom_urls: Optional explicit list of URLs to try (ignores defaults).

    Returns:
        The JSON-RPC result object.

    Raises:
        The last encountered exception if all endpoints fail.
    """
    endpoints = custom_urls if custom_urls else get_rpc_urls(network)
    last_error: Optional[Exception] = None
    for url in endpoints:
        try:
            return await rpc_call_single(url, method, params)
        except Exception as e:
            last_error = e
            print(f"⏳ RPC fallback {url} failed: {e}")
    if last_error is None:
        raise RuntimeError("No RPC endpoints configured")
    raise last_error
