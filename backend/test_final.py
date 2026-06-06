"""
Test final : Génération complète avec l'interface
"""
import requests
import json

BASE_URL = "http://localhost:8000"
TEST_WALLET = "test_wallet_01234567890abcdef"

print("🎨 TRAPPISTAI - TEST FINAL")
print("=" * 70)

# 1. Vérifier le solde
print("\n1️⃣ Solde actuel...")
r = requests.get(f"{BASE_URL}/api/user/{TEST_WALLET}/balance")
balance = r.json()
print(f"   💰 {balance['tokens']} tokens disponibles")

if balance['tokens'] >= 1:
    # 2. Générer une image cyberpunk
    print("\n2️⃣ Génération d'image (FLUX.1-schnell)...")
    print("   📝 Prompt: a futuristic cyberpunk city at night...")
    
    payload = {
        "walletAddress": TEST_WALLET,
        "prompt": "a futuristic cyberpunk city at night with neon lights, flying cars, rain, ultra detailed, 8k"
    }
    
    r = requests.post(f"{BASE_URL}/api/generate/image", json=payload)
    
    if r.status_code == 200:
        result = r.json()
        print(f"   ✅ Génération réussie !")
        print(f"   🖼️  URL: {result.get('url', 'N/A')}")
        
        # 3. Vérifier le nouveau solde
        print("\n3️⃣ Nouveau solde...")
        r = requests.get(f"{BASE_URL}/api/user/{TEST_WALLET}/balance")
        new_balance = r.json()
        print(f"   💰 {new_balance['tokens']} tokens")
        print(f"   📊 Dépensé: {balance['tokens'] - new_balance['tokens']} token")
        
        print("\n" + "=" * 70)
        print("✅ TEST RÉUSSI ! L'application fonctionne parfaitement ! 🎉")
        print("=" * 70)
    else:
        print(f"   ❌ Erreur {r.status_code}: {r.text}")
else:
    print("\n❌ Pas assez de tokens ! Ajoutez-en avec add_test_tokens.py")
