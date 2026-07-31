# External API Configuration

This document contains setup instructions and links for all external APIs used by TrappistAI.

---

## 🔑 Required APIs

### 1. WaveSpeed.ai
**Purpose**: AI generation (images, music, 3D)

- **Website**: https://wavespeed.ai/
- **Docs**: https://docs.wavespeed.ai/
- **Sign up**: https://app.wavespeed.ai/signup
- **Pricing**: Pay-as-you-go

**Models Used**:
- FLUX.1-schnell: $0.003/image
- HeartMuLa: $0.10/song
- MiniMax Music 2.5 HD: $0.15/song
- Hunyuan-3D V3.1: $0.0225/model
- Tripo3D v2.5: $0.30/model

**Environment Variable**:
```bash
WAVESPEED_API_KEY=ws_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 2. CSPR.cloud
**Purpose**: Real-time Casper blockchain event streaming

- **Website**: https://cspr.cloud/
- **Docs**: https://docs.cspr.cloud/
- **Sign up**: https://cspr.cloud/register
- **WebSocket**: wss://streaming.mainnet.cspr.cloud/transfers

**Features**:
- Real-time transfer detection
- Ping/reconnect handling
- Mainnet & testnet support

**Environment Variable**:
```bash
CSPR_CLOUD_KEY=cspr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 3. Groq
**Purpose**: Fast LLM inference for chat

- **Website**: https://groq.com/
- **Console**: https://console.groq.com/
- **Docs**: https://console.groq.com/docs
- **Free tier**: 10,000 requests/day

**Models**:
- llama-3.3-70b-versatile (recommended)
- mixtral-8x7b-32768
- gemma-7b-it

**Environment Variable**:
```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🌐 RPC Nodes (No API Key Needed)

### Casper Mainnet RPC
- Primary: https://node.mainnet.casper.network/rpc
- Fallback: https://rpc.casper.network/rpc

### Casper Testnet RPC
- Primary: https://node.testnet.casper.network/rpc

**Used For**:
- Payment verification (info_get_deploy)
- Sender public key extraction
- Transaction validation

---

## 🔐 Security Best Practices

### Never Expose in Frontend
- ❌ CSPR_CLOUD_KEY
- ❌ WAVESPEED_API_KEY
- ❌ GROQ_API_KEY
- ❌ Private keys

### Safe to Expose
- ✅ RECEIVER_WALLET (public key)
- ✅ RPC URLs
- ✅ WebSocket URLs (with auth header)

### Environment Files
```bash
# Backend .env (secrets)
CSPR_CLOUD_KEY=xxx
WAVESPEED_API_KEY=xxx
GROQ_API_KEY=xxx

# Frontend .env (public only)
VITE_RECEIVER_WALLET=xxx
VITE_API_URL=xxx
```

---

## 💰 Cost Estimates

### Monthly Costs (1000 users/day)

**WaveSpeed.ai**:
- Images (60%): 600 × $0.003 = $1.80/day
- Music HM (14%): 140 × $0.10 = $14.00/day
- Music HD (6%): 60 × $0.15 = $9.00/day
- 3D No Tex (15%): 150 × $0.0225 = $3.38/day
- 3D Tex (5%): 50 × $0.30 = $15.00/day
- **Total**: ~$43/day = **$1,290/month**

**CSPR.cloud**:
- Free tier: 10,000 events/day
- Paid: $29/month for 100k events

**Groq**:
- Free tier: 10,000 requests/day
- Paid: $0.10 per 1M tokens

**Total Infrastructure**: **~$1,350/month**

---

## 📊 Alternative Providers

### Image Generation
- **Replicate**: https://replicate.com/ (FLUX models)
- **HuggingFace Inference**: https://huggingface.co/inference-api
- **Together AI**: https://together.ai/

### Music Generation
- **Suno API**: https://suno.ai/ (unofficial)
- **Mubert API**: https://mubert.com/
- **AIVA API**: https://www.aiva.ai/

### Chat/LLM
- **OpenAI**: https://openai.com/ (GPT-4)
- **Anthropic**: https://anthropic.com/ (Claude)
- **Together AI**: https://together.ai/ (open models)

### Blockchain Streaming
- **Direct RPC polling**: No streaming, higher latency
- **Casper Event Store**: Self-hosted solution

---

## 🧪 Testing Endpoints

### WaveSpeed.ai
```bash
curl -X POST https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-schnell \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "size": "1024x1024", "num_inference_steps": 4}'
```

### CSPR.cloud
```bash
# WebSocket test (use wscat or similar)
wscat -c wss://streaming.mainnet.cspr.cloud/transfers \
  -H "Authorization: YOUR_KEY"
```

### Groq
```bash
curl https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "test"}]}'
```

---

## 🔄 Rate Limits

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| WaveSpeed.ai | N/A | Pay-as-you-go |
| CSPR.cloud | 10k events/day | 100k events/month |
| Groq | 10k requests/day | 1M tokens/month |

**TrappistAI Rate Limits** (backend):
- Balance check: 100/min per IP
- Payments: 50/min per IP
- Generation: 30/min per IP (image), 10/min (music)
- Chat: 50/min per IP

---

## 📝 Support Contacts

- **WaveSpeed.ai**: support@wavespeed.ai
- **CSPR.cloud**: support@cspr.cloud
- **Groq**: support@groq.com
- **Casper Labs**: https://casperlabs.io/contact

---

**Last Updated**: June 6, 2026
