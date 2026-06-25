"""
Shared PostgreSQL database functions for TrappistAI
Used by bot, webhook, and backend to sync user tokens
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Get PostgreSQL connection."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(DATABASE_URL)


def store_username_mapping_pg(username: str, user_id: int):
    """Store Telegram username -> user_id mapping."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert or update username mapping
        cur.execute("""
            INSERT INTO telegram_usernames (username, user_id, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (username) 
            DO UPDATE SET user_id = EXCLUDED.user_id, updated_at = NOW()
        """, (username.lstrip("@").lower(), user_id))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Error storing username mapping: {e}")


def get_wallet_by_telegram_id_pg(telegram_user_id: int) -> str | None:
    """Get wallet address by Telegram user ID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT wallet_address 
            FROM users 
            WHERE telegram_user_id = %s AND telegram_verified = TRUE
            LIMIT 1
        """, (telegram_user_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        return row[0] if row else None
    except Exception as e:
        print(f"⚠️ Error getting wallet: {e}")
        return None


def get_user_id_by_username_pg(username: str) -> int | None:
    """Get Telegram user_id from username."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        clean_username = username.lstrip("@").lower()
        
        cur.execute("""
            SELECT user_id 
            FROM telegram_usernames 
            WHERE LOWER(username) = %s
            LIMIT 1
        """, (clean_username,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        return row[0] if row else None
    except Exception as e:
        print(f"⚠️ Error getting user_id: {e}")
        return None


def get_tokens_pg(telegram_user_id: int) -> int:
    """Get token balance for Telegram user."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user by telegram_user_id
        cur.execute("""
            SELECT tokens 
            FROM users 
            WHERE telegram_user_id = %s
            LIMIT 1
        """, (telegram_user_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        return row[0] if row else 0
        
    except Exception as e:
        print(f"⚠️ Error getting tokens: {e}")
        return 0


def add_tokens_pg(telegram_user_id: int, amount: int) -> int:
    """Add tokens to user balance (for gifts/purchases)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists by telegram_user_id
        cur.execute("""
            SELECT wallet_address, tokens 
            FROM users 
            WHERE telegram_user_id = %s
            LIMIT 1
        """, (telegram_user_id,))
        
        existing = cur.fetchone()
        
        if existing:
            # User exists - just add tokens
            cur.execute("""
                UPDATE users 
                SET tokens = tokens + %s, updated_at = NOW()
                WHERE telegram_user_id = %s
                RETURNING tokens
            """, (amount, telegram_user_id))
            result = cur.fetchone()
            new_balance = result[0] if result else 0
        else:
            # Create new user with dummy wallet
            dummy_wallet = f"tg_{telegram_user_id}"
            cur.execute("""
                INSERT INTO users (telegram_user_id, tokens, wallet_address)
                VALUES (%s, %s, %s)
                RETURNING tokens
            """, (telegram_user_id, amount, dummy_wallet))
            result = cur.fetchone()
            new_balance = result[0] if result else 0
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Added {amount} tokens to user {telegram_user_id}, new balance: {new_balance}")
        return new_balance
        
    except Exception as e:
        print(f"⚠️ Error adding tokens: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: try to get current balance
        try:
            return get_tokens_pg(telegram_user_id)
        except:
            return 0


def consume_tokens_pg(telegram_user_id: int, amount: int, admin_username: str = "") -> bool:
    """
    Consume tokens for generation.
    Returns True if successful, False if insufficient balance.
    Admin always passes.
    """
    try:
        # Admin bypass
        if admin_username and len(admin_username) > 0:
            return True
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check balance first
        cur.execute("""
            SELECT tokens 
            FROM users 
            WHERE telegram_user_id = %s
        """, (telegram_user_id,))
        
        row = cur.fetchone()
        
        if not row or row[0] < amount:
            cur.close()
            conn.close()
            return False
        
        # Consume tokens
        cur.execute("""
            UPDATE users 
            SET tokens = tokens - %s, updated_at = NOW()
            WHERE telegram_user_id = %s AND tokens >= %s
            RETURNING tokens
        """, (amount, telegram_user_id, amount))
        
        result = cur.fetchone()
        success = result is not None
        
        conn.commit()
        cur.close()
        conn.close()
        
        if success:
            print(f"✅ Consumed {amount} tokens from user {telegram_user_id}, remaining: {result[0]}")
        
        return success
        
    except Exception as e:
        print(f"⚠️ Error consuming tokens: {e}")
        return False
