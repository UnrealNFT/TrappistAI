"""
Database migration script for Render deployment.
Creates crypto_news table if it doesn't exist.
Called automatically by Procfile 'release' command.
"""
import psycopg2
import os
import sys

def migrate_database():
    """Run database migrations."""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if crypto_news table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'crypto_news'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if table_exists:
            print("✅ crypto_news table already exists - skipping migration")
        else:
            print("📊 Creating crypto_news table...")
            
            # Read and execute schema (Render-compatible version without vector extension)
            schema_file = "news-schema-render.sql" if os.path.exists("news-schema-render.sql") else "news-schema.sql"
            with open(schema_file, "r", encoding="utf-8") as f:
                sql_schema = f.read()
            
            cur.execute(sql_schema)
            
            # Verify creation
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'crypto_news'
            """)
            column_count = cur.fetchone()[0]
            
            print(f"✅ crypto_news table created with {column_count} columns")
        
        cur.close()
        conn.close()
        
        print("✅ Database migration complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(migrate_database())
