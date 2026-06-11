"""
TrappistAI Backend - Multi-modal AI Generation Platform
Supports: Image (FLUX), Music (HeartMuLa/MiniMax), 3D (Hunyuan/Tripo), Chat (Groq)
Payment: CSPR (Casper blockchain)
"""
import os
import asyncio
import random
import requests
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from cspr_listener import listen_payments
from db import get_db_session, get_user_balance, consume_user_tokens, get_payment_history
import wavespeed

load_dotenv()

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
conversation_history = {}  # Store per-user conversation history

# Jobs system for async generation (music, 3D, etc.)
import uuid
from typing import Optional
jobs = {}  # {job_id: {status, result, error, created_at, updated_at}}

def create_job(job_type: str) -> str:
    """Create a new job and return job_id"""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "type": job_type,
        "status": "pending",  # pending, processing, completed, failed
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    return job_id

def update_job(job_id: str, status: str, result: Optional[dict] = None, error: Optional[str] = None):
    """Update job status"""
    if job_id in jobs:
        jobs[job_id]["status"] = status
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        if result:
            jobs[job_id]["result"] = result
        if error:
            jobs[job_id]["error"] = error

def get_job(job_id: str) -> Optional[dict]:
    """Get job by ID"""
    return jobs.get(job_id)

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

class GenerateLyricsRequest(BaseModel):
    walletAddress: str
    style: str  # trap, drill, pop, rnb, rock, afrobeat
    voice: str  # male or female
    subject: str  # What the song is about (NOT the musical style)

class VerifyPaymentRequest(BaseModel):
    walletAddress: str
    txHash: str

# ============================================
# GROQ CHAT HELPERS
# ============================================

def _groq_complete(messages: list, max_tokens: int = 800) -> str:
    """Call Groq API for chat completion"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Groq API error: {str(e)}")

def _groq_chat_with_memory(wallet: str, prompt: str) -> str:
    """Chat with memory - remembers conversation history per wallet"""
    if wallet not in conversation_history:
        conversation_history[wallet] = []

    # Add new message
    conversation_history[wallet].append({"role": "user", "content": prompt})

    # Keep only last 10 messages (5 exchanges)
    if len(conversation_history[wallet]) > 10:
        conversation_history[wallet] = conversation_history[wallet][-10:]

    messages = [
        {
            "role": "system", 
            "content": "You are TrappistAI, a friendly, smart, and natural AI assistant. You love AI, crypto, and helping users create amazing content. You remember all previous conversations. Detect the user's language and always reply in that same language."
        }
    ] + conversation_history[wallet]

    try:
        answer = _groq_complete(messages, max_tokens=900)
        conversation_history[wallet].append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        return f"❌ Chat error: {str(e)[:150]}"

def _groq_lyrics(style: str, voice: str, subject: str) -> str:
    """Generate lyrics with Groq - CRITICAL separation between STYLE and SUBJECT"""
    system_msg = (
        "You are a world-class songwriter and lyricist. "
        "CRITICAL: Understand the FUNDAMENTAL difference between MUSICAL STYLE and SONG SUBJECT. "
        "STYLE defines HOW you write (flow, rhythm, energy, delivery). "
        "SUBJECT defines WHAT you write about (the content, the topic). "
        "These are COMPLETELY SEPARATE concepts. A trap song can be about ANYTHING (love, dogs, cars, life). "
        "Detect the language of the subject description and write ALL lyrics in that EXACT same language. "
        "Write ONLY lyrics with structure markers. NO explanations, NO titles."
    )
    
    user_msg = (
        f"MUSICAL STYLE: {style}\n"
        f"(This defines your flow, rhythm, delivery, and energy - NOT the content)\n\n"
        f"VOICE TYPE: {voice} vocals\n\n"
        f"SONG SUBJECT: {subject}\n"
        f"(This is WHAT the lyrics talk about - completely independent of style)\n\n"
        "CRITICAL EXAMPLES to avoid confusion:\n"
        "- Style: 'Trap' + Subject: 'black dog, great companion' → Trap FLOW about a loyal dog (NOT a dog rapping)\n"
        "- Style: 'Pop' + Subject: 'broken laptop, frustration' → Catchy pop song about tech problems\n"
        "- Style: 'Drill' + Subject: 'grandmother, warm cookies' → Dark menacing delivery about grandma\n\n"
        "STRICT TECHNICAL REQUIREMENTS:\n"
        "- Structure markers: [intro-short] [Verse] [Chorus] [Bridge] [outro-short]\n"
        "- Every [Verse]: 6-8 lines with MANDATORY end-of-line rhymes (AABB or ABAB scheme)\n"
        "- Every [Chorus]: 4-6 catchy sticky hook lines (repeatable, memorable)\n"
        "- [Bridge]: 3-4 lines (emotional twist or shift in perspective)\n"
        "- TWO verses + chorus repeated + bridge\n"
        f"- Write ENTIRELY in the SAME language as this subject: '{subject}'\n"
        f"- Apply {style} style characteristics: flow, wordplay, delivery energy\n"
        f"- Make lyrics about: {subject}\n"
        "\nNOW WRITE:\n"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
    
    return _groq_complete(messages, max_tokens=1200)

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
        # Normalize to lowercase
        wallet_normalized = wallet_address.lower().strip()
        print(f"💰 Balance request for: {wallet_normalized[:20]}...")
        balance = await get_user_balance(wallet_normalized)
        print(f"💰 Balance returned: {balance} tokens")
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
# JOB STATUS
# ============================================

@app.get("/api/jobs/{job_id}")
@limiter.limit("60/minute")
async def get_job_status(request: Request, job_id: str):
    """Get job status for async generation (music, 3D, etc.)
    
    Status values:
    - pending: Job created, not started yet
    - processing: Generation in progress
    - completed: Generation successful, result available
    - failed: Generation failed, error available
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# ============================================
# PROFILE & TELEGRAM LINKING
# ============================================

class LinkTelegramRequest(BaseModel):
    walletAddress: str
    telegramUsername: str

class VerifyCodeRequest(BaseModel):
    walletAddress: str
    code: str

@app.get("/api/profile/{wallet_address}")
@limiter.limit("50/minute")
async def get_profile(request: Request, wallet_address: str):
    """Get user profile info including Telegram link status"""
    wallet_normalized = wallet_address.lower().strip()
    
    with get_db_session() as conn:
        result = conn.execute(
            text("""
                SELECT telegram_username, telegram_user_id, telegram_verified, created_at
                FROM users 
                WHERE wallet_address = :wallet
                LIMIT 1
            """),
            {"wallet": wallet_normalized}
        )
        row = result.fetchone()
        
        if not row:
            # Create user if doesn't exist
            conn.execute(
                text("INSERT INTO users (wallet_address, tokens) VALUES (:wallet, 0)"),
                {"wallet": wallet_normalized}
            )
            conn.commit()
            return {
                "wallet_address": wallet_address,
                "telegram_username": None,
                "telegram_verified": False,
                "created_at": datetime.now().isoformat()
            }
        
        return {
            "wallet_address": wallet_address,
            "telegram_username": row[0],
            "telegram_user_id": row[1],
            "telegram_verified": bool(row[2]),
            "created_at": row[3].isoformat() if row[3] else None
        }

@app.post("/api/profile/link-telegram")
@limiter.limit("10/minute")
async def link_telegram(request: Request, data: LinkTelegramRequest):
    """Generate verification code and send to Telegram bot"""
    wallet_normalized = data.walletAddress.lower().strip()
    username = data.telegramUsername.strip().replace('@', '')
    
    if not username:
        raise HTTPException(status_code=400, detail="Telegram username required")
    
    # Generate 6-digit code
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.now() + timedelta(minutes=10)
    
    # Store verification code
    with get_db_session() as conn:
        # Ensure user exists
        result = conn.execute(
            text("SELECT id FROM users WHERE wallet_address = :wallet"),
            {"wallet": wallet_normalized}
        )
        if not result.fetchone():
            conn.execute(
                text("INSERT INTO users (wallet_address, tokens) VALUES (:wallet, 0)"),
                {"wallet": wallet_normalized}
            )
        
        # Insert verification code (delete old ones first)
        conn.execute(
            text("DELETE FROM telegram_verification WHERE wallet_address = :wallet AND verified = 0"),
            {"wallet": wallet_normalized}
        )
        conn.execute(
            text("""
                INSERT INTO telegram_verification 
                (wallet_address, telegram_username, verification_code, expires_at, verified)
                VALUES (:wallet, :username, :code, :expires, 0)
            """),
            {
                "wallet": wallet_normalized,
                "username": username,
                "code": code,
                "expires": expires_at
            }
        )
        conn.commit()
    
    # TODO: Send code to PiranAI bot via webhook
    # For now, we'll return it (in production, only send to Telegram)
    print(f"🔐 Verification code for @{username}: {code}")
    
    try:
        # Try to send to PiranAI bot webhook
        PIRANAI_WEBHOOK = os.getenv("PIRANAI_WEBHOOK_URL")
        if PIRANAI_WEBHOOK:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(PIRANAI_WEBHOOK, json={
                    "action": "send_verification",
                    "username": username,
                    "code": code,
                    "wallet": wallet_normalized,
                    "secret": os.getenv("WEBHOOK_SECRET", "")  # Security check
                })
            print(f"✅ Sent code to @{username} via PiranAI bot")
    except Exception as e:
        print(f"⚠️ Failed to send to PiranAI bot: {e}")
        # Continue anyway - code is stored in DB
    
    return {
        "success": True,
        "message": f"Verification code sent to @{username}",
        "code": code if os.getenv("DEBUG") == "1" else None  # Only in debug mode
    }

@app.post("/api/profile/verify-code")
@limiter.limit("20/minute")
async def verify_code(request: Request, data: VerifyCodeRequest):
    """Verify code and link Telegram account"""
    wallet_normalized = data.walletAddress.lower().strip()
    code = data.code.strip()
    
    if len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid code format")
    
    with get_db_session() as conn:
        # Check verification code
        result = conn.execute(
            text("""
                SELECT telegram_username, expires_at, verified
                FROM telegram_verification
                WHERE wallet_address = :wallet AND verification_code = :code
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"wallet": wallet_normalized, "code": code}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        username, expires_at, verified = row
        
        if verified:
            raise HTTPException(status_code=400, detail="Code already used")
        
        if datetime.now() > expires_at:
            raise HTTPException(status_code=400, detail="Code expired (10 min limit)")
        
        # Mark as verified
        conn.execute(
            text("""
                UPDATE telegram_verification 
                SET verified = 1 
                WHERE wallet_address = :wallet AND verification_code = :code
            """),
            {"wallet": wallet_normalized, "code": code}
        )
        
        # Update user
        conn.execute(
            text("""
                UPDATE users 
                SET telegram_username = :username, telegram_verified = 1 
                WHERE wallet_address = :wallet
            """),
            {"wallet": wallet_normalized, "username": username}
        )
        
        conn.commit()
    
    print(f"✅ Linked @{username} to wallet {wallet_normalized[:10]}...")
    
    return {
        "success": True,
        "message": "Telegram account linked successfully",
        "telegram_username": username
    }

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
        
        # RPC node (mainnet) - ONLY working endpoint
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc"
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
        
        # Normalize wallet address to lowercase
        normalized_wallet = data.wallet.lower().strip()
        print(f"🔐 Verifying payment: wallet={normalized_wallet[:20]}..., deploy={data.deployHash[:20]}...")
        
        # Clean hashes
        clean_deploy = data.deployHash.lower().replace("hash-", "").replace("deploy-", "")
        
        # RPC node - ONLY working endpoint
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc"
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
            # New format (execution_info can be dict or None)
            exec_info = deploy_info.get("execution_info")
            if exec_info and isinstance(exec_info, dict):
                execution_result = exec_info.get("execution_result", {})
                if execution_result and isinstance(execution_result, dict):
                    version2 = execution_result.get("Version2", {})
                    if version2 and isinstance(version2, dict):
                        error_message = version2.get("error_message")
        elif deploy_info.get("execution_results"):
            # Old format
            execution_results = deploy_info.get("execution_results", [])
            if execution_results and len(execution_results) > 0:
                first_result = execution_results[0]
                if first_result and isinstance(first_result, dict):
                    result = first_result.get("result", {})
                    if result and isinstance(result, dict) and "Failure" in result:
                        failure = result.get("Failure", {})
                        if failure and isinstance(failure, dict):
                            error_message = failure.get("error_message", "Unknown error")
        
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
            normalized_wallet, 
            clean_deploy, 
            data.amount, 
            data.tokens, 
            package_name
        )
        
        print(f"💰 Credited {data.tokens} tokens to {normalized_wallet}")
        
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
        
        # RPC node - ONLY working endpoint
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc"
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
        
        # RPC node - ONLY working endpoint
        rpc_nodes = [
            "https://node.mainnet.casper.network/rpc"
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
        # Check balance WITHOUT consuming yet
        current_balance = await get_user_balance(data.walletAddress)
        if current_balance < 1:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
        # Generate image FIRST
        try:
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_image, data.prompt
            )
        except Exception as gen_error:
            # API failed - DON'T consume tokens
            print(f"❌ Image generation failed: {gen_error}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(gen_error)}")
        
        # Only consume tokens if generation succeeded
        consumed = await consume_user_tokens(data.walletAddress, 1, "image", data.prompt)
        if not consumed:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
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
    """Generate music with HeartMuLa (14 tokens) or MiniMax (10 tokens)
    
    Returns job_id immediately. Use GET /api/jobs/{job_id} to check status.
    Generation runs in background and can take 2-10 minutes.
    """
    try:
        tokens_needed = 14 if data.quality == "hm" else 10
        
        # Check balance WITHOUT consuming yet
        current_balance = await get_user_balance(data.walletAddress)
        if current_balance < tokens_needed:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
        # Create job and return immediately
        job_id = create_job("music")
        
        # Launch background generation
        asyncio.create_task(_generate_music_background(
            job_id,
            data.walletAddress,
            data.lyrics,
            data.tags,
            data.quality,
            tokens_needed
        ))
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": "Music generation started. Use GET /api/jobs/{job_id} to check status.",
            "estimatedTime": "2-10 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_music_background(
    job_id: str,
    wallet_address: str,
    lyrics: str,
    tags: str,
    quality: str,
    tokens_needed: int
):
    """Background task for music generation"""
    try:
        update_job(job_id, "processing")
        
        # Generate music with retry + fallback
        fallback_used = False
        try:
            if quality == "minimax":
                url = await asyncio.get_event_loop().run_in_executor(
                    None, wavespeed.generate_music_minimax, lyrics, tags
                )
            else:
                # HeartMuLa with auto-retry
                try:
                    url = await asyncio.get_event_loop().run_in_executor(
                        None, wavespeed.generate_music, lyrics, tags
                    )
                except Exception as hm_error:
                    print(f"⚠️ HeartMuLa failed (attempt 1): {hm_error}")
                    # Retry once
                    try:
                        print("🔄 Retrying HeartMuLa...")
                        url = await asyncio.get_event_loop().run_in_executor(
                            None, wavespeed.generate_music, lyrics, tags
                        )
                    except Exception as retry_error:
                        # Fallback to MiniMax
                        print(f"⚠️ HeartMuLa failed again: {retry_error}")
                        print("🔄 Falling back to MiniMax...")
                        url = await asyncio.get_event_loop().run_in_executor(
                            None, wavespeed.generate_music_minimax, lyrics, tags
                        )
                        fallback_used = True
                        tokens_needed = 10  # MiniMax pricing
        except Exception as gen_error:
            # Both failed - DON'T consume tokens
            print(f"❌ Music generation failed completely: {gen_error}")
            update_job(job_id, "failed", error=f"Generation failed: {str(gen_error)}")
            return
        
        # Only consume tokens if generation succeeded
        consumed = await consume_user_tokens(
            wallet_address, tokens_needed, "music", f"{tags[:50]}..."
        )
        if not consumed:
            # Edge case: balance changed during generation
            update_job(job_id, "failed", error="Insufficient tokens (balance changed)")
            return
        
        result = {
            "url": url,
            "tokensUsed": tokens_needed
        }
        
        # Notify if fallback was used
        if fallback_used:
            result["warning"] = "HeartMuLa unavailable, used MiniMax (saved 4 tokens)"
        
        update_job(job_id, "completed", result=result)
        print(f"✅ Music generation completed: {job_id}")
        
    except Exception as e:
        print(f"❌ Background music generation error: {e}")
        update_job(job_id, "failed", error=str(e))

@app.post("/api/generate/3d")
@limiter.limit("20/minute")
async def generate_3d(request: Request, data: Generate3DRequest):
    """Generate 3D model (2 tokens without texture, 30 with texture)
    
    Returns job_id immediately. Use GET /api/jobs/{job_id} to check status.
    Generation runs in background and can take 5-10 minutes.
    """
    try:
        tokens_needed = 30 if data.withTexture else 2
        
        # Check balance WITHOUT consuming yet
        current_balance = await get_user_balance(data.walletAddress)
        if current_balance < tokens_needed:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
        # Create job and return immediately
        job_id = create_job("3d")
        
        # Launch background generation
        asyncio.create_task(_generate_3d_background(
            job_id,
            data.walletAddress,
            data.imageUrl,
            data.withTexture,
            tokens_needed
        ))
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": "3D generation started. Use GET /api/jobs/{job_id} to check status.",
            "estimatedTime": "5-10 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_3d_background(
    job_id: str,
    wallet_address: str,
    image_url: str,
    with_texture: bool,
    tokens_needed: int
):
    """Background task for 3D generation"""
    try:
        update_job(job_id, "processing")
        
        # Generate 3D
        try:
            if with_texture:
                url = await asyncio.get_event_loop().run_in_executor(
                    None, wavespeed.generate_3d_with_texture, image_url
                )
            else:
                url = await asyncio.get_event_loop().run_in_executor(
                    None, wavespeed.generate_3d_from_image, image_url
                )
        except Exception as gen_error:
            # Generation failed - DON'T consume tokens
            print(f"❌ 3D generation failed: {gen_error}")
            update_job(job_id, "failed", error=f"Generation failed: {str(gen_error)}")
            return
        
        # Only consume tokens if generation succeeded
        consumed = await consume_user_tokens(
            wallet_address, tokens_needed, "3d", f"texture={with_texture}"
        )
        if not consumed:
            update_job(job_id, "failed", error="Insufficient tokens (balance changed)")
            return
        
        result = {
            "url": url,
            "tokensUsed": tokens_needed
        }
        
        update_job(job_id, "completed", result=result)
        print(f"✅ 3D generation completed: {job_id}")
        
    except Exception as e:
        print(f"❌ Background 3D generation error: {e}")
        update_job(job_id, "failed", error=str(e))

@app.post("/api/chat")
@limiter.limit("50/minute")
async def chat(request: Request, data: ChatRequest):
    """Free chat with Groq (no tokens consumed)"""
    try:
        if not GROQ_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Chat service not configured - GROQ_API_KEY missing"
            )
        
        wallet = data.walletAddress
        message = data.message.strip()
        
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Run chat in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _groq_chat_with_memory, wallet, message)
        
        return {
            "success": True,
            "response": response,
            "tokensUsed": 0  # Chat is free!
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate/lyrics")
@limiter.limit("20/minute")
async def generate_lyrics(request: Request, data: GenerateLyricsRequest):
    """Generate lyrics with AI (FREE - no tokens consumed)"""
    try:
        if not GROQ_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Lyrics generation not configured - GROQ_API_KEY missing"
            )
        
        style = data.style.strip()
        voice = data.voice.strip()
        subject = data.subject.strip()
        
        if not style or not voice or not subject:
            raise HTTPException(status_code=400, detail="Style, voice, and subject are required")
        
        print(f"🎤 Generating {style} lyrics ({voice} voice) about: {subject[:50]}...")
        
        # Run lyrics generation in thread pool
        loop = asyncio.get_event_loop()
        lyrics = await loop.run_in_executor(None, _groq_lyrics, style, voice, subject)
        
        print(f"✅ Generated {len(lyrics)} chars of lyrics")
        
        return {
            "success": True,
            "lyrics": lyrics,
            "style": style,
            "voice": voice,
            "subject": subject,
            "tokensUsed": 0  # Lyrics generation is FREE!
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Lyrics generation error: {str(e)}")
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
