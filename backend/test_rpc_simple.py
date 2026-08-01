import asyncio
import json

from casper_rpc import get_rpc_urls, rpc_call_single


deploy_hash = "a18ad48a38dead27a71ad3c6cd6e2a2295f500a8d77c50acb83e238bc2aa9067"


async def test_endpoints():
    rpc_urls = get_rpc_urls("mainnet")

    print(f"📦 Deploy: {deploy_hash}\n")

    for rpc_url in rpc_urls:
        print(f"\n{'='*60}")
        print(f"🔍 Testing RPC: {rpc_url}")
        print(f"{'='*60}")

        try:
            result = await rpc_call_single(
                rpc_url,
                "info_get_deploy",
                {"deploy_hash": deploy_hash},
            )

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


if __name__ == "__main__":
    asyncio.run(test_endpoints())
