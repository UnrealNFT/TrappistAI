"""
x402 CEP-18 Settlement Module
Handles on-chain transfer_with_authorization calls using python_condor SDK
"""
import os
import sys
from typing import Dict, Any, Optional

# Add python_condor SDK to path
CONDOR_SDK_PATH = r"C:\Users\Djaf\scai\Demo-Beatcoin-main\python_sdk_condor-main\packages\src"
if CONDOR_SDK_PATH not in sys.path:
    sys.path.insert(0, CONDOR_SDK_PATH)

from python_condor import ContractCallBuilder, PutTransaction, KeyAlgorithm
from python_condor import CLKey, CLPublicKey, CLU256, CLU64, CLByteArray

# Configuration
FACILITATOR_KEY_PATH = os.getenv("FACILITATOR_KEY_PATH", "")  # Path to facilitator private key
CEP18_PACKAGE_HASH = "3f8d7013ce13a8e4dc9ef58bfb05e8a78e31bec0f8c92b3e7afedc7e35c3c381"  # WCSPR contract
CASPER_RPC_URL = os.getenv("CASPER_RPC_URL", "https://node.mainnet.casper.network/rpc")
CHAIN_NAME = "casper"  # mainnet
GAS_PAYMENT = 5_000_000_000  # 5 CSPR for gas

def parse_account_hash(account_hash_hex: str) -> bytes:
    """
    Parse account hash from hex string (with or without '00' prefix)
    Example: '00abc123...' or 'abc123...'
    """
    clean_hex = account_hash_hex.replace("account-hash-", "").strip()
    if clean_hex.startswith("00"):
        clean_hex = clean_hex[2:]
    return bytes.fromhex(clean_hex)

def parse_nonce(nonce_hex: str) -> bytes:
    """
    Parse nonce from hex string (with or without '0x' prefix)
    Example: '0x123abc...' or '123abc...'
    """
    clean_hex = nonce_hex.replace("0x", "").strip()
    return bytes.fromhex(clean_hex)

def parse_signature(signature_hex: str) -> bytes:
    """
    Parse signature from hex string
    """
    clean_hex = signature_hex.replace("0x", "").strip()
    return bytes.fromhex(clean_hex)

def parse_public_key_bytes(public_key_hex: str) -> bytes:
    """
    Parse public key from hex string (must include 01 or 02 prefix for Ed25519/Secp256k1)
    """
    clean_hex = public_key_hex.strip()
    return bytes.fromhex(clean_hex)

async def settle_transfer_with_authorization(
    authorization: Dict[str, Any],
    public_key: str,
    signature: str,
    cep18_package_hash: str = CEP18_PACKAGE_HASH,
    facilitator_public_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute CEP-18 transfer_with_authorization on-chain
    
    Args:
        authorization: Dict with from, to, value, validAfter, validBefore, nonce
        public_key: User's public key hex (with 01/02 prefix)
        signature: EIP-712 signature hex
        cep18_package_hash: CEP-18 contract package hash
        facilitator_public_key: Facilitator's public key (defaults to env)
    
    Returns:
        Dict with deploy_hash, status, message
    
    Raises:
        Exception if settlement fails
    """
    try:
        # Parse authorization fields
        value = int(authorization["value"])  # Already in motes
        valid_after = int(authorization["validAfter"])
        valid_before = int(authorization["validBefore"])
        nonce_bytes = parse_nonce(authorization["nonce"])
        public_key_bytes = parse_public_key_bytes(public_key)
        signature_bytes = parse_signature(signature)
        
        print(f"🔧 Building CEP-18 transfer_with_authorization deploy...")
        print(f"   From: {authorization['from'][:20]}...")
        print(f"   To: {authorization['to'][:20]}...")
        print(f"   Value: {value} motes ({value/1e9:.2f} CSPR)")
        print(f"   Nonce: {authorization['nonce'][:20]}...")
        
        # Get facilitator key
        if not FACILITATOR_KEY_PATH or not os.path.exists(FACILITATOR_KEY_PATH):
            raise ValueError(
                f"Facilitator key not found at: {FACILITATOR_KEY_PATH}. "
                f"Set FACILITATOR_KEY_PATH env variable."
            )
        
        # Determine facilitator public key
        if not facilitator_public_key:
            # TODO: Extract from key file (for now, must be provided)
            raise ValueError("facilitator_public_key must be provided")
        
        # Build transaction using python_condor SDK
        builder = ContractCallBuilder([
            (FACILITATOR_KEY_PATH, KeyAlgorithm.ED25519)
        ])
        
        # Create CLKey objects for from/to (must have 'account-hash-' prefix)
        # If authorization["from"] already has prefix, use as-is
        # Otherwise, add prefix
        from_str = authorization["from"]
        if not from_str.startswith("account-hash-"):
            # Remove '00' prefix if present and add 'account-hash-'
            clean_from = from_str[2:] if from_str.startswith("00") else from_str
            from_str = f"account-hash-{clean_from}"
        
        to_str = authorization["to"]
        if not to_str.startswith("account-hash-"):
            clean_to = to_str[2:] if to_str.startswith("00") else to_str
            to_str = f"account-hash-{clean_to}"
        
        from_key = CLKey(from_str)
        to_key = CLKey(to_str)
        
        # Build runtime args matching CEP-18 transfer_with_authorization entrypoint
        transaction_json = builder.runtime_args({
            "from": from_key,
            "to": to_key,
            "amount": CLU256(value),
            "valid_after": CLU64(valid_after),
            "valid_before": CLU64(valid_before),
            "nonce": CLByteArray(nonce_bytes),
            "public_key": CLPublicKey(public_key_bytes),
            "signature": CLByteArray(signature_bytes)
        }).chainname(CHAIN_NAME) \
          .by_package_hash(cep18_package_hash) \
          .entry_point("transfer_with_authorization") \
          .from_publickey(facilitator_public_key) \
          .payment(GAS_PAYMENT) \
          .build()
        
        print(f"📡 Submitting transaction to Casper RPC: {CASPER_RPC_URL}")
        
        # Submit transaction
        transaction_result = PutTransaction(CASPER_RPC_URL, transaction_json).run()
        
        print(f"✅ Transaction submitted!")
        print(f"   Result: {transaction_result}")
        
        # Extract transaction hash
        if isinstance(transaction_result, dict) and "result" in transaction_result:
            tx_hash = transaction_result["result"].get("transaction_hash")
            if tx_hash:
                return {
                    "success": True,
                    "deploy_hash": tx_hash,
                    "status": "submitted",
                    "message": f"Transfer submitted on-chain: {tx_hash}"
                }
        
        # Fallback if format different
        return {
            "success": True,
            "deploy_hash": str(transaction_result),
            "status": "submitted",
            "message": "Transfer submitted on-chain"
        }
        
    except Exception as e:
        print(f"❌ Settlement error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "deploy_hash": None,
            "status": "failed",
            "message": f"Settlement failed: {str(e)}"
        }

# Test function
async def test_settlement():
    """Test settlement with dummy data"""
    auth = {
        "from": "00abc123def456",
        "to": "00123abc456def",
        "value": "10000000000",  # 10 CSPR in motes
        "validAfter": "1718812800",
        "validBefore": "1718816400",
        "nonce": "0x1234567890abcdef"
    }
    
    # Dummy keys (replace with real for testing)
    public_key = "01abc123"
    signature = "0xdef456"
    facilitator_pk = "017e037b8b5621b9803cad20c2d85aca9b5028c5ee5238923bb4a8fc5131d539f5"
    
    result = await settle_transfer_with_authorization(
        auth, public_key, signature, 
        facilitator_public_key=facilitator_pk
    )
    print(f"Test result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_settlement())
