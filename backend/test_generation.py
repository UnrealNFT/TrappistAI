"""
Test simple : Génération d'image avec un utilisateur existant
"""
import requests

BASE_URL = "http://localhost:8000"
TEST_WALLET = "test_wallet_01234567890abcdef"

print("🧪 TrappistAI Generation Test\n")
print("=" * 60)

# 1. Check balance
print("\n1️⃣ Checking balance...")
response = requests.get(f"{BASE_URL}/api/user/{TEST_WALLET}/balance")
balance = response.json()
print(f"   💰 Balance: {balance['tokens']} tokens")

# 2. Generate image (costs 1 token)
if balance['tokens'] > 0:
    print("\n2️⃣ Generating image...")
    gen_data = {
        "walletAddress": TEST_WALLET,
        "prompt": "a beautiful sunset over mountains"
    }
    response = requests.post(f"{BASE_URL}/api/generate/image", json=gen_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Image generated!")
        print(f"   Remaining: {result.get('remaining_tokens', 'N/A')} tokens")
        if 'url' in result:
            print(f"   URL: {result['url']}")
        if 'error' in result:
            print(f"   Note: {result['error']}")
    else:
        print(f"   ❌ Error: {response.json()}")

    # 3. Check new balance
    print("\n3️⃣ Final balance...")
    response = requests.get(f"{BASE_URL}/api/user/{TEST_WALLET}/balance")
    final = response.json()
    print(f"   💰 Balance: {final['tokens']} tokens")
    print(f"   📊 Spent: {balance['tokens'] - final['tokens']} token(s)")
else:
    print("\n❌ No tokens available! Run add_test_tokens.py first")

print("\n" + "=" * 60)
