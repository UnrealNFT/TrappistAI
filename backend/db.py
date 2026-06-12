"""
Database operations for TrappistAI
Uses SQLAlchemy with SQLite for testing
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trappistai.db")

# Convert postgres:// to postgresql+psycopg:// for psycopg v3 support
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

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
            
            trans.commit()
            
        except Exception as e:
            trans.rollback()
            raise e


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
