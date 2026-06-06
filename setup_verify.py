#!/usr/bin/env python3
"""
TrappistAI Setup & Verification Script
Run this after installation to verify everything is configured correctly
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_env_var(name, required=True, secret=False):
    value = os.getenv(name)
    if value:
        display = "***HIDDEN***" if secret else value[:50] + "..." if len(value) > 50 else value
        print(f"✅ {name}: {display}")
        return True
    else:
        status = "❌ REQUIRED" if required else "⚠️  OPTIONAL"
        print(f"{status} {name}: NOT SET")
        return not required

def check_database():
    """Test database connection"""
    try:
        from sqlalchemy import create_engine, text
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False
        
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Database connection successful")
        
        # Check tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
        
        required_tables = ['users', 'payments', 'generations']
        for table in required_tables:
            if table in tables:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' missing (run schema.sql)")
        
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_wavespeed():
    """Test WaveSpeed API"""
    try:
        import requests
        api_key = os.getenv("WAVESPEED_API_KEY")
        if not api_key:
            print("❌ WAVESPEED_API_KEY not set")
            return False
        
        # Simple API test (just check auth)
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get("https://api.wavespeed.ai/api/v3/models", headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ WaveSpeed API connection successful")
            return True
        else:
            print(f"⚠️  WaveSpeed API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ WaveSpeed error: {e}")
        return False

def check_cspr_cloud():
    """Test CSPR.cloud API key"""
    api_key = os.getenv("CSPR_CLOUD_KEY")
    if not api_key:
        print("❌ CSPR_CLOUD_KEY not set")
        return False
    
    print("✅ CSPR_CLOUD_KEY is set (WebSocket test requires connection)")
    return True

def check_groq():
    """Test Groq API"""
    try:
        import requests
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ GROQ_API_KEY not set")
            return False
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Groq API connection successful")
            return True
        else:
            print(f"⚠️  Groq API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Groq error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  🚀 TrappistAI Setup & Verification")
    print("="*60)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required (current: {sys.version_info.major}.{sys.version_info.minor})")
        return
    print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check environment variables
    print_section("Environment Variables")
    
    all_good = True
    all_good &= check_env_var("DATABASE_URL", required=True, secret=True)
    all_good &= check_env_var("RECEIVER_WALLET", required=True)
    all_good &= check_env_var("RECEIVER_ACCOUNT_HASH", required=True)
    all_good &= check_env_var("CSPR_CLOUD_KEY", required=True, secret=True)
    all_good &= check_env_var("WAVESPEED_API_KEY", required=True, secret=True)
    all_good &= check_env_var("GROQ_API_KEY", required=False, secret=True)
    all_good &= check_env_var("ALLOWED_ORIGINS", required=True)
    
    if not all_good:
        print("\n⚠️  Some required environment variables are missing!")
        print("Copy .env.example to .env and fill in the values\n")
    
    # Check database
    print_section("Database Connection")
    check_database()
    
    # Check APIs
    print_section("External APIs")
    check_wavespeed()
    check_cspr_cloud()
    check_groq()
    
    # Summary
    print_section("Summary")
    print("✅ Setup verification complete!")
    print("\nNext steps:")
    print("1. Fix any ❌ errors above")
    print("2. Run backend: cd backend && python main.py")
    print("3. Run frontend: cd frontend && npm run dev")
    print("4. Open http://localhost:5173")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    # Change to backend directory if exists
    if os.path.exists("backend"):
        os.chdir("backend")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
