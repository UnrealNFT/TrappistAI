# TrappistAI Agent x402 API

This document describes the **agent-only** HTTP API for AI agents that want to
pay per-generation using the [x402](https://github.com/make-software/casper-x402)
payment protocol on the Casper mainnet.

Human users keep using the website and the token-credit system. Agents use the
endpoints below.

---

## Overview

1. `POST /api/v1/agent/generate/image` (or `music`, `3d`, `video`, `tts`)
   with no payment proof.
2. Server responds `402 Payment Required` with a `PAYMENT-REQUIRED` header.
3. Agent signs and broadcasts a **native CSPR transfer** on mainnet for the
   exact amount shown to the treasury wallet.
4. Agent re-posts the same request with a `PAYMENT-SIGNATURE` header containing
   the signed deploy.
5. Server verifies the payment on-chain, generates the asset, and returns the
   result plus a `PAYMENT-RESPONSE` receipt. Long-running generations (music,
   3d, video) return a `job_id` to poll on `GET /api/jobs/{job_id}` instead
   (see below).

All five resources share the exact same payment flow; only the request body
and the delivery mode differ.

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

| Resource | USD price | CSPR price (live) | Delivery |
|---|---|---|---|
| `image` | $0.03 | converted from live CSPR/USD rate | synchronous (`url`) |
| `tts` | $0.01 | converted from live CSPR/USD rate | synchronous (base64 MP3) |
| `music` | $1.00 | converted from live CSPR/USD rate | job-based (`job_id`) |
| `video` | $1.50 | converted from live CSPR/USD rate | job-based (`job_id`) |
| `3d` | $2.00 | converted from live CSPR/USD rate | job-based (`job_id`) |

The CSPR amount is computed at request time from the live CSPR/USD rate
(CoinGecko primary, with Kraken / CryptoCompare / CoinMarketCap fallbacks). A
minimum floor protects against extreme price spikes:

- image: minimum 1.0 CSPR
- tts: minimum 1.0 CSPR
- music: minimum 10.0 CSPR
- video: minimum 15.0 CSPR
- 3d: minimum 20.0 CSPR

---

## Long-running generations (music / 3d / video)

Music, 3D and video take 2-10 minutes. These endpoints settle the payment,
then return **immediately** with a `job_id` instead of the final URL:

```json
{
  "success": true,
  "job_id": "d3f0a1b2c3...",
  "status": "pending",
  "pollUrl": "/api/jobs/d3f0a1b2c3...",
  "estimatedTime": "2-10 minutes",
  "costUsd": 1.0,
  "costCspr": 95.4,
  "transaction": "abc123..."
}
```

Poll `GET /api/jobs/{job_id}` until `status` is `completed` (the asset URL is
in `result.url`) or `failed`. The `PAYMENT-RESPONSE` receipt header is already
returned with the `job_id` response.

> **Note:** payment is settled before the job starts. If generation fails, the
> job shows `failed` with an `error` message — on-chain payments are not
> automatically refunded.

### `POST /api/v1/agent/generate/music`

```json
{
  "lyrics": "[verse]\nNeon lights on the blockchain...",
  "tags": "electronic, dark, cinematic",
  "quality": "hm",
  "wallet": "02abc..."
}
```

- `lyrics`: song lyrics (empty string = instrumental)
- `quality`: `hm` (HeartMuLa, auto-fallback to MiniMax) or `minimax`

### `POST /api/v1/agent/generate/3d`

```json
{
  "imageUrl": "https://example.com/input.png",
  "withTexture": false,
  "wallet": "02abc..."
}
```

- `withTexture`: `false` = Hunyuan 3D v3.1 (monochrome), `true` = Tripo3D v2.5
  (textured). Result is a GLB model.

### `POST /api/v1/agent/generate/video`

```json
{
  "prompt": "a drone shot over a futuristic city at dusk",
  "imageUrl": null,
  "duration": 5,
  "aspectRatio": "16:9",
  "audio": true,
  "wallet": "02abc..."
}
```

- `imageUrl`: when set, runs image-to-video (animates the image); otherwise
  text-to-video
- `duration`: `5` or `10` seconds
- `aspectRatio`: `16:9`, `9:16` or `1:1`
- `audio`: `false` skips soundtrack generation
- Model: ByteDance Seedance 1.5 Pro (fast variant). Result is an MP4.

---

## Text-to-Speech (`tts`)

`POST /api/v1/agent/tts` follows the exact same x402 flow as
`POST /api/v1/agent/generate/image` (402 challenge → `PAYMENT-SIGNATURE` →
settlement → result), with request body:

```json
{
  "text": "Bonjour le monde",
  "voice": "fr-female",
  "wallet": "02abc..."
}
```

- `text` (required): up to 2000 characters.
- `voice` (optional): `fr-female`, `fr-male`, `en-female`, `en-male`, a raw
  edge-tts voice id (e.g. `fr-FR-DeniseNeural`), or omitted/`auto` for
  automatic FR/EN language detection.
- `wallet` (required): payer public key hex.

On success the response contains the audio inline as base64 MP3:

```json
{
  "success": true,
  "audioBase64": "//uQx...",
  "contentType": "audio/mpeg",
  "voice": "fr-FR-DeniseNeural",
  "costUsd": 0.01,
  "costCspr": 1.05,
  "transaction": "abc123...",
  "message": "Speech synthesized successfully"
}
```

The same voices are listed in the `402` challenge response under `voices`.
Human users can also use the token-credit variant `POST /api/tts`
(1 token per synthesis, body: `walletAddress`, `text`, optional `voice`).

---

## Error Reference

| Status | Meaning |
|---|---|
| `400` | Bad request, invalid proof, or invalid payment |
| `402` | Payment required (expected first call) |
| `429` | Rate limit exceeded (10/minute per wallet) |
| `500` | Server error during generation or settlement |
| `503` | Pricing temporarily unavailable (all price sources down and no cached rate) |

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
