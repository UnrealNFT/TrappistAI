"""
Shared database functions for PostgreSQL (used by bot and webhook)
This allows bot and webhook to share telegram_usernames table
Uses psycopg v3 directly (no SQLAlchemy) for Python 3.14 compatibility
"""
import os
import psycopg
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_pg_connection():
    """Get PostgreSQL connection using psycopg v3"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

def store_username_mapping_pg(user_id: int, username: str):
    """Store or update username → user_id mapping in PostgreSQL"""
    if not username or not DATABASE_URL:
        return
    
    clean_username = username.lstrip("@").lower()
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO telegram_usernames (username, user_id, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (username) 
                    DO UPDATE SET user_id = %s, updated_at = NOW()
                """, (clean_username, user_id, user_id))
                conn.commit()
                print(f"✅ Stored @{clean_username} → {user_id} in PostgreSQL")
    except Exception as e:
        print(f"⚠️ Failed to store in PostgreSQL: {e}")

def get_user_id_by_username_pg(username: str) -> int | None:
    """Get user_id from username from PostgreSQL"""
    if not DATABASE_URL:
        return None
    
    clean_username = username.lstrip("@").lower()
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM telegram_usernames WHERE username = %s",
                    (clean_username,)
                )
                result = cur.fetchone()
                return result[0] if result else None
    except Exception as e:
        print(f"⚠️ Failed to query PostgreSQL: {e}")
        return None

def get_tokens_pg(telegram_user_id: int) -> int:
    """Get token balance from PostgreSQL users table"""
    if not DATABASE_URL:
        return 0
    
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tokens FROM users WHERE telegram_user_id = %s",
                    (telegram_user_id,)
                )
                result = cur.fetchone()
                return result[0] if result else 0
    except Exception as e:
        print(f"⚠️ Failed to get tokens from PostgreSQL: {e}")
        return 0

def consume_tokens_pg(telegram_user_id: int, amount: int, admin_username: str = "") -> bool:
    """
    Consume tokens from PostgreSQL. 
    Admin users (by telegram_username match) always pass without consuming.
    Returns True if successful, False if insufficient tokens.
    """
    if not DATABASE_URL:
        return False
    
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                # Check if user is admin
                if admin_username:
                    clean_admin = admin_username.lstrip("@").lower()
                    cur.execute(
                        "SELECT telegram_username FROM users WHERE telegram_user_id = %s",
                        (telegram_user_id,)
                    )
                    result = cur.fetchone()
                    if result and result[0] and result[0].lower() == clean_admin:
                        print(f"👑 Admin @{clean_admin} bypass token check")
                        return True
                
                # Get current balance
                cur.execute(
                    "SELECT tokens FROM users WHERE telegram_user_id = %s",
                    (telegram_user_id,)
                )
                result = cur.fetchone()
                if not result or result[0] < amount:
                    print(f"❌ Insufficient tokens: {result[0] if result else 0} < {amount}")
                    return False
                
                # Deduct tokens
                cur.execute(
                    "UPDATE users SET tokens = tokens - %s WHERE telegram_user_id = %s",
                    (amount, telegram_user_id)
                )
                conn.commit()
                print(f"✅ Consumed {amount} tokens from user {telegram_user_id}")
                return True
    except Exception as e:
        print(f"⚠️ Failed to consume tokens from PostgreSQL: {e}")
        return False

def add_tokens_pg(telegram_user_id: int, amount: int) -> int:
    """Add tokens to PostgreSQL users table. Returns new balance.

    If the user has not linked a wallet yet (no row with this telegram_user_id),
    a placeholder row keyed by `telegram:{id}` is created so gifted tokens are
    never lost. When the user later links a real wallet via /verify, those
    tokens are transferred to the real wallet row.
    """
    if not DATABASE_URL:
        return 0
    
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET tokens = tokens + %s, updated_at = NOW()
                    WHERE telegram_user_id = %s
                    RETURNING tokens
                """, (amount, telegram_user_id))
                result = cur.fetchone()

                if result is None:
                    # No wallet-linked row yet — store the gift on a placeholder row.
                    placeholder_wallet = f"telegram:{telegram_user_id}"
                    cur.execute("""
                        INSERT INTO users (wallet_address, tokens, telegram_user_id, telegram_verified)
                        VALUES (%s, %s, %s, FALSE)
                        ON CONFLICT (wallet_address)
                        DO UPDATE SET tokens = users.tokens + EXCLUDED.tokens, updated_at = NOW()
                        RETURNING tokens
                    """, (placeholder_wallet, amount, telegram_user_id))
                    result = cur.fetchone()
                    print(f"🆕 No linked wallet for {telegram_user_id}, stored gift on placeholder row")

                conn.commit()
                new_balance = result[0] if result else 0
                print(f"✅ Added {amount} tokens to user {telegram_user_id}, new balance: {new_balance}")
                return new_balance
    except Exception as e:
        print(f"⚠️ Failed to add tokens to PostgreSQL: {e}")
        return 0


def get_wallet_by_telegram_id_pg(telegram_user_id: int) -> str:
    """
    Get wallet address for a Telegram user from PostgreSQL.
    Returns wallet address or empty string if not found/verified.
    """
    if not DATABASE_URL:
        return ""
    
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT wallet_address 
                    FROM users 
                    WHERE telegram_user_id = %s 
                      AND telegram_verified = TRUE
                    LIMIT 1
                """, (telegram_user_id,))
                result = cur.fetchone()
                return result[0] if result else ""
    except Exception as e:
        print(f"⚠️ Failed to get wallet from PostgreSQL: {e}")
        return ""

