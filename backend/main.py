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
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
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
