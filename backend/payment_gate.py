import base64
import json
import os
import secrets
import time
from typing import Any, Dict, Optional


SERVICE_NAME = os.getenv("SERVICE_NAME", "trappistai")


def create_payment_challenge(resource_url: str, amount: float, currency: str = "CSPR", ttl_seconds: int = 300) -> str:
    """Create a short-lived challenge token for a resource that requires payment."""
    now = int(time.time())
    challenge = {
        "type": "resource-payment-gate",
        "resource": resource_url,
        "amount": amount,
        "currency": currency.upper(),
        "issued_at": now,
        "expires_at": now + ttl_seconds,
        "nonce": secrets.token_hex(8),
        "service": SERVICE_NAME,
    }

    payload = json.dumps(challenge, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def verify_payment_proof(challenge_token: str, proof_payload: Optional[Dict[str, Any]]) -> bool:
    """Validate a proof submitted by the client for a previously issued challenge."""
    if not challenge_token or not isinstance(proof_payload, dict):
        return False

    try:
        raw = challenge_token.encode("ascii")
        if len(raw) % 4:
            raw += b"=" * (4 - len(raw) % 4)
        decoded = base64.urlsafe_b64decode(raw)
        challenge = json.loads(decoded.decode("utf-8"))
    except Exception:
        return False

    now = int(time.time())
    if now > challenge.get("expires_at", 0):
        return False

    receipt = proof_payload.get("receipt") or proof_payload.get("proof") or {}
    if not isinstance(receipt, dict):
        return False

    if receipt.get("status") != "confirmed":
        return False

    if receipt.get("amount") != challenge.get("amount"):
        return False

    if str(receipt.get("currency", "")).upper() != str(challenge.get("currency", "")).upper():
        return False

    return True
