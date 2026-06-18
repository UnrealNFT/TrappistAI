"""
x402 Payment Protocol Utilities for Casper Network
Based on: https://github.com/make-software/casper-x402
"""
import base64
import json
import hashlib
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass


# x402 Configuration
CASPER_CHAIN_ID = "casper:casper-test"  # or casper:casper for mainnet
CEP18_CONTRACT = "hash-8c6e0c3600d3371e3d898b9506fd60155fbd126877a35b88171b7e0e7ba27dd9"  # WCSPR testnet
ASSET_NAME = "Wrapped Casper"
ASSET_SYMBOL = "WCSPR"
ASSET_VERSION = "1"
ASSET_DECIMALS = 9

RECEIVER_WALLET = "0202e5a88e2baf0306484eced583f8642902752668b4b91070dc2abd01d6304d2cd8"


@dataclass
class PaymentRequirement:
    """x402 Payment Requirement (what the server accepts)"""
    scheme: str = "exact"
    network: str = CASPER_CHAIN_ID
    asset: str = CEP18_CONTRACT
    amount: str = "10000000000"  # 10 CSPR in motes
    payTo: str = RECEIVER_WALLET
    maxTimeoutSeconds: int = 3600
    extra: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme": self.scheme,
            "network": self.network,
            "asset": self.asset,
            "amount": self.amount,
            "payTo": self.payTo,
            "maxTimeoutSeconds": self.maxTimeoutSeconds,
            "extra": self.extra or {
                "name": ASSET_NAME,
                "symbol": ASSET_SYMBOL,
                "version": ASSET_VERSION,
                "decimals": str(ASSET_DECIMALS)
            }
        }


def create_payment_required_header(
    resource_url: str,
    description: str,
    amount_cspr: int = 10
) -> str:
    """
    Create x402 PAYMENT-REQUIRED header (base64 encoded JSON)
    
    Returns HTTP 402 with this header to initiate x402 payment flow
    """
    amount_motes = str(amount_cspr * 1_000_000_000)
    
    requirement = PaymentRequirement(amount=amount_motes)
    
    payment_required = {
        "x402Version": 2,
        "error": "payment_required",
        "resource": {
            "url": resource_url,
            "description": description,
            "mimeType": "application/json"
        },
        "accepts": [requirement.to_dict()]
    }
    
    # Encode to base64
    json_str = json.dumps(payment_required)
    return base64.b64encode(json_str.encode()).decode()


def parse_payment_signature(payment_signature_header: str) -> Dict[str, Any]:
    """
    Parse x402 PAYMENT-SIGNATURE header (base64 encoded PaymentPayload)
    """
    try:
        decoded = base64.b64decode(payment_signature_header)
        return json.loads(decoded)
    except Exception as e:
        raise ValueError(f"Invalid PAYMENT-SIGNATURE header: {e}")


def verify_payment_payload(payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Verify x402 PaymentPayload structure and constraints
    
    Returns: (is_valid, error_message)
    """
    try:
        # Check x402Version
        if payload.get("x402Version") != 2:
            return False, "Unsupported x402 version"
        
        # Check required fields
        if "resource" not in payload:
            return False, "Missing resource"
        
        if "accepted" not in payload:
            return False, "Missing accepted requirement"
        
        if "payload" not in payload:
            return False, "Missing payment payload"
        
        accepted = payload["accepted"]
        payment = payload["payload"]
        
        # Verify scheme
        if accepted.get("scheme") != "exact":
            return False, "Unsupported payment scheme"
        
        # Verify network
        if not accepted.get("network", "").startswith("casper:"):
            return False, "Invalid network"
        
        # Verify payTo matches our receiver
        if accepted.get("payTo", "").lower() != RECEIVER_WALLET.lower():
            return False, "Invalid payTo address"
        
        # Check authorization fields
        auth = payment.get("authorization", {})
        required_fields = ["from", "to", "value", "validAfter", "validBefore", "nonce"]
        for field in required_fields:
            if field not in auth:
                return False, f"Missing authorization.{field}"
        
        # Check signature fields
        if "publicKey" not in payment:
            return False, "Missing publicKey"
        
        if "signature" not in payment:
            return False, "Missing signature"
        
        # Verify time bounds
        now = int(time.time())
        valid_after = int(auth["validAfter"])
        valid_before = int(auth["validBefore"])
        
        if now < valid_after:
            return False, "Payment not yet valid"
        
        if now > valid_before:
            return False, "Payment expired"
        
        # All checks passed
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def verify_eip712_signature(
    payload: Dict[str, Any],
    accepted: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Verify EIP-712 signature for Casper CEP-18 transfer_with_authorization
    
    This is a simplified version - in production, use casper-eip-712 library
    """
    try:
        auth = payload["authorization"]
        public_key = payload["publicKey"]
        signature = payload["signature"]
        
        # TODO: Implement full EIP-712 verification
        # For now, we'll rely on on-chain verification during settlement
        # The Casper network will reject invalid signatures
        
        # Basic sanity checks
        if not signature or len(signature) < 130:  # 01/02 prefix + 128 hex chars
            return False, "Invalid signature format"
        
        if not public_key or len(public_key) != 68:  # 01/02 prefix + 66 hex chars
            return False, "Invalid public key format"
        
        # Verify public key matches "from" address
        # In Casper, account hash = blake2b(public_key)[1:]
        # This is a simplified check - proper implementation should verify the hash
        from_address = auth["from"].lower()
        if not from_address.startswith("00"):
            return False, "Invalid from address format"
        
        return True, None
        
    except Exception as e:
        return False, f"Signature verification error: {str(e)}"


def create_payment_response_header(
    deploy_hash: str,
    status: str = "settled",
    message: str = "Payment confirmed on-chain"
) -> str:
    """
    Create x402 PAYMENT-RESPONSE header (base64 encoded settlement result)
    
    Return this in HTTP 200 response after successful settlement
    """
    response = {
        "status": status,
        "transactionHash": deploy_hash,
        "message": message,
        "timestamp": int(time.time())
    }
    
    json_str = json.dumps(response)
    return base64.b64encode(json_str.encode()).decode()
