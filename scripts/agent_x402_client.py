#!/usr/bin/env python3
"""
TrappistAI Agent x402 Client
============================

Example Python client that demonstrates the full agent payment flow:

1. Request an image generation without payment.
2. Receive HTTP 402 + a PAYMENT-REQUIRED challenge.
3. Sign a native CSPR transfer on mainnet for the amount shown.
4. Submit the signed deploy as a PAYMENT-SIGNATURE header.
5. Receive the generated image URL.

This script handles steps 1, 2, 4 and 5. Step 3 (signing the deploy) must be
performed by the agent's wallet or SDK, because there is no widely available
Python SDK for signing Casper deploys in production.

Usage
-----
# Step 1: get the payment challenge
python scripts/agent_x402_client.py \
  --wallet 01a1b2c3d4e5... \
  --prompt "a cyberpunk cat in a neon city"

# Step 2: sign the native CSPR transfer with your wallet, save it as
# signed_deploy.json, then submit the payment proof
python scripts/agent_x402_client.py \
  --wallet 01a1b2c3d4e5... \
  --prompt "a cyberpunk cat in a neon city" \
  --deploy-file signed_deploy.json
"""

import argparse
import base64
import json
import sys
from pathlib import Path

import requests

DEFAULT_API_URL = "https://trappist.land"


def decode_header(header_value: str) -> dict:
    """Decode a base64-encoded x402 header."""
    return json.loads(base64.b64decode(header_value).decode())


def encode_payment_signature(deploy_json: dict, wallet: str) -> str:
    """Build the base64 PAYMENT-SIGNATURE payload."""
    payload = {"deployJson": deploy_json, "wallet": wallet}
    return base64.b64encode(json.dumps(payload).encode()).decode()


def request_challenge(api_url: str, wallet: str, prompt: str) -> dict:
    """Step 1: request generation without payment and parse the 402 challenge."""
    url = f"{api_url.rstrip('/')}/api/v1/agent/generate/image"
    body = {"wallet": wallet, "prompt": prompt}

    print(f"\n[1/3] POST {url}")
    print(f"      Body: {json.dumps(body)}")

    response = requests.post(url, json=body, timeout=30)

    print(f"      HTTP {response.status_code}")

    if response.status_code != 402:
        print(f"\nUnexpected response: {response.text}")
        sys.exit(1)

    payment_required_header = response.headers.get("PAYMENT-REQUIRED")
    if not payment_required_header:
        print("\nMissing PAYMENT-REQUIRED header in 402 response.")
        sys.exit(1)

    challenge = decode_header(payment_required_header)

    print("\n[2/3] Received x402 Payment Required challenge:")
    print(json.dumps(challenge, indent=2))

    return challenge


def extract_payment_details(challenge: dict) -> dict:
    """Extract human-readable payment details from the challenge."""
    accepts = challenge.get("accepts", [{}])[0]
    extra = accepts.get("extra", {})
    return {
        "resource": challenge.get("resource", {}).get("url"),
        "description": challenge.get("resource", {}).get("description"),
        "network": accepts.get("network"),
        "asset": accepts.get("asset"),
        "amount_motes": accepts.get("amount"),
        "pay_to": accepts.get("payTo"),
        "cost_usd": extra.get("usdPrice"),
        "cost_cspr": extra.get("csprPrice"),
        "decimals": int(extra.get("decimals", 9)),
        "memo": extra.get("memo"),
    }


def submit_payment(
    api_url: str, wallet: str, prompt: str, deploy_json: dict
) -> dict:
    """Step 2: submit the signed deploy and receive the generated image URL."""
    url = f"{api_url.rstrip('/')}/api/v1/agent/generate/image"
    body = {"wallet": wallet, "prompt": prompt}
    payment_signature = encode_payment_signature(deploy_json, wallet)

    print(f"\n[3/3] POST {url}")
    print(f"      Submitting payment proof (deploy hash: {deploy_json.get('deploy', {}).get('hash', 'N/A')})")

    response = requests.post(
        url,
        json=body,
        headers={"PAYMENT-SIGNATURE": payment_signature},
        timeout=120,
    )

    print(f"      HTTP {response.status_code}")

    if response.status_code != 200:
        print(f"\nPayment or generation failed: {response.text}")
        sys.exit(1)

    return response.json()


def load_deploy_file(path: str) -> dict:
    """Load a signed deploy JSON from disk."""
    with open(Path(path), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="TrappistAI Agent x402 client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Get the payment challenge:
    python scripts/agent_x402_client.py --wallet 01... --prompt "cyberpunk cat"

  Submit a signed deploy:
    python scripts/agent_x402_client.py --wallet 01... --prompt "cyberpunk cat" --deploy-file signed_deploy.json
        """,
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"TrappistAI API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--wallet",
        required=True,
        help="Your Casper public key hex (with 01 or 02 prefix)",
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Image generation prompt",
    )
    parser.add_argument(
        "--deploy-file",
        help="Path to the signed deploy JSON file. If omitted, only the challenge is requested.",
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Step 1: request challenge
    # ------------------------------------------------------------------
    challenge = request_challenge(args.api_url, args.wallet, args.prompt)
    details = extract_payment_details(challenge)

    print("\nPayment summary:")
    print(f"  Resource : {details['description']}")
    print(f"  Network  : {details['network']}")
    print(f"  Asset    : {details['asset']}")
    print(f"  Cost     : ${details['cost_usd']} USD")
    print(f"  Amount   : {details['cost_cspr']} CSPR ({details['amount_motes']} motes)")
    print(f"  Pay to   : {details['pay_to']}")
    print(f"  Memo     : {details['memo']}")

    if not args.deploy_file:
        print("\nNext step: sign a native CSPR transfer on mainnet with the above amount")
        print("and recipient, save the signed deploy JSON to a file, then rerun this")
        print("script with --deploy-file <path>.")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Step 2: submit signed deploy
    # ------------------------------------------------------------------
    deploy_json = load_deploy_file(args.deploy_file)
    result = submit_payment(args.api_url, args.wallet, args.prompt, deploy_json)

    print("\nResult:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
