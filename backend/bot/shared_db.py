"""
Shared database functions for PostgreSQL (used by bot and webhook)
This allows bot and webhook to share telegram_usernames table
Uses psycopg2 directly (no SQLAlchemy) to avoid Python 3.14 compatibility issues
"""
import os
import psycopg2
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_pg_connection():
    """Get PostgreSQL connection using psycopg2"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    
    conn = psycopg2.connect(DATABASE_URL)
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
