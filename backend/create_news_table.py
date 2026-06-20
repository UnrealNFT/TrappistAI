"""
Quick script to create crypto_news table without psql command.
Just run: python create_news_table.py
"""
import psycopg2
import os

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/trappistai")

# Read SQL schema
with open("news-schema.sql", "r", encoding="utf-8") as f:
    sql_schema = f.read()

try:
    # Connect to database
    print("🔌 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Execute schema
    print("📊 Creating crypto_news table...")
    cur.execute(sql_schema)
    
    # Verify table exists
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name = 'crypto_news'
    """)
    result = cur.fetchone()
    
    if result:
        print("✅ Table 'crypto_news' created successfully!")
        
        # Check indexes
        cur.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'crypto_news'
        """)
        indexes = cur.fetchall()
        print(f"✅ Created {len(indexes)} indexes")
        
        # Check triggers
        cur.execute("""
            SELECT tgname FROM pg_trigger 
            WHERE tgrelid = 'crypto_news'::regclass
        """)
        triggers = cur.fetchall()
        print(f"✅ Created {len(triggers)} triggers")
        
    else:
        print("❌ Table creation failed")
    
    cur.close()
    conn.close()
    
    print("\n🎉 Database setup complete!")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nℹ️ Make sure:")
    print("   1. PostgreSQL is running")
    print("   2. Database 'trappistai' exists")
    print("   3. DATABASE_URL is correct")
