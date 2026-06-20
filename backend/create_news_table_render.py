"""
Create crypto_news table on Render production database.
Usage: python create_news_table_render.py <DATABASE_URL>

Get your DATABASE_URL from Render Dashboard > PostgreSQL > Connect > External Database URL
Example:
  postgresql://user:password@hostname.render.com:5432/dbname
"""
import psycopg2
import sys

if len(sys.argv) < 2:
    print("❌ Missing DATABASE_URL argument")
    print("")
    print("Usage: python create_news_table_render.py <DATABASE_URL>")
    print("")
    print("Get DATABASE_URL from:")
    print("  Render Dashboard > PostgreSQL Database > Connect > External Database URL")
    print("")
    print("Example:")
    print('  python create_news_table_render.py "postgresql://user:pass@host.render.com:5432/db"')
    sys.exit(1)

DATABASE_URL = sys.argv[1]

# Read SQL schema
print("📖 Reading news-schema.sql...")
with open("news-schema.sql", "r", encoding="utf-8") as f:
    sql_schema = f.read()

try:
    # Connect to Render database
    print("🔌 Connecting to Render database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Check if table already exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'crypto_news'
        )
    """)
    exists = cur.fetchone()[0]
    
    if exists:
        print("⚠️  Table 'crypto_news' already exists!")
        response = input("    Drop and recreate? (y/N): ").strip().lower()
        if response == 'y':
            print("🗑️  Dropping existing table...")
            cur.execute("DROP TABLE IF EXISTS crypto_news CASCADE")
        else:
            print("❌ Aborted")
            sys.exit(0)
    
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
        
        # Check columns
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'crypto_news'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        print(f"✅ Created {len(columns)} columns:")
        for col in columns[:5]:  # Show first 5
            print(f"   - {col[0]} ({col[1]})")
        if len(columns) > 5:
            print(f"   ... and {len(columns) - 5} more")
        
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
            WHERE tgrelid = 'crypto_news'::regclass AND tgisinternal = false
        """)
        triggers = cur.fetchall()
        print(f"✅ Created {len(triggers)} triggers")
        
        # Check views
        cur.execute("""
            SELECT table_name FROM information_schema.views 
            WHERE table_name = 'recent_crypto_news'
        """)
        views = cur.fetchall()
        if views:
            print(f"✅ Created view 'recent_crypto_news'")
        
    else:
        print("❌ Table creation failed")
    
    cur.close()
    conn.close()
    
    print("\n🎉 Production database setup complete!")
    print("✅ Ready to run news-fetcher.py")

except psycopg2.OperationalError as e:
    print(f"❌ Connection error: {e}")
    print("\nℹ️ Check:")
    print("   1. DATABASE_URL is correct")
    print("   2. IP is whitelisted on Render")
    print("   3. Database is running")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
