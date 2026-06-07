"""
TrappistAI Backend - Multi-modal AI Generation Platform
Supports: Image (FLUX), Music (HeartMuLa/MiniMax), 3D (Hunyuan/Tripo), Chat (Groq)
Payment: CSPR (Casper blockchain)
"""
import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from cspr_listener import listen_payments
from db import get_db_session, get_user_balance, consume_user_tokens, get_payment_history
import wavespeed

load_dotenv()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start CSPR listener on startup"""
    # Initialize database
    try:
        print("🔧 Initializing database...")
        import init_db
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database init warning: {e}")
    
    listener_task = asyncio.create_task(listen_payments())
    print("🚀 CSPR payment listener started")
    
    yield
    
    listener_task.cancel()
    print("🛑 CSPR listener stopped")

# FastAPI app
app = FastAPI(
    title="TrappistAI API",
    description="Multi-modal AI generation with CSPR payments",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")]
print(f"🌐 CORS allowed origins: {ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MODELS
# ============================================

class GenerateImageRequest(BaseModel):
    walletAddress: str
    prompt: str

class GenerateMusicRequest(BaseModel):
    walletAddress: str
    lyrics: str
    tags: str = "electronic, dark, cinematic"
    quality: str = "hm"  # hm or minimax

class Generate3DRequest(BaseModel):
    walletAddress: str
    imageUrl: str
    withTexture: bool = False

class ChatRequest(BaseModel):
    walletAddress: str
    message: str

class VerifyPaymentRequest(BaseModel):
    walletAddress: str
    txHash: str

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/")
async def root():
    return {
        "name": "TrappistAI API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# ============================================
# USER BALANCE
# ============================================

@app.get("/api/user/{wallet_address}/balance")
@limiter.limit("100/minute")
async def get_balance(request: Request, wallet_address: str):
    """Get user's token balance"""
    try:
        balance = await get_user_balance(wallet_address)
        return {"success": True, "tokens": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{wallet_address}/payments")
@limiter.limit("50/minute")
async def get_payments(request: Request, wallet_address: str):
    """Get user's payment history"""
    try:
        payments = await get_payment_history(wallet_address)
        return {"success": True, "payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PAYMENT VERIFICATION
# ============================================

class SendDeployRequest(BaseModel):
    deployJson: dict

class VerifyPaymentRequest(BaseModel):
    wallet: str
    deployHash: str
    amount: float
    tokens: int

@app.post("/api/casper/send-deploy")
@limiter.limit("10/minute")
async def send_deploy(request: Request, data: SendDeployRequest):
    """Send signed deploy to Casper RPC (Step 1 of payment flow - like ScreenerLand)"""
    try:
        import httpx
        
        if not data.deployJson:
            raise HTTPException(status_code=400, detail="Missing deployJson")
        
        # Extract the actual deploy (frontend sends { deploy: {...} })
        actual_deploy = data.deployJson.get("deploy", data.deployJson)
        
        print("📤 Submitting signed deploy to blockchain...")
        print(f"Deploy hash: {actual_deploy.get('hash', 'N/A')}")
        print(f"Deploy chain_name: {actual_deploy.get('header', {}).get('chain_name', 'N/A')}")
        print(f"Deploy approvals count: {len(actual_deploy.get('approvals', []))}")
        
        # RPC nodes (mainnet) - node.mainnet works, rpc.casper returns 404!
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc",
            "https://casper-node.tor.us"
        ]
        
        result = None
        last_error = None
        
        for rpc_url in rpc_nodes:
            try:
                print(f"🔄 Trying MAINNET RPC node: {rpc_url}")
                
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    response = await client.post(
                        rpc_url,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "account_put_deploy",
                            "params": {
                                "deploy": actual_deploy
                            }
                        }
                    )
                    
                    # Check response validity
                    if response.status_code != 200:
                        raise Exception(f"RPC returned status {response.status_code}")
                    
                    if not response.content:
                        raise Exception("RPC returned empty response")
                    
                    try:
                        rpc_data = response.json()
                    except Exception as json_err:
                        raise Exception(f"Invalid JSON: {str(json_err)}")
                    
                    print(f"📥 RPC Response from {rpc_url}: {rpc_data}")
                    
                    if "error" in rpc_data:
                        raise Exception(rpc_data["error"].get("message", str(rpc_data["error"])))
                    
                    result = rpc_data["result"]
                    print(f"✅ Deploy sent via {rpc_url}: {result.get('deploy_hash')}")
                    break  # Success!
                    
            except Exception as node_error:
                print(f"⚠️ Failed {rpc_url}: {str(node_error)}")
                last_error = node_error
        
        if not result:
            raise Exception(f"All MAINNET RPC nodes failed: {str(last_error)}")
        
        return {
            "success": True,
            "deployHash": result["deploy_hash"]
        }
        
    except Exception as e:
        print(f"❌ Error sending deploy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payment/verify")
@limiter.limit("10/minute")
async def verify_payment(request: Request, data: VerifyPaymentRequest):
    """Verify payment on blockchain and credit tokens (Step 2 - like ScreenerLand)"""
    try:
        import httpx
        
        if not data.wallet or not data.deployHash:
            raise HTTPException(status_code=400, detail="Missing wallet or deployHash")
        
        print(f"🔐 Verifying payment: wallet={data.wallet[:20]}..., deploy={data.deployHash[:20]}...")
        
        # Clean hashes
        clean_deploy = data.deployHash.lower().replace("hash-", "").replace("deploy-", "")
        
        # RPC nodes - node.mainnet works, rpc.casper returns 404!
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc",
            "https://casper-node.tor.us"
        ]
        
        # Wait for deploy to be executed (max 30 attempts * 3s = 90s - same as ScreenerLand)
        deploy_info = None
        max_attempts = 30
        delay_ms = 3000
        
        for attempt in range(1, max_attempts + 1):
            print(f"🔍 Attempt {attempt}/{max_attempts} to fetch deploy info...")
            
            for rpc_url in rpc_nodes:
                try:
                    print(f"📡 Trying RPC node: {rpc_url}")
                    
                    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                        response = await client.post(
                            rpc_url,
                            json={
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "info_get_deploy",
                                "params": {
                                    "deploy_hash": clean_deploy
                                }
                            }
                        )
                        
                        # Check response validity
                        if response.status_code != 200:
                            print(f"⚠️ RPC returned status {response.status_code}")
                            continue
                        
                        if not response.content:
                            print(f"⚠️ RPC returned empty response")
                            continue
                        
                        try:
                            rpc_data = response.json()
                        except Exception as json_err:
                            print(f"⚠️ Invalid JSON from {rpc_url}: {str(json_err)}")
                            continue
                        
                        if "error" in rpc_data:
                            print(f"⏳ RPC returned error: {rpc_data['error'].get('message', 'Unknown')}")
                            continue
                        
                        # Check BOTH formats like ScreenerLand (execution_results AND execution_info)
                        result = rpc_data.get("result")
                        if result and (result.get("execution_results") or result.get("execution_info")):
                            deploy_info = result
                            print(f"✅ Deploy found with execution result from {rpc_url}")
                            break
                        elif result:
                            print("⏳ Deploy found but not executed yet, waiting...")
                        else:
                            print("⏳ No result yet, waiting...")
                    
                except Exception as fetch_error:
                    print(f"⚠️ Fetch error on {rpc_url}: {str(fetch_error)}")
            
            # Check both formats like ScreenerLand
            if deploy_info and (deploy_info.get("execution_results") or deploy_info.get("execution_info")):
                break
            
            if attempt < max_attempts:
                await asyncio.sleep(delay_ms / 1000)
        
        # Check both old and new API formats (like ScreenerLand)
        has_execution = deploy_info and (deploy_info.get("execution_results") or deploy_info.get("execution_info"))
        
        if not has_execution:
            print("❌ Deploy not executed after 90 seconds")
            return {
                "error": "Payment not confirmed yet. Mainnet confirmation is taking longer than expected - wait 1 minute and refresh the page to check again.",
                "pending": True,
                "deployHash": clean_deploy,
                "message": "Your payment was sent successfully but blockchain confirmation is taking longer than expected. Please wait and refresh the page."
            }
        
        # Extract execution result from either format (like ScreenerLand)
        error_message = None
        
        if deploy_info.get("execution_info"):
            # New format (testnet uses this)
            execution_result = deploy_info["execution_info"].get("execution_result", {})
            if execution_result.get("Version2"):
                error_message = execution_result["Version2"].get("error_message")
        elif deploy_info.get("execution_results"):
            # Old format
            execution_results = deploy_info["execution_results"]
            if execution_results and len(execution_results) > 0:
                result = execution_results[0].get("result", {})
                if "Failure" in result:
                    error_message = result["Failure"].get("error_message", "Unknown error")
        
        # Check if deploy failed
        if error_message:
            print(f"❌ Deploy FAILED on blockchain: {error_message}")
            raise HTTPException(
                status_code=400,
                detail=f"Payment failed on blockchain: {error_message}"
            )
        
        print("✅ Deploy succeeded on blockchain!")
        
        # Credit tokens
        from db import process_payment_manual
        
        package_name = "Custom"
        if data.amount == 10 and data.tokens == 100:
            package_name = "Starter"
        
        await process_payment_manual(
            data.wallet, 
            clean_deploy, 
            data.amount, 
            data.tokens, 
            package_name
        )
        
        print(f"💰 Credited {data.tokens} tokens to {data.wallet}")
        
        return {
            "success": True,
            "deployHash": clean_deploy,
            "tokens": data.tokens,
            "message": f"Payment successful! {data.tokens} tokens credited."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Payment processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/verify")
@limiter.limit("10/minute")
async def verify_payment(request: Request, data: VerifyPaymentRequest):
    """Manual payment verification (fallback if WebSocket missed it)"""
    try:
        import httpx
        
        # Fetch deploy from RPC
        rpc_url = "https://node.mainnet.casper.network/rpc"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "info_get_deploy",
                    "params": {"deploy_hash": data.txHash},
                    "id": 1
                }
            )
            rpc_data = response.json()
        
        if "error" in rpc_data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        deploy = rpc_data["result"]["deploy"]
        sender = deploy["header"]["account"]
        
        # Extract amount
        transfer_args = deploy["session"]["Transfer"]["args"]
        amount_arg = next((a for a in transfer_args if a[0] == "amount"), None)
        if not amount_arg:
            raise HTTPException(status_code=400, detail="Invalid transfer")
        
        amount_motes = int(amount_arg[1]["parsed"])
        amount_cspr = amount_motes / 1e9
        
        # Match package
        PACKAGES = {
            10: {"tokens": 100, "name": "Starter"},
        }
        
        pkg = PACKAGES.get(round(amount_cspr))
        if not pkg:
            raise HTTPException(status_code=400, detail=f"Invalid amount: {amount_cspr} CSPR")
        
        # Save payment and credit tokens (via db.py)
        from db import process_payment_manual
        await process_payment_manual(sender, data.txHash, amount_cspr, pkg["tokens"], pkg["name"])
        
        return {
            "success": True,
            "tokens": pkg["tokens"],
            "package": pkg["name"],
            "sender": sender
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payment/recover")
@limiter.limit("5/minute")
async def recover_payment(request: Request, deployHash: str, wallet: str, amount: float, tokens: int):
    """Recover lost payment by verifying on blockchain (for payments that timed out)"""
    try:
        import httpx
        from db import process_payment_manual
        
        print(f"🔍 Recovering payment: deploy={deployHash[:20]}..., wallet={wallet[:20]}...")
        
        # Clean hash
        clean_deploy = deployHash.lower().replace("hash-", "").replace("deploy-", "")
        
        # RPC nodes - node.mainnet works, rpc.casper returns 404!
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc",
            "https://casper-node.tor.us"
        ]
        
        # Fetch deploy info from blockchain
        deploy_info = None
        for rpc_url in rpc_nodes:
            try:
                print(f"📡 Checking blockchain via {rpc_url}")
                
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    response = await client.post(
                        rpc_url,
                        json={
                            "jsonrpc": "2.0",
                            "method": "info_get_deploy",
                            "params": {"deploy_hash": clean_deploy},
                            "id": 1
                        }
                    )
                    
                    if response.status_code == 200 and response.content:
                        try:
                            result = response.json()
                            if result.get("result") and result["result"].get("deploy"):
                                deploy_info = result["result"]["deploy"]
                                print("✅ Deploy found on blockchain!")
                                break
                        except Exception as json_err:
                            print(f"⚠️ Invalid JSON from {rpc_url}: {str(json_err)}")
                            continue
                            
            except Exception as e:
                print(f"⚠️ RPC node {rpc_url} failed: {e}")
                continue
        
        if not deploy_info:
            raise HTTPException(status_code=404, detail="Deploy not found on blockchain. Wait a few minutes and try again.")
        
        # Check execution results
        execution_results = deploy_info.get("execution_results", [])
        if not execution_results:
            return {
                "error": "Deploy not yet executed on blockchain. Wait 1-2 minutes and try again.",
                "pending": True
            }
        
        # Check if successful
        result = execution_results[0].get("result", {})
        if "Failure" in result:
            error_msg = result["Failure"].get("error_message", "Unknown error")
            raise HTTPException(status_code=400, detail=f"Payment failed on blockchain: {error_msg}")
        
        print("✅ Deploy SUCCESS on blockchain!")
        
        # Determine package name
        package_name = "Custom"
        if amount == 10 and tokens == 100:
            package_name = "Starter"
        
        # Credit tokens (will check for duplicates)
        try:
            await process_payment_manual(wallet, clean_deploy, amount, tokens, package_name)
            print(f"💰 Credited {tokens} tokens to {wallet}")
            
            return {
                "success": True,
                "deployHash": clean_deploy,
                "tokens": tokens,
                "message": f"Payment recovered! {tokens} tokens credited."
            }
            
        except Exception as e:
            if "already processed" in str(e).lower():
                return {
                    "success": False,
                    "message": "Payment already credited",
                    "deployHash": clean_deploy
                }
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Recovery error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payment/recover-batch")
@limiter.limit("3/minute")
async def recover_batch_payments(
    request: Request, 
    wallet: str, 
    deployHashes: list[str],
    tokensPerDeploy: int = 100,
    csrpPerDeploy: float = 10.0
):
    """Recover multiple payments at once - for when multiple payments timed out"""
    try:
        import httpx
        from db import process_payment_manual
        
        print(f"🔍 Batch recovery for wallet: {wallet[:20]}...")
        print(f"📦 {len(deployHashes)} deploys to check")
        
        # RPC nodes - node.mainnet works, rpc.casper returns 404!
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc",
            "https://casper-node.tor.us"
        ]
        
        results = {
            "credited": [],
            "already_credited": [],
            "failed": [],
            "pending": []
        }
        
        for deployHash in deployHashes:
            try:
                clean_deploy = deployHash.lower().replace("hash-", "").replace("deploy-", "")
                print(f"\n🔍 Checking deploy: {clean_deploy[:20]}...")
                
                # Fetch from blockchain
                deploy_info = None
                for rpc_url in rpc_nodes:
                    try:
                        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                            response = await client.post(
                                rpc_url,
                                json={
                                    "jsonrpc": "2.0",
                                    "method": "info_get_deploy",
                                    "params": {"deploy_hash": clean_deploy},
                                    "id": 1
                                }
                            )
                            
                            if response.status_code == 200 and response.content:
                                try:
                                    result = response.json()
                                    if result.get("result") and result["result"].get("deploy"):
                                        deploy_info = result["result"]["deploy"]
                                        break
                                except:
                                    continue
                    except:
                        continue
                
                if not deploy_info:
                    results["failed"].append({
                        "deployHash": clean_deploy,
                        "reason": "Not found on blockchain"
                    })
                    continue
                
                # Check execution
                execution_results = deploy_info.get("execution_results", [])
                if not execution_results:
                    results["pending"].append({
                        "deployHash": clean_deploy,
                        "reason": "Not yet executed"
                    })
                    continue
                
                # Check if success
                result_data = execution_results[0].get("result", {})
                if "Failure" in result_data:
                    results["failed"].append({
                        "deployHash": clean_deploy,
                        "reason": result_data["Failure"].get("error_message", "Failed on blockchain")
                    })
                    continue
                
                # Try to credit
                try:
                    await process_payment_manual(
                        wallet, 
                        clean_deploy, 
                        csrpPerDeploy, 
                        tokensPerDeploy, 
                        "Starter"
                    )
                    results["credited"].append({
                        "deployHash": clean_deploy,
                        "tokens": tokensPerDeploy
                    })
                    print(f"✅ Credited {tokensPerDeploy} tokens for {clean_deploy[:20]}")
                    
                except Exception as credit_err:
                    if "already processed" in str(credit_err).lower():
                        results["already_credited"].append({
                            "deployHash": clean_deploy,
                            "tokens": tokensPerDeploy
                        })
                        print(f"⚠️ Already credited: {clean_deploy[:20]}")
                    else:
                        results["failed"].append({
                            "deployHash": clean_deploy,
                            "reason": str(credit_err)
                        })
                        
            except Exception as e:
                results["failed"].append({
                    "deployHash": deployHash,
                    "reason": str(e)
                })
        
        total_credited = sum(r["tokens"] for r in results["credited"])
        
        return {
            "success": True,
            "summary": {
                "total_checked": len(deployHashes),
                "credited": len(results["credited"]),
                "already_credited": len(results["already_credited"]),
                "failed": len(results["failed"]),
                "pending": len(results["pending"]),
                "total_tokens_credited": total_credited
            },
            "details": results
        }
        
    except Exception as e:
        print(f"❌ Batch recovery error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# GENERATION ENDPOINTS
# ============================================

@app.post("/api/generate/image")
@limiter.limit("30/minute")
async def generate_image(request: Request, data: GenerateImageRequest):
    """Generate image with FLUX.1-schnell (1 token)"""
    try:
        # Consume tokens
        consumed = await consume_user_tokens(data.walletAddress, 1, "image", data.prompt)
        if not consumed:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
        # Generate image
        url = await asyncio.get_event_loop().run_in_executor(
            None, wavespeed.generate_image, data.prompt
        )
        
        return {
            "success": True,
            "url": url,
            "tokensUsed": 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate/music")
@limiter.limit("10/minute")
async def generate_music(request: Request, data: GenerateMusicRequest):
    """Generate music with HeartMuLa (10 tokens) or MiniMax (15 tokens)"""
    try:
        tokens_needed = 10 if data.quality == "hm" else 15
        
        # Consume tokens
        consumed = await consume_user_tokens(
            data.walletAddress, tokens_needed, "music", f"{data.tags[:50]}..."
        )
        if not consumed:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
        # Generate music
        if data.quality == "minimax":
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_music_minimax, data.lyrics, data.tags
            )
        else:
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_music, data.lyrics, data.tags
            )
        
        return {
            "success": True,
            "url": url,
            "tokensUsed": tokens_needed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate/3d")
@limiter.limit("20/minute")
async def generate_3d(request: Request, data: Generate3DRequest):
    """Generate 3D model (5 tokens without texture, 20 with texture)"""
    try:
        tokens_needed = 20 if data.withTexture else 5
        
        # Consume tokens
        consumed = await consume_user_tokens(
            data.walletAddress, tokens_needed, "3d", f"texture={data.withTexture}"
        )
        if not consumed:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
        # Generate 3D (TODO: implement wavespeed 3D functions)
        # For now, return mock response
        return {
            "success": True,
            "url": "https://example.com/model.glb",
            "tokensUsed": tokens_needed,
            "message": "3D generation coming soon"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
@limiter.limit("50/minute")
async def chat(request: Request, data: ChatRequest):
    """Free chat with Groq (no tokens consumed)"""
    try:
        # TODO: Implement Groq integration
        return {
            "success": True,
            "response": "Chat feature coming soon!",
            "tokensUsed": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
