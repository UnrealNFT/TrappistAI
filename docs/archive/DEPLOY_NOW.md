# 🚀 DÉPLOIEMENT RAPIDE - 10 MINUTES

## ✅ Code poussé: Commit `9acda37`

---

## 🎯 MAINTENANT - 3 Actions sur Render:

### 1️⃣ Créer PiranAI Webhook (Web Service)

**Render Dashboard** → https://dashboard.render.com/

Click **"New +"** → **"Web Service"**

**Configuration:**
```
Name: piranai-webhook
Region: Oregon (US West)
Repo: UnrealNFT/TrappistAI
Branch: main
Root Directory: backend/bot
Runtime: Python 3
Build Command: pip install -r ../requirements.txt
Start Command: gunicorn bot_webhook:app --bind 0.0.0.0:$PORT --workers 2
Instance Type: Free
```

**Environment Variables** (Add these):
```env
BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
WEBHOOK_SECRET=trappistai_piranai_webhook_2026_secure_key
DB_PATH=/tmp/piranai.db
RENDER=true
```

Click **"Create Web Service"** → Wait 2-3 min

**Copy URL:** https://piranai-webhook.onrender.com (exemple)

---

### 2️⃣ Créer PiranAI Bot (Background Worker)

Click **"New +"** → **"Background Worker"**

**Configuration:**
```
Name: piranai-bot
Region: Oregon (US West)
Repo: UnrealNFT/TrappistAI
Branch: main
Root Directory: backend/bot
Runtime: Python 3
Build Command: pip install -r ../requirements.txt
Start Command: python bot.py
Instance Type: Free
```

**Environment Variables:**
```env
BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
WAVESPEED_API_KEY=YOUR_WAVESPEED_API_KEY
GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_MODEL=llama-3.3-70b-versatile
ADMIN_USERNAME=your_telegram_username
DB_PATH=/tmp/piranai.db
```

Click **"Create Background Worker"** → Wait 2-3 min

**Check Logs:** Doit voir "PiranAI Bot started" ✅

---

### 3️⃣ Mettre à jour Backend API (Existing)

Dashboard → **trappistai-backend** → **Environment** tab

**Add these variables:**
```env
PIRANAI_WEBHOOK_URL=https://piranai-webhook.onrender.com/webhook/verification
WEBHOOK_SECRET=trappistai_piranai_webhook_2026_secure_key
```

⚠️ **IMPORTANT:** Replace `piranai-webhook.onrender.com` with YOUR actual webhook URL!

Click **"Save Changes"**

Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## ✅ Vérifications (2 min):

### Webhook Health:
```bash
curl https://piranai-webhook.onrender.com/health
# {"status":"ok","service":"PiranAI Webhook Handler"}
```

### Backend Health:
```bash
curl https://trappistai-backend.onrender.com/health
# {"status":"ok"}
```

### Bot Running:
- Check logs Render → **piranai-bot** → Logs tab
- Should see: `PiranAI Bot started`

### Telegram Test:
1. Open Telegram
2. Search: **@PiranAI_bot**
3. Send: `/start`
4. Send: `/link`
5. Should receive:
```
✅ Compte lié avec succès!

📱 Telegram: @djaf77
🆔 User ID: XXXXXXXXX

🔗 Tu peux maintenant linker ton compte sur:
trappisai.netlify.app/profile
```

---

## 🎉 TEST COMPLET (3 min):

### 1. Site Web:
- Go to: https://trappisai.netlify.app/profile
- Connect wallet (Casper Wallet)
- Enter: `@djaf77` (your Telegram username)
- Click: **"Link Account"**

### 2. Backend Logs:
- Render Dashboard → trappistai-backend → Logs
- Should see:
```
🔐 Verification code for @djaf77: 123456
✅ Sent code to @djaf77 via PiranAI bot
```

### 3. Webhook Logs:
- Render Dashboard → piranai-webhook → Logs
- Should see:
```
📬 Verification request for @djaf77: 123456
✅ Sent verification code to @djaf77 (user_id: XXXXX)
```

### 4. Telegram DM:
- Check @PiranAI_bot chat
- Should receive:
```
Hi @djaf77!

🔐 TrappistAI Verification Code

Your verification code is: 123456

Enter this code on trappisai.netlify.app/profile to link your account.

⏰ Code expires in 10 minutes.
```

### 5. Website:
- Enter code: `123456`
- Click: **"Verify Code"**
- Should see: ✅ **"Account linked successfully!"**

---

## 🐛 Troubleshooting:

### "User not found in database"
❌ **Problem:** You didn't run `/link` in Telegram first

✅ **Fix:** Open @PiranAI_bot → Send `/link` → Try again

### "Invalid secret" (403)
❌ **Problem:** WEBHOOK_SECRET mismatch

✅ **Fix:** Make sure `WEBHOOK_SECRET` is IDENTICAL in:
- piranai-webhook env vars
- trappistai-backend env vars

### "Connection refused"
❌ **Problem:** Webhook not running

✅ **Fix:**
- Check piranai-webhook logs for errors
- Verify URL is correct (no typos)
- Redeploy if needed

### Bot not responding
❌ **Problem:** Bot not running or crashed

✅ **Fix:**
- Check piranai-bot logs
- Verify BOT_TOKEN is correct
- Restart service if needed

---

## 📊 Services Status:

After successful deployment, you should have:

✅ **3 Render Services:**
1. trappistai-backend (Web Service)
2. piranai-webhook (Web Service)
3. piranai-bot (Background Worker)

✅ **All on Free Tier:** $0/month

✅ **All connected:** Backend → Webhook → Bot → Telegram

---

## 🎯 Next Steps:

Once verification works:

1. ✅ Implement generation sync (website → Telegram)
2. ✅ Implement generation sync (Telegram → website)
3. ✅ Gallery page with all generations
4. ✅ Test everything before buildathon deadline

**Let's GO! 🚀**
