# x402 Payment Integration - TODO

## Goal

Replace current WaveSpeed payment listener with x402 protocol for credit purchases:
- User pays 1000 CSPR → receives 100 credits
- No smart contract needed
- Use Casper x402 Facilitator

## Current Architecture (to replace)

```
User → Frontend → Backend /api/listen-payment → WaveSpeed listener → Payment detected
```

## Target Architecture (x402)

```
User → Frontend → Backend /api/buy-credits (HTTP 402) → User signs with wallet → Facilitator settles on-chain → Callback → Credits added
```

## Implementation Steps

### 1. Research Casper x402 Facilitator API

- [ ] Read Casper x402 documentation
- [ ] Understand Facilitator endpoint structure
- [ ] Get Facilitator URL and authentication method
- [ ] Understand payment flow (request → sign → settle → callback)

### 2. Backend: Create /api/buy-credits endpoint

```python
@app.post("/api/buy-credits")
async def buy_credits(request: BuyCreditRequest):
    """
    Return HTTP 402 Payment Required with x402 payment details
    """
    # Calculate amount: 1000 CSPR = 100 credits
    cspr_amount = request.amount * 10  # 100 credits = 1000 CSPR
    
    # Generate x402 payment request
    payment_request = {
        "amount": cspr_amount,
        "currency": "CSPR",
        "recipient": TREASURY_WALLET,
        "callback_url": f"{API_URL}/api/payment-callback",
        "metadata": {
            "wallet": request.wallet,
            "credits": request.amount
        }
    }
    
    # Return HTTP 402 with payment details
    return JSONResponse(
        status_code=402,
        content={
            "payment_required": True,
            "facilitator_url": "https://facilitator.casper.network/pay",
            "payment_request": payment_request
        }
    )
```

### 3. Backend: Create /api/payment-callback endpoint

```python
@app.post("/api/payment-callback")
async def payment_callback(callback: PaymentCallbackRequest):
    """
    Called by x402 Facilitator after payment settlement
    """
    # Verify signature from Facilitator
    # Extract metadata (wallet, credits)
    # Add credits to user balance
    # Return success
```

### 4. Frontend: x402 Payment Flow

```javascript
// In BuyCredits.jsx
const handlePurchase = async () => {
  try {
    // 1. Request payment details (expect HTTP 402)
    const response = await fetch(`${API_URL}/api/buy-credits`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wallet, amount: selectedBundle.credits })
    })
    
    if (response.status === 402) {
      const data = await response.json()
      
      // 2. Open x402 Facilitator with payment details
      const facilitatorUrl = data.facilitator_url
      const paymentRequest = data.payment_request
      
      // 3. User signs transaction with Casper Wallet
      // (Facilitator handles this)
      
      // 4. Poll /api/balance to check when credits arrive
      // (After Facilitator calls our callback)
    }
  } catch (error) {
    console.error('Payment failed:', error)
  }
}
```

### 5. Remove WaveSpeed Dependencies

- [ ] Remove `backend/bot/wavespeed.py`
- [ ] Remove WaveSpeed imports from `backend/bot/bot.py`
- [ ] Remove `/api/listen-payment` endpoint from `backend/main.py`
- [ ] Remove WaveSpeed environment variables from Render

## Timeline

User said: "je suis pas encore inscrit reste 15 jours on met le x402"
- Deadline: ~15 days
- Priority: HIGH (after current simplification deployed)

## Questions for User

1. Do you have the x402 Facilitator URL?
2. Is there authentication required for Facilitator API?
3. Should we keep WaveSpeed as fallback or full replacement?

## Resources Needed

- [ ] Casper x402 documentation link
- [ ] x402 Facilitator endpoint details
- [ ] Example x402 payment request/response

## Current Status

- ⏳ Pending: Research phase
- ⏳ Pending: Get x402 Facilitator details
- ✅ Architecture design complete (see above)
