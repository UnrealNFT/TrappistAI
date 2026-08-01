#!/usr/bin/env python3
"""Debug script to check deploy status on Casper RPC"""

import json
import sys

from casper_rpc import get_rpc_urls, rpc_call_single


async def check_deploy(deploy_hash: str):
    """Check deploy status on all RPC nodes."""

    rpc_nodes = get_rpc_urls("mainnet")

    print(f"\n🔍 Checking deploy: {deploy_hash}\n")

    for rpc_url in rpc_nodes:
        print(f"\n{'='*60}")
        print(f"📡 RPC Node: {rpc_url}")
        print(f"{'='*60}")

        try:
            result = await rpc_call_single(
                rpc_url,
                "info_get_deploy",
                {"deploy_hash": deploy_hash},
            )

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

        except Exception as e:
            print(f"❌ Exception: {str(e)}")


if __name__ == "__main__":
    import asyncio

    if len(sys.argv) < 2:
        print("Usage: python debug_deploy.py <deploy_hash>")
        sys.exit(1)

    deploy_hash = sys.argv[1].lower().replace("hash-", "").replace("deploy-", "")

    asyncio.run(check_deploy(deploy_hash))
