# TrappistAI Agent x402 API

This document describes the **agent-only** HTTP API for AI agents that want to
pay per-generation using the [x402](https://github.com/make-software/casper-x402)
payment protocol on the Casper mainnet.

Human users keep using the website and the token-credit system. Agents use the
endpoints below.

---

## Overview

1. `POST /api/v1/agent/generate/image` with no payment proof.
2. Server responds `402 Payment Required` with a `PAYMENT-REQUIRED` header.
3. Agent signs and broadcasts a **native CSPR transfer** on mainnet for the
   exact amount shown to the treasury wallet.
4. Agent re-posts the same request with a `PAYMENT-SIGNATURE` header containing
   the signed deploy.
5. Server verifies the payment on-chain, generates the image, and returns the
   result URL plus a `PAYMENT-RESPONSE` receipt.

---

## Authentication

There is no API key. Authentication is cryptographic:

- The agent must prove it paid by sending a valid Casper deploy hash.
- The deploy must be a native CSPR transfer on mainnet (`chain_name: casper`).
- The recipient must be the treasury wallet.
- The amount must be greater than or equal to the current price in CSPR.
- Each deploy hash can only be used once.

---

## Endpoint

### `POST /api/v1/agent/generate/image`

Generate one image with FLUX Schnell-1.

#### Request (without payment)

```bash
curl -X POST https://trappist.land/api/v1/agent/generate/image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cyberpunk cat in a neon city, 8k, cinematic",
    "wallet": "01a1b2c3d4e5..."
  }'
```

#### Response: 402 Payment Required

```http
HTTP/1.1 402 Payment Required
PAYMENT-REQUIRED: eyJ4NDAyVmVyc2lvbiI6MSwiZXJyb3IiOiJwYXltZW50X3JlcXVpcmVkIi...==
Access-Control-Expose-Headers: PAYMENT-REQUIRED, PAYMENT-RESPONSE
```

```json
{
  "error": "payment_required",
  "message": "A native CSPR payment is required to generate this image.",
  "resource": "/api/v1/agent/generate/image",
  "costUsd": 0.03,
  "costCspr": 12.0
}
```

The `PAYMENT-REQUIRED` header contains base64-encoded JSON:

```json
{
  "x402Version": 1,
  "error": "payment_required",
  "resource": {
    "url": "/api/v1/agent/generate/image",
    "description": "Generate 1 image with FLUX Schnell-1",
    "mimeType": "application/json"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "casper:casper",
      "asset": "CSPR",
      "amount": "12000000000",
      "payTo": "0202e5a88e2baf0306484eced583f8642902752668b4b91070dc2abd01d6304d2cd8",
      "resource": "/api/v1/agent/generate/image",
      "description": "Generate 1 image with FLUX Schnell-1",
      "extra": {
        "symbol": "CSPR",
        "decimals": "9",
        "usdPrice": "0.03",
        "csprPrice": "12.000000",
        "memo": "TrappistAI agent: Generate 1 image with FLUX Schnell-1"
      }
    }
  ]
}
```

#### Requesting the payment

The agent must create and sign a native CSPR transfer deploy with:

- `chain_name`: `casper`
- `target`: `0202e5a88e2baf0306484eced583f8642902752668b4b91070dc2abd01d6304d2cd8`
- `amount`: exactly the `amount` field from the challenge (in motes)
- `transfer_id`: any unique ID

Then broadcast it to the Casper mainnet.

#### Request (with payment proof)

```bash
curl -X POST https://trappist.land/api/v1/agent/generate/image \
  -H "Content-Type: application/json" \
  -H "PAYMENT-SIGNATURE: $(echo '{"deployJson":{...signed deploy...},"wallet":"01a1b2c3d4e5..."}' | base64 -w 0)" \
  -d '{
    "prompt": "a cyberpunk cat in a neon city, 8k, cinematic",
    "wallet": "01a1b2c3d4e5..."
  }'
```

#### Response: 200 OK

```http
HTTP/1.1 200 OK
PAYMENT-RESPONSE: eyJzdGF0dXMiOiJzZXR0bGVkIiwidHJhbnNhY3Rpb25IYXNoIjoiLi4uIn0=...
```

```json
{
  "success": true,
  "url": "https://storage.example.com/generated/abc123.png",
  "costUsd": 0.03,
  "costCspr": 12.0,
  "transaction": "abc123...",
  "message": "Image generated successfully"
}
```

---

## Pricing

| Resource | USD price | CSPR price (live) |
|---|---|---|
| `image` | $0.03 | converted from CoinGecko CSPR/USD rate |
| `music` | $1.00 | *(reserved for future release)* |
| `3d` | $2.00 | *(reserved for future release)* |

The CSPR amount is computed at request time from the live CoinGecko rate. A
minimum floor protects against extreme price spikes:

- image: minimum 1.0 CSPR
- music: minimum 10.0 CSPR
- 3d: minimum 20.0 CSPR

---

## Error Reference

| Status | Meaning |
|---|---|
| `400` | Bad request, invalid proof, or invalid payment |
| `402` | Payment required (expected first call) |
| `429` | Rate limit exceeded (10/minute per wallet) |
| `500` | Server error during generation or settlement |
| `503` | Pricing temporarily unavailable (CoinGecko down and no cached rate) |

---

## Replay protection

A successful payment deploy hash is recorded in the `agent_payments` table.
Any attempt to reuse the same deploy hash returns:

```json
{ "detail": "Deploy hash already used" }
```

---

## Network

This API only accepts payments on **Casper mainnet** (`chain_name: casper`).
