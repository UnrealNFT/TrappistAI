#!/bin/bash
# Test Marketplace API Endpoints
# Run after creating marketplace tables

API_URL="https://trappistai-backend.onrender.com"
WALLET="020200927927ec53d1969e76dd69739830cdac7fbb21e9d7b3984dc6c3b3267b92ca"

echo "🧪 Testing Marketplace API..."
echo ""

# 1. Test GET /api/marketplace/listings
echo "1️⃣ GET /api/marketplace/listings"
curl -s "$API_URL/api/marketplace/listings" | jq
echo ""
echo "---"
echo ""

# 2. Test GET /api/rwa/my-tokens
echo "2️⃣ GET /api/rwa/my-tokens/$WALLET"
curl -s "$API_URL/api/rwa/my-tokens/$WALLET" | jq
echo ""
echo "---"
echo ""

echo "✅ Tests complete!"
echo ""
echo "Next steps:"
echo "1. Generate image on Telegram: /image un robot"
echo "2. Click 'Tokenize' button"
echo "3. Check token appears in /my-rwa"
echo "4. List token on marketplace"
echo "5. Test purchase with slider"
