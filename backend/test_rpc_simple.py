import requests
import json

deploy_hash = "a18ad48a38dead27a71ad3c6cd6e2a2295f500a8d77c50acb83e238bc2aa9067"

# Test multiple RPC endpoints
rpc_urls = [
    "https://rpc.casper.network/rpc",
    "https://node.mainnet.casper.network/rpc",
    "https://casper-node.tor.us",
    "https://rpc.mainnet.casperlabs.io/rpc"
]

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "info_get_deploy",
    "params": {
        "deploy_hash": deploy_hash
    }
}

print(f"📦 Deploy: {deploy_hash}\n")

for rpc_url in rpc_urls:
    print(f"\n{'='*60}")
    print(f"🔍 Testing RPC: {rpc_url}")
    print(f"{'='*60}")

for rpc_url in rpc_urls:
    print(f"\n{'='*60}")
    print(f"🔍 Testing RPC: {rpc_url}")
    print(f"{'='*60}")

    try:
        response = requests.post(rpc_url, json=payload, timeout=30, verify=False)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            continue
        
        data = response.json()
        
        if "error" in data:
            print(f"❌ RPC Error: {data['error']}")
            continue
        
        if "result" in data:
            result = data["result"]
            print("\n🔍 Checking formats:")
            print(f"  - has execution_results: {bool(result.get('execution_results'))}")
            print(f"  - has execution_info: {bool(result.get('execution_info'))}")
            
            if result.get("execution_results"):
                print(f"\n✅✅✅ execution_results FOUND!")
                print(json.dumps(result["execution_results"], indent=2))
            
            if result.get("execution_info"):
                print(f"\n✅✅✅ execution_info FOUND!")
                print(json.dumps(result["execution_info"], indent=2))
            
            if not result.get("execution_results") and not result.get("execution_info"):
                print("\n⚠️ Deploy found but NO execution data yet")
                
    except Exception as e:
        print(f"❌ Error: {e}")
