#!/usr/bin/env python3
"""
Delete broken RWA tokens #20 and #21 with malformed URLs
Run this script once to clean up the database
"""
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

def delete_broken_tokens():
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trappistai.db")
    
    # Check if using SQLite (local) or PostgreSQL (production)
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
        if not os.path.exists(db_path):
            print(f"❌ SQLite database not found: {db_path}")
            return
        print(f"📂 Using SQLite database: {db_path}")
        conn = sqlite3.connect(db_path)
    else:
        print("🚨 PostgreSQL detected - use this script on Render production server")
        return
    
    cursor = conn.cursor()
    
    try:
        # Check tokens before deletion
        print("🔍 Checking tokens #20 and #21 before deletion...")
        cursor.execute("""
            SELECT token_id, asset_type, asset_url, prompt, created_at 
            FROM rwa_tokens 
            WHERE token_id IN (20, 21)
        """)
        tokens = cursor.fetchall()
        
        if not tokens:
            print("✅ No broken tokens found (already deleted or don't exist)")
            return
        
        print(f"\n📋 Found {len(tokens)} token(s) to delete:")
        for token in tokens:
            token_id, asset_type, asset_url, prompt, created_at = token
            print(f"   #{token_id} - {asset_type} - {asset_url[:60]}...")
        
        # Delete the broken tokens
        print("\n🗑️ Deleting tokens #20 and #21...")
        cursor.execute("DELETE FROM rwa_tokens WHERE token_id IN (20, 21)")
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ Deleted {deleted_count} token(s)")
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM rwa_tokens")
        remaining = cursor.fetchone()[0]
        print(f"📊 Remaining tokens in database: {remaining}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🧹 Cleaning broken RWA tokens...\n")
    delete_broken_tokens()
    print("\n✅ Done!")
