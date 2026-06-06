"""
CSPR Payment Listener - WebSocket connection to CSPR.cloud
Monitors transfers to receiver wallet and credits tokens automatically
"""
import asyncio
import json
import os
from datetime import datetime
import websockets
import httpx
from dotenv import load_dotenv

from db import process_payment

load_dotenv()

# Configuration
RECEIVER_WALLET = os.getenv("RECEIVER_WALLET", "")
RECEIVER_ACCOUNT_HASH = os.getenv("RECEIVER_ACCOUNT_HASH", "")
CSPR_CLOUD_KEY = os.getenv("CSPR_CLOUD_KEY", "")
CSPR_CLOUD_WS = "wss://streaming.mainnet.cspr.cloud/transfers"
RPC_URL = "https://node.mainnet.casper.network/rpc"

# Package unique
PACKAGES = {
    10: {"tokens": 100, "name": "Starter"},
}


def normalize_hash(hash_str):
    """Remove hash prefixes"""
    if not hash_str:
        return ""
    prefixes = ["hash-", "account-hash-", "deploy-", "0x"]
    result = hash_str.lower()
    for prefix in prefixes:
        result = result.replace(prefix, "")
    return result


async def fetch_deploy_sender(deploy_hash: str) -> str:
    """Fetch sender public key from RPC"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "info_get_deploy",
                    "params": {"deploy_hash": deploy_hash},
                    "id": 1
                }
            )
            data = response.json()
            return data["result"]["deploy"]["header"]["account"]
    except Exception as e:
        print(f"[CSPR] Error fetching deploy: {e}")
        return None


async def process_transfer(transfer: dict):
    """Process confirmed payment transfer"""
    try:
        deploy_hash = normalize_hash(transfer.get("deploy_hash", ""))
        amount_motes = int(transfer.get("amount", 0))
        amount_cspr = amount_motes / 1e9
        
        print(f"[CSPR] Processing: {amount_cspr} CSPR - Deploy: {deploy_hash[:20]}...")
        
        # Fetch sender
        sender_pubkey = await fetch_deploy_sender(deploy_hash)
        if not sender_pubkey:
            print(f"[CSPR] Could not extract sender public key")
            return
        
        # Match package
        pkg = PACKAGES.get(round(amount_cspr))
        if not pkg:
            print(f"[CSPR] Invalid amount: {amount_cspr} CSPR - No matching package")
            return
        
        # Save payment and credit tokens
        success = await process_payment(
            wallet_address=sender_pubkey,
            tx_hash=deploy_hash,
            amount_cspr=amount_cspr,
            tokens=pkg["tokens"],
            package_name=pkg["name"]
        )
        
        if success:
            print(f"[CSPR] ✅ {pkg['name']} package ({pkg['tokens']} tokens) credited to {sender_pubkey[:20]}...")
        else:
            print(f"[CSPR] ⚠️ Payment already processed or error occurred")
        
    except Exception as e:
        print(f"[CSPR] Error processing transfer: {e}")


async def listen_payments():
    """WebSocket listener for CSPR payments"""
    if not CSPR_CLOUD_KEY:
        print("[CSPR] ❌ CSPR_CLOUD_KEY not set!")
        return
    
    if not RECEIVER_WALLET or not RECEIVER_ACCOUNT_HASH:
        print("[CSPR] ❌ RECEIVER_WALLET or RECEIVER_ACCOUNT_HASH not set!")
        return
    
    print("[CSPR] 🚀 Starting payment listener...")
    print(f"[CSPR] Wallet: {RECEIVER_WALLET}")
    print(f"[CSPR] Account Hash: {RECEIVER_ACCOUNT_HASH[:20]}...")
    
    headers = {"Authorization": CSPR_CLOUD_KEY}
    last_ping = datetime.now()
    
    while True:
        try:
            async with websockets.connect(CSPR_CLOUD_WS, extra_headers=headers) as ws:
                print("[CSPR] ✅ Connected to CSPR.cloud")
                
                async for message in ws:
                    # Handle ping
                    if message == "Ping":
                        last_ping = datetime.now()
                        print("[CSPR] 💓 Ping received")
                        continue
                    
                    # Parse transfer
                    try:
                        data = json.loads(message)
                        
                        if not data.get("data") or data.get("action") != "created":
                            continue
                        
                        transfer = data["data"]
                        to_hash = normalize_hash(transfer.get("to_account_hash", ""))
                        expected_hash = normalize_hash(RECEIVER_ACCOUNT_HASH)
                        
                        print(f"[CSPR] Transfer detected: to={to_hash[:20]}...")
                        print(f"[CSPR] Expected: {expected_hash[:20]}...")
                        
                        # Match receiver
                        if to_hash == expected_hash:
                            await process_transfer(transfer)
                        else:
                            print(f"[CSPR] Transfer not for us, ignoring")
                    
                    except json.JSONDecodeError:
                        print(f"[CSPR] Failed to parse message")
                        continue
        
        except Exception as e:
            print(f"[CSPR] WebSocket error: {e}")
            print("[CSPR] Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    """Test listener standalone"""
    asyncio.run(listen_payments())
