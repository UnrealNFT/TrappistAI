"""
Shared database functions for PostgreSQL (used by bot and webhook)
This allows bot and webhook to share telegram_usernames table
"""
import os
from sqlalchemy import create_engine, text
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_pg_connection():
    """Get PostgreSQL connection"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
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
            conn.execute(
                text("""
                    INSERT INTO telegram_usernames (username, user_id, updated_at)
                    VALUES (:username, :user_id, NOW())
                    ON CONFLICT (username) 
                    DO UPDATE SET user_id = :user_id, updated_at = NOW()
                """),
                {"username": clean_username, "user_id": user_id}
            )
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
            result = conn.execute(
                text("SELECT user_id FROM telegram_usernames WHERE username = :username"),
                {"username": clean_username}
            ).fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"⚠️ Failed to query PostgreSQL: {e}")
        return None
