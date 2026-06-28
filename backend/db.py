"""
Database operations for TrappistAI
Uses SQLAlchemy with SQLite for testing
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trappistai.db")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )


# Asyncpg pool for news fetcher (PostgreSQL only)
_asyncpg_pool = None

async def get_db_pool():
    """Get asyncpg connection pool for async operations (news fetcher)."""
    global _asyncpg_pool
    
    if DATABASE_URL.startswith("sqlite"):
        # SQLite not supported for async pool
        raise RuntimeError("News fetcher requires PostgreSQL DATABASE_URL")
    
    if _asyncpg_pool is None:
        _asyncpg_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    
    return _asyncpg_pool

def get_db_session():
    """Get database connection"""
    return engine.connect()


async def get_user_balance(wallet_address: str) -> int:
    """Get user's token balance"""
    # Normalize to lowercase
    wallet_normalized = wallet_address.lower().strip()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT tokens FROM users WHERE wallet_address = :wallet LIMIT 1"),
            {"wallet": wallet_normalized}
        )
        row = result.fetchone()
        return row[0] if row else 0


async def consume_user_tokens(wallet_address: str, tokens: int, gen_type: str, prompt: str) -> bool:
    """
    Consume tokens for generation
    Returns True if successful, False if insufficient balance
    """
    # Normalize to lowercase
    wallet_normalized = wallet_address.lower().strip()
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Check balance
            result = conn.execute(
                text("SELECT tokens FROM users WHERE wallet_address = :wallet LIMIT 1"),
                {"wallet": wallet_normalized}
            )
            row = result.fetchone()
            current_tokens = row[0] if row else 0
            
            if current_tokens < tokens:
                trans.rollback()
                return False
            
            # Deduct tokens
            conn.execute(
                text("""
                    UPDATE users 
                    SET tokens = tokens - :tokens, updated_at = CURRENT_TIMESTAMP 
                    WHERE wallet_address = :wallet
                """),
                {"tokens": tokens, "wallet": wallet_normalized}
            )
            
            # Log generation
            conn.execute(
                text("""
                    INSERT INTO generations (wallet_address, type, prompt, tokens_spent)
                    VALUES (:wallet, :type, :prompt, :tokens)
                """),
                {
                    "wallet": wallet_normalized,
                    "type": gen_type,
                    "prompt": prompt[:500],  # Limit prompt length
                    "tokens": tokens
                }
            )
            
            trans.commit()
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"[DB] Error consuming tokens: {e}")
            return False


async def user_is_testnet_only(wallet_address: str) -> bool:
    """
    True only if this wallet has bought testnet (x402) credits and has NEVER
    made a real payment. Used to watermark demo/testnet images while ensuring
    real paying users are never watermarked.
    """
    w = wallet_address.lower().strip()
    try:
        with engine.connect() as conn:
            real = conn.execute(
                text("""
                    SELECT COUNT(*) FROM payments
                    WHERE wallet_address = :w AND status = 'confirmed'
                      AND COALESCE(package_name, '') NOT LIKE '%testnet%'
                """),
                {"w": w},
            ).scalar() or 0
            if real > 0:
                return False
            testnet = conn.execute(
                text("""
                    SELECT COUNT(*) FROM payments
                    WHERE wallet_address = :w AND status = 'confirmed'
                      AND COALESCE(package_name, '') LIKE '%testnet%'
                """),
                {"w": w},
            ).scalar() or 0
            return testnet > 0
    except Exception as e:
        print(f"[DB] user_is_testnet_only error: {e}")
        return False


async def process_payment(wallet_address: str, tx_hash: str, amount_cspr: float, tokens: int, package_name: str) -> bool:
    """
    Process payment: save payment record and credit tokens
    Returns True if successful, False if already processed
    """
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Check if already processed
            result = conn.execute(
                text("SELECT id FROM payments WHERE transaction_hash = :tx LIMIT 1"),
                {"tx": tx_hash}
            )
            if result.fetchone():
                trans.rollback()
                return False  # Already processed
            
            # Save payment
            conn.execute(
                text("""
                    INSERT INTO payments 
                    (wallet_address, amount_cspr, tokens_purchased, package_name, transaction_hash, network, status, confirmed_at)
                    VALUES (:wallet, :amount, :tokens, :package, :tx, 'mainnet', 'confirmed', CURRENT_TIMESTAMP)
                """),
                {
                    "wallet": wallet_address,
                    "amount": amount_cspr,
                    "tokens": tokens,
                    "package": package_name,
                    "tx": tx_hash
                }
            )
            
            # Credit tokens
            conn.execute(
                text("""
                    INSERT INTO users (wallet_address, tokens, created_at, updated_at)
                    VALUES (:wallet, :tokens, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (wallet_address)
                    DO UPDATE SET 
                        tokens = users.tokens + :tokens,
                        updated_at = CURRENT_TIMESTAMP
                """),
                {"wallet": wallet_address, "tokens": tokens}
            )
            
            trans.commit()
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"[DB] Error processing payment: {e}")
            return False


async def process_payment_manual(wallet_address: str, tx_hash: str, amount_cspr: float, tokens: int, package_name: str):
    """Manual payment processing (same as process_payment but raises exceptions)"""
    # Normalize to lowercase
    wallet_normalized = wallet_address.lower().strip()
    tx_normalized = tx_hash.lower().strip()
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Check if already processed
            result = conn.execute(
                text("SELECT id FROM payments WHERE transaction_hash = :tx LIMIT 1"),
                {"tx": tx_normalized}
            )
            if result.fetchone():
                trans.rollback()
                raise Exception("Payment already processed")
            
            # Save payment
            conn.execute(
                text("""
                    INSERT INTO payments 
                    (wallet_address, amount_cspr, tokens_purchased, package_name, transaction_hash, network, status, confirmed_at)
                    VALUES (:wallet, :amount, :tokens, :package, :tx, 'mainnet', 'confirmed', CURRENT_TIMESTAMP)
                """),
                {
                    "wallet": wallet_normalized,
                    "amount": amount_cspr,
                    "tokens": tokens,
                    "package": package_name,
                    "tx": tx_normalized
                }
            )
            
            # Credit tokens
            conn.execute(
                text("""
                    INSERT INTO users (wallet_address, tokens, created_at, updated_at)
                    VALUES (:wallet, :tokens, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (wallet_address)
                    DO UPDATE SET 
                        tokens = users.tokens + :tokens,
                        updated_at = CURRENT_TIMESTAMP
                """),
                {"wallet": wallet_normalized, "tokens": tokens}
            )
            
            # Read back telegram link + new balance for notification
            info = conn.execute(
                text("""
                    SELECT telegram_user_id, telegram_verified, tokens
                    FROM users WHERE wallet_address = :wallet LIMIT 1
                """),
                {"wallet": wallet_normalized}
            ).fetchone()
            
            trans.commit()
            
            # Notify the user on Telegram if their account is linked (best-effort)
            if info and info[0] and info[1]:
                await _notify_telegram_topup(info[0], tokens, info[2])
            
        except Exception as e:
            trans.rollback()
            raise e


async def _notify_telegram_topup(telegram_user_id: int, tokens_added: int, new_balance: int):
    """Send a 'credits received' message to the user on Telegram. Best-effort."""
    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        print("⚠️ BOT_TOKEN not set — skipping Telegram top-up notification")
        return
    try:
        import httpx
        message = (
            "✅ *Credits received!*\n\n"
            f"💎 *+{tokens_added} tokens* added to your account\n"
            f"💰 New balance: *{new_balance} tokens*\n\n"
            "🖼 `/image your prompt` — generate AI images\n"
            "🎵 `/music` — create custom songs\n"
            "🧊 `/3d` — turn images into 3D models"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": telegram_user_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
        print(f"✅ Notified Telegram user {telegram_user_id}: +{tokens_added} tokens")
    except Exception as e:
        print(f"⚠️ Could not send Telegram top-up notification: {e}")


async def get_payment_history(wallet_address: str) -> list:
    """Get user's payment history"""
    # Normalize to lowercase
    wallet_normalized = wallet_address.lower().strip()
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    id, amount_cspr, tokens_purchased, package_name, 
                    transaction_hash, status, confirmed_at
                FROM payments 
                WHERE wallet_address = :wallet 
                ORDER BY confirmed_at DESC
                LIMIT 50
            """),
            {"wallet": wallet_normalized}
        )
        
        payments = []
        for row in result:
            payments.append({
                "id": row[0],
                "amount_cspr": float(row[1]),
                "tokens_purchased": row[2],
                "package_name": row[3],
                "transaction_hash": row[4],
                "status": row[5],
                "confirmed_at": row[6].isoformat() if row[6] else None
            })
        
        return payments


if __name__ == "__main__":
    """Test database connection"""
    print("Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
