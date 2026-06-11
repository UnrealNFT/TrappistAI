"""
Migration: Add Telegram linking fields to users table
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

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

print(f"🔧 Running Telegram migration on: {DATABASE_URL.split('@')[0]}...")

with engine.connect() as conn:
    # Add telegram columns to users table if they don't exist
    try:
        # Check if columns exist (will fail if they do in some DBs)
        conn.execute(text('''
        ALTER TABLE users 
        ADD COLUMN telegram_username TEXT
        '''))
        print("✅ Added telegram_username column")
    except Exception as e:
        print(f"ℹ️  telegram_username column may already exist: {e}")
    
    try:
        conn.execute(text('''
        ALTER TABLE users 
        ADD COLUMN telegram_user_id TEXT
        '''))
        print("✅ Added telegram_user_id column")
    except Exception as e:
        print(f"ℹ️  telegram_user_id column may already exist: {e}")
    
    try:
        conn.execute(text('''
        ALTER TABLE users 
        ADD COLUMN telegram_verified INTEGER DEFAULT 0
        '''))
        print("✅ Added telegram_verified column")
    except Exception as e:
        print(f"ℹ️  telegram_verified column may already exist: {e}")
    
    # Create verification codes table
    id_col = "INTEGER PRIMARY KEY AUTOINCREMENT" if DATABASE_URL.startswith("sqlite") else "SERIAL PRIMARY KEY"
    timestamp_default = "CURRENT_TIMESTAMP" if DATABASE_URL.startswith("sqlite") else "NOW()"
    
    conn.execute(text(f'''
    CREATE TABLE IF NOT EXISTS telegram_verification (
        id {id_col},
        wallet_address TEXT NOT NULL,
        telegram_username TEXT NOT NULL,
        verification_code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT {timestamp_default}
    )
    '''))
    print("✅ Created telegram_verification table")
    
    # Create index
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_verification_wallet ON telegram_verification(wallet_address)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_verification_code ON telegram_verification(verification_code)'))
    
    conn.commit()

print("\n✅ Telegram migration completed successfully!")
print("\nNew columns:")
print("  • users.telegram_username")
print("  • users.telegram_user_id")
print("  • users.telegram_verified")
print("\nNew table:")
print("  • telegram_verification")
