#!/usr/bin/env python3
"""Debug script to check deploy status on Casper RPC"""

import httpx
import json
import sys

async def check_deploy(deploy_hash: str):
    """Check deploy status on all RPC nodes"""
    
    rpc_nodes = [
        "https://rpc.casper.network/rpc",
        "https://node.mainnet.casper.network/rpc"
    ]
    
    print(f"\n🔍 Checking deploy: {deploy_hash}\n")
    
    for rpc_url in rpc_nodes:
        print(f"\n{'='*60}")
        print(f"📡 RPC Node: {rpc_url}")
        print(f"{'='*60}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "info_get_deploy",
                        "params": {
                            "deploy_hash": deploy_hash
                        }
                    }
                )
                
                print(f"Status Code: {response.status_code}")
                
                if not response.content:
                    print("❌ Empty response")
                    continue
                
                data = response.json()
                
                if "error" in data:
                    print(f"❌ Error: {json.dumps(data['error'], indent=2)}")
                    continue
                
                if "result" in data:
                    result = data["result"]
                    
                    print("\n✅ DEPLOY FOUND!\n")
                    
                    # Check execution results
                    if "execution_results" in result:
                        exec_results = result["execution_results"]
                        print(f"📊 Execution Results ({len(exec_results)} results):")
                        for i, exec_result in enumerate(exec_results):
                            print(f"\n  Result #{i+1}:")
                            if "result" in exec_result:
                                exec_data = exec_result["result"]
                                if "Success" in exec_data:
                                    print("    ✅ SUCCESS")
                                    if "cost" in exec_data["Success"]:
                                        print(f"    💰 Cost: {exec_data['Success']['cost']}")
                                elif "Failure" in exec_data:
                                    print(f"    ❌ FAILURE: {exec_data['Failure']}")
                    else:
                        print("⏳ NO EXECUTION RESULTS YET")
                    
                    # Print full result for debugging
                    print(f"\n📝 Full Result:\n{json.dumps(result, indent=2)}")
                else:
                    print("❌ No result in response")
                    print(f"Response: {json.dumps(data, indent=2)}")
                    
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    import asyncio
    
    if len(sys.argv) < 2:
        print("Usage: python debug_deploy.py <deploy_hash>")
        sys.exit(1)
    
    deploy_hash = sys.argv[1].lower().replace("hash-", "").replace("deploy-", "")
    
    asyncio.run(check_deploy(deploy_hash))
