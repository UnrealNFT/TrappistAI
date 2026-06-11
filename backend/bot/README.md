# 🤖 PiranAI Bot

Telegram bot pour génération d'images, musique et 3D avec IA. Intégration avec TrappistAI website.

## Features

- 🖼️ **Image Generation** - FLUX.1-schnell via WaveSpeed API
- 🎵 **Music Generation** - HeartMuLa & MiniMax 2.5 HD with AI lyrics
- 🎨 **3D Generation** - Hunyuan 3D & Tripo3D
- 💬 **Chat** - Groq Llama 3.3 70B
- 🔗 **Website Integration** - Sync with TrappistAI platform

## Commands

- `/start` - Welcome message & auto-register username
- `/link` - Link Telegram account with TrappistAI website
- `/image <prompt>` - Generate FLUX.1 image (1 token)
- `/music` - Music wizard: style → voice → theme → lyrics (10-15 tokens)
- `/pira3d` - 3D generation from image (2-30 tokens)
- `/text <question>` - Free chat with Llama 3.3
- `/balance` - Check token balance
- `/topup` - Recharge tokens

## Tech Stack

- **Bot Framework:** python-telegram-bot 20+
- **AI APIs:** WaveSpeed, Groq
- **Database:** SQLite (local) / PostgreSQL (production)
- **Webhook:** Flask for TrappistAI integration
- **Deployment:** Render (Web Service + Background Worker)

## Deployment

### Render - Web Service (Webhook Handler)
```bash
# Build Command
pip install -r requirements.txt

# Start Command
gunicorn bot_webhook:app --bind 0.0.0.0:$PORT
```

### Render - Background Worker (Bot)
```bash
# Build Command
pip install -r requirements.txt

# Start Command
python bot.py
```

### Environment Variables
```env
BOT_TOKEN=your_telegram_bot_token
WAVESPEED_API_KEY=your_wavespeed_key
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
WEBHOOK_SECRET=your_webhook_secret
DATABASE_URL=postgresql://... (optional, defaults to SQLite)
ADMIN_USERNAME=your_telegram_username
```

## Integration with TrappistAI

1. User runs `/link` in bot
2. Bot stores username → user_id mapping
3. User enters @username on trappisai.netlify.app/profile
4. Backend sends verification code to webhook
5. Bot sends code via Telegram DM
6. User verifies on website
7. ✅ Accounts linked - all generations sync!

## Architecture

```
TrappistAI Website
    ↓
Backend (Render)
    ↓ webhook
PiranAI Webhook (Render Web Service)
    ↓ queries DB
PiranAI Bot (Render Background Worker)
    ↓ sends DM
User receives code in Telegram
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edit .env with your keys

# Run bot locally
python bot.py

# Run webhook locally (separate terminal)
python bot_webhook.py

# Test webhook
python test_webhook.py
```

## License

MIT

## Links

- Bot: [@PiraAi_bot](https://t.me/PiraAi_bot)
- Website: [trappistai.netlify.app](https://trappistai.netlify.app)
- Backend: [trappistai-backend.onrender.com](https://trappistai-backend.onrender.com)
