"""
Flask Webhook Handler for PiranAI Bot
Receives verification codes from TrappistAI backend and sends to Telegram users

Run alongside bot.py:
1. Terminal 1: python bot.py
2. Terminal 2: python bot_webhook.py
3. Terminal 3: ngrok http 5001
"""
from flask import Flask, request, jsonify
import requests
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8641629385:AAGibWxAiHRqirqrk9Rawt6FAE_DDVtlTmk")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "YOUR_SECRET_HERE_CHANGE_ME")
DB_PATH = os.getenv("DB_PATH", "piranai.db")

def get_user_id_by_username(username: str) -> int | None:
    """Get user_id from username (same DB as bot.py)"""
    try:
        db = sqlite3.connect(DB_PATH)
        clean_username = username.lstrip("@").lower()
        row = db.execute(
            "SELECT user_id FROM telegram_usernames WHERE username = ? COLLATE NOCASE",
            (clean_username,)
        ).fetchone()
        db.close()
        return row[0] if row else None
    except Exception as e:
        print(f"❌ DB error: {e}")
        return None

@app.route('/webhook/verification', methods=['POST'])
def handle_verification():
    """Receive verification code from TrappistAI backend"""
    try:
        data = request.json
        
        # Security check
        if data.get("secret") != WEBHOOK_SECRET:
            print(f"❌ Invalid secret: {data.get('secret')}")
            return jsonify({"error": "Invalid secret"}), 403
        
        username = data.get("username", "").replace("@", "")
        code = data.get("code", "")
        wallet = data.get("wallet", "")
        
        if not username or not code:
            return jsonify({"error": "Missing username or code"}), 400
        
        print(f"📬 Verification request for @{username}: {code}")
        
        # Lookup telegram_user_id from database
        telegram_user_id = get_user_id_by_username(username)
        
        if not telegram_user_id:
            print(f"⚠️  User @{username} not found in database")
            print(f"💡 User needs to run /link in @PiraAi_bot first!")
            return jsonify({
                "error": "User not found",
                "message": f"@{username} needs to run /link in @PiraAi_bot first",
                "hint": "Ask user to open Telegram and send /link to @PiraAi_bot"
            }), 404
        
        # Send message via Telegram Bot API
        success = send_telegram_message(telegram_user_id, code, username)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Verification code sent to @{username}",
                "telegram_user_id": telegram_user_id
            })
        else:
            return jsonify({
                "error": "Failed to send Telegram message",
                "telegram_user_id": telegram_user_id
            }), 500
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

def send_telegram_message(chat_id: int, code: str, username: str = "") -> bool:
    """Send verification code via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    greeting = f"Hi @{username}!\\n\\n" if username else ""
    
    message = f"""{greeting}🔐 **TrappistAI Verification Code**

Your verification code is: `{code}`

Enter this code on [trappisai.netlify.app/profile](https://trappisai.netlify.app/profile) to link your account.

⏰ Code expires in 10 minutes.

🎨 Once linked, all your generations will sync between the website and Telegram bot!
    """.strip()
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"✅ Sent verification code to @{username} (user_id: {chat_id})")
        return True
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
        return False

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "PiranAI Webhook Handler"})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5001))
    print(f"🚀 Starting PiranAI Webhook Handler on port {port}")
    print(f"🔐 Webhook secret: {WEBHOOK_SECRET[:10]}...")
    print(f"📊 Database: {DB_PATH}")
    
    # Production mode with gunicorn (don't run app.run)
    if os.getenv("RENDER"):
        print("✅ Running in Render production mode (gunicorn)")
    else:
        print("\n📋 Local development mode")
        print("   For production, use: gunicorn bot_webhook:app --bind 0.0.0.0:$PORT")
        app.run(host='0.0.0.0', port=port, debug=True)
