"""Test direct de l'API WaveSpeed pour diagnostiquer le problème 401"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WAVESPEED_API_KEY")
print(f"🔑 Clé API: {API_KEY[:20]}...{API_KEY[-10:]}")
print(f"📏 Longueur: {len(API_KEY)} caractères")
print()

# Test 1: Submit task
print("=" * 60)
print("TEST 1: Soumettre une tâche de génération d'image")
print("=" * 60)

url = "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-schnell"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
payload = {
    "prompt": "A beautiful sunset over mountains",
    "size": "1024x1024",
    "num_inference_steps": 4
}

print(f"📡 URL: {url}")
print(f"📤 Headers: Authorization: Bearer {API_KEY[:15]}...")
print(f"📦 Payload: {payload}")
print()

try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"📊 Status Code: {response.status_code}")
    print(f"📄 Response Headers: {dict(response.headers)}")
    print(f"📝 Response Body:")
    print(response.text)
    print()
    
    if response.status_code == 401:
        print("❌ ERREUR 401: Unauthorized")
        print("   Causes possibles:")
        print("   1. La clé API n'est pas valide")
        print("   2. Le compte n'est pas activé")
        print("   3. La clé a été créée avant le top-up")
        print("   4. La clé n'a pas les permissions pour flux-schnell")
        print()
    elif response.status_code == 200:
        print("✅ SUCCESS! La clé fonctionne!")
        data = response.json()
        task_id = data.get("data", {}).get("id")
        print(f"   Task ID: {task_id}")
    else:
        print(f"⚠️ Code inattendu: {response.status_code}")
        
except Exception as e:
    print(f"💥 Exception: {e}")
    import traceback
    traceback.print_exc()
