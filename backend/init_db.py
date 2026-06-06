"""
Initialize SQLite database for TrappistAI
"""
import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('trappistai.db')
cursor = conn.cursor()

# Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT UNIQUE NOT NULL,
    tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create payments table
cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    transaction_hash TEXT UNIQUE NOT NULL,
    amount_cspr REAL NOT NULL,
    tokens_purchased INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP
)
''')

# Create generations table
cursor.execute('''
CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    type TEXT NOT NULL,
    prompt TEXT,
    tokens_spent INTEGER NOT NULL,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create indexes
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_wallet ON payments(wallet_address)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_tx ON payments(transaction_hash)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_generations_wallet ON generations(wallet_address)')

conn.commit()
conn.close()

print("✅ SQLite database initialized successfully!")
print("📁 Database file: trappistai.db")
print("\nTables created:")
print("  • users")
print("  • payments")
print("  • generations")
