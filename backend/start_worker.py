#!/usr/bin/env python3
"""
TrappistAI Worker Launcher
Runs news fetcher daemon + Telegram bot in same process
"""
import asyncio
import os
import sys
import time
import signal
from multiprocessing import Process

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_flag
    print(f"\n⚠️ Received signal {signum}, shutting down gracefully...")
    shutdown_flag = True


async def run_news_fetcher():
    """Run news fetcher daemon (fetch every 5 minutes)."""
    from news_fetcher import fetch_and_store_news
    
    print("📰 News fetcher starting (will fetch every 5 minutes)...")
    
    # Wait 30 seconds before first fetch (let bot initialize)
    await asyncio.sleep(30)
    
    fetch_count = 0
    while not shutdown_flag:
        try:
            fetch_count += 1
            print(f"\n🔄 News fetch cycle #{fetch_count} starting...")
            await fetch_and_store_news()
            print(f"✅ News fetch cycle #{fetch_count} complete")
            
            # Sleep 5 minutes (300 seconds)
            for _ in range(60):  # Check shutdown every 5 seconds
                if shutdown_flag:
                    break
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"❌ News fetcher error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute on error


def run_news_fetcher_process():
    """Run news fetcher in async loop."""
    asyncio.run(run_news_fetcher())


def run_telegram_bot():
    """Run Telegram bot (blocking)."""
    print("🤖 Telegram bot starting...")
    
    # Import and run bot main function
    from bot.bot import main as bot_main
    bot_main()  # This is blocking - runs until bot stops


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("🚀 TrappistAI Worker Starting")
    print("=" * 60)
    print("   Components:")
    print("   - Telegram Bot (@TrappistAI_bot)")
    print("   - Crypto News Fetcher (every 5 minutes)")
    print("=" * 60)
    
    # Start news fetcher in separate process
    fetcher_process = Process(target=run_news_fetcher_process, daemon=True)
    fetcher_process.start()
    print(f"✅ News fetcher process started (PID: {fetcher_process.pid})")
    
    try:
        # Run bot in main thread (blocking)
        run_telegram_bot()
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt received")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
    finally:
        print("\n👋 Shutting down worker...")
        shutdown_flag = True
        
        # Wait for fetcher to finish
        if fetcher_process.is_alive():
            print("⏳ Waiting for news fetcher to stop...")
            fetcher_process.join(timeout=10)
            if fetcher_process.is_alive():
                print("⚠️ Force terminating news fetcher...")
                fetcher_process.terminate()
        
        print("✅ Worker shutdown complete")
