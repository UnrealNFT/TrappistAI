"""
Initialize database for TrappistAI
Compatible with both SQLite and PostgreSQL
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
    # SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT
    id_col = "INTEGER PRIMARY KEY AUTOINCREMENT"
    timestamp_default = "CURRENT_TIMESTAMP"
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
    # PostgreSQL uses SERIAL PRIMARY KEY
    id_col = "SERIAL PRIMARY KEY"
    timestamp_default = "NOW()"

print(f"🔧 Initializing database: {DATABASE_URL.split('@')[0]}...")

with engine.connect() as conn:
    # Create users table
    conn.execute(text(f'''
    CREATE TABLE IF NOT EXISTS users (
        id {id_col},
        wallet_address TEXT UNIQUE NOT NULL,
        tokens INTEGER DEFAULT 0,
        telegram_username TEXT,
        telegram_user_id BIGINT,
        telegram_verified BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT {timestamp_default},
        updated_at TIMESTAMP DEFAULT {timestamp_default}
    )
    '''))
    
    # Migrate existing users table to add Telegram columns (if not exists)
    if not DATABASE_URL.startswith("sqlite"):
        # PostgreSQL: Add columns if they don't exist
        try:
            conn.execute(text('''
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(255),
                ADD COLUMN IF NOT EXISTS telegram_user_id BIGINT,
                ADD COLUMN IF NOT EXISTS telegram_verified BOOLEAN DEFAULT FALSE
            '''))
            conn.commit()
            print("  ✓ Telegram columns added/verified")
        except Exception as e:
            print(f"  ⚠ Telegram columns migration: {e}")
    
    # Create payments table
    conn.execute(text(f'''
    CREATE TABLE IF NOT EXISTS payments (
        id {id_col},
        wallet_address TEXT NOT NULL,
        transaction_hash TEXT UNIQUE NOT NULL,
        amount_cspr REAL NOT NULL,
        tokens_purchased INTEGER NOT NULL,
        package_name TEXT,
        network TEXT DEFAULT 'mainnet',
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT {timestamp_default},
        confirmed_at TIMESTAMP
    )
    '''))
    
    # Create generations table
    conn.execute(text(f'''
    CREATE TABLE IF NOT EXISTS generations (
        id {id_col},
        wallet_address TEXT NOT NULL,
        type TEXT NOT NULL,
        prompt TEXT,
        tokens_spent INTEGER NOT NULL,
        result TEXT,
        created_at TIMESTAMP DEFAULT {timestamp_default}
    )
    '''))
    
    # Create telegram_verification table
    conn.execute(text(f'''
    CREATE TABLE IF NOT EXISTS telegram_verification (
        id {id_col},
        wallet_address TEXT NOT NULL,
        telegram_username TEXT NOT NULL,
        verification_code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        verified BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT {timestamp_default}
    )
    '''))
    
    # Create telegram_usernames table (shared between bot and webhook)
    conn.execute(text(f'''
    CREATE TABLE IF NOT EXISTS telegram_usernames (
        username TEXT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        updated_at TIMESTAMP DEFAULT {timestamp_default}
    )
    '''))
    
    conn.commit()
    
    # Create indexes for better performance
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_username)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_payments_wallet ON payments(wallet_address)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_payments_tx ON payments(transaction_hash)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_generations_wallet ON generations(wallet_address)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_telegram_verification_wallet ON telegram_verification(wallet_address)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_telegram_verification_code ON telegram_verification(verification_code)'))
    
    conn.commit()

db_type = "PostgreSQL" if not DATABASE_URL.startswith("sqlite") else "SQLite"
print(f"✅ {db_type} database initialized successfully!")
print("\nTables created:")
print("  • users (with Telegram linking)")
print("  • payments")
print("  • generations")
print("  • telegram_verification")
print("  • indexes for performance")
