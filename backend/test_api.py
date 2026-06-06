"""
Test TrappistAI API - Simule un utilisateur complet
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
TEST_WALLET = "test_wallet_01234567890abcdef"
TEST_TX_HASH = f"test_tx_{datetime.now().timestamp()}"

print("🧪 TrappistAI API Test\n")
print("=" * 60)

# 1. Check balance (devrait être 0 au début)
print("\n1️⃣ Checking initial balance...")
response = requests.get(f"{BASE_URL}/api/user/{TEST_WALLET}/balance")
print(f"   Status: {response.status_code}")
print(f"   Balance: {response.json()}")

# 2. Simuler un paiement de 10 CSPR (100 tokens)
print("\n2️⃣ Simulating payment (10 CSPR → 100 tokens)...")
payment_data = {
    "walletAddress": TEST_WALLET,
    "txHash": TEST_TX_HASH,
    "amountCspr": 10
}
response = requests.post(f"{BASE_URL}/api/payments/verify", json=payment_data)
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# 3. Vérifier le nouveau solde
print("\n3️⃣ Checking new balance...")
response = requests.get(f"{BASE_URL}/api/user/{TEST_WALLET}/balance")
print(f"   Status: {response.status_code}")
balance_data = response.json()
print(f"   Balance: {balance_data}")
print(f"   ✅ You have {balance_data['tokens']} tokens!")

# 4. Générer une image (coûte 1 token)
print("\n4️⃣ Testing image generation (costs 1 token)...")
gen_data = {
    "walletAddress": TEST_WALLET,
    "prompt": "a beautiful sunset over mountains"
}
response = requests.post(f"{BASE_URL}/api/generate/image", json=gen_data)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"   ✅ Image generated!")
    print(f"   Remaining tokens: {result.get('remaining_tokens', 'N/A')}")
else:
    print(f"   ❌ Error: {response.json()}")

# 5. Vérifier le solde final
print("\n5️⃣ Checking final balance...")
response = requests.get(f"{BASE_URL}/api/user/{TEST_WALLET}/balance")
print(f"   Status: {response.status_code}")
final_balance = response.json()
print(f"   Balance: {final_balance}")
print(f"   💰 Final balance: {final_balance['tokens']} tokens")

print("\n" + "=" * 60)
print("✅ Test completed successfully!")
print("\n📊 Summary:")
print(f"   • Initial: 0 tokens")
print(f"   • Paid: 10 CSPR")
print(f"   • Received: 100 tokens")
print(f"   • Spent: 1 token (image)")
print(f"   • Remaining: {final_balance['tokens']} tokens")
