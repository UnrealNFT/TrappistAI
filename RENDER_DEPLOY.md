# 🚀 TrappistAI Render Deployment Guide

## Architecture - 3 Services sur Render:

### 1. **Backend API** (Web Service - Déjà déployé)
- **Type:** Web Service
- **Repo:** UnrealNFT/TrappistAI
- **Root Directory:** backend
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **URL:** https://trappistai-backend.onrender.com

### 2. **PiranAI Webhook** (Web Service - NOUVEAU)
- **Type:** Web Service
- **Repo:** UnrealNFT/TrappistAI
- **Root Directory:** backend/bot
- **Build Command:** `pip install -r ../requirements.txt`
- **Start Command:** `gunicorn bot_webhook:app --bind 0.0.0.0:$PORT --workers 2`
- **URL:** https://piranai-webhook.onrender.com (ou similaire)

### 3. **PiranAI Bot** (Background Worker - NOUVEAU)
- **Type:** Background Worker
- **Repo:** UnrealNFT/TrappistAI
- **Root Directory:** backend/bot
- **Build Command:** `pip install -r ../requirements.txt`
- **Start Command:** `python bot.py`

---

## Environment Variables (Partagées entre services):

### Backend API:
```env
DATABASE_URL=postgresql://...
GROQ_API_KEY=gsk_...
WAVESPEED_API_KEY=5baad7e3...
PIRANAI_WEBHOOK_URL=https://piranai-webhook.onrender.com/webhook/verification
WEBHOOK_SECRET=ton_secret_super_securise
DEBUG=0
```

### PiranAI Webhook:
```env
BOT_TOKEN=8641629385:AAGibWxAiHRqirqrk9Rawt6FAE_DDVtlTmk
WEBHOOK_SECRET=ton_secret_super_securise
DB_PATH=/tmp/piranai.db
DATABASE_URL=postgresql://... (optional - shared with backend)
```

### PiranAI Bot:
```env
BOT_TOKEN=8641629385:AAGibWxAiHRqirqrk9Rawt6FAE_DDVtlTmk
WAVESPEED_API_KEY=5baad7e3...
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
ADMIN_USERNAME=djaf77
DB_PATH=/tmp/piranai.db
DATABASE_URL=postgresql://... (optional - shared with backend)
```

---

## 📋 Étapes de Déploiement:

### 1. Push le code
```bash
cd c:\Users\Djaf\scai\TrappistAI
git add .
git commit -m "feat: Add PiranAI bot integration"
git push origin main
```

### 2. Créer PiranAI Webhook sur Render

1. Dashboard Render → **New Web Service**
2. Connect repository: **UnrealNFT/TrappistAI**
3. Configuration:
   - **Name:** `piranai-webhook`
   - **Region:** Oregon (même que backend)
   - **Branch:** main
   - **Root Directory:** `backend/bot`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r ../requirements.txt`
   - **Start Command:** `gunicorn bot_webhook:app --bind 0.0.0.0:$PORT --workers 2`
   - **Instance Type:** Free
4. Environment Variables: (copier du tableau ci-dessus)
5. **Create Web Service**

### 3. Créer PiranAI Bot sur Render

1. Dashboard Render → **New Background Worker**
2. Connect repository: **UnrealNFT/TrappistAI**
3. Configuration:
   - **Name:** `piranai-bot`
   - **Region:** Oregon
   - **Branch:** main
   - **Root Directory:** `backend/bot`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r ../requirements.txt`
   - **Start Command:** `python bot.py`
   - **Instance Type:** Free
4. Environment Variables: (copier du tableau ci-dessus)
5. **Create Background Worker**

### 4. Mettre à jour Backend API

1. Dashboard → **trappistai-backend** → Environment
2. Ajouter:
   ```env
   PIRANAI_WEBHOOK_URL=https://piranai-webhook.onrender.com/webhook/verification
   WEBHOOK_SECRET=ton_secret_super_securise
   ```
3. **Manual Deploy** → Deploy latest commit

---

## ✅ Vérifications Post-Déploiement:

### Backend API:
```bash
curl https://trappistai-backend.onrender.com/health
# {"status":"ok"}
```

### PiranAI Webhook:
```bash
curl https://piranai-webhook.onrender.com/health
# {"status":"ok","service":"PiranAI Webhook Handler"}
```

### PiranAI Bot:
- Check logs Render → doit voir: `PiranAI Bot started`
- Test Telegram: `/start` dans @PiranAI_bot
- Test `/link` → doit recevoir message de confirmation

### Test Complet:
1. Site: https://trappisai.netlify.app/profile
2. Connect wallet
3. Enter @username (celui du /link)
4. Click "Link Account"
5. **Check Telegram → DM avec code!**
6. Enter code sur site
7. ✅ **Account linked!**

---

## 🔄 Database Migration (PostgreSQL - Optionnel):

Si tu veux un PostgreSQL partagé entre backend et bot:

1. Render Dashboard → Backend → Add PostgreSQL Database
2. Copy `DATABASE_URL`
3. Ajoute à tous les services (Backend + Webhook + Bot)
4. Bot créera automatiquement la table `telegram_usernames`
5. Backend et Bot partageront la même DB → sync parfait!

**Avantages:**
- ✅ Pas de fichier SQLite à gérer
- ✅ Persistence entre redémarrages
- ✅ Données partagées entre services

**Free Tier PostgreSQL sur Render:**
- 90 jours gratuit
- Puis $7/mois
- 1GB storage

---

## 💰 Coût Total Render (Estimation):

- Backend API: **FREE** (Web Service)
- PiranAI Webhook: **FREE** (Web Service)
- PiranAI Bot: **FREE** (Background Worker)
- PostgreSQL: **FREE** (90 jours)

**Total:** $0/mois les 3 premiers mois! 🎉

Après 90 jours:
- Option 1: SQLite (gratuit mais perd data on restart)
- Option 2: PostgreSQL $7/mois (persistence totale)

---

## 🎯 Next Steps After Deploy:

1. ✅ Test verification flow complet
2. ✅ Implement generation sync (website → Telegram)
3. ✅ Implement generation sync (Telegram → website)
4. ✅ Gallery page showing all generations
5. ✅ Smart contract deployment
6. ✅ Documentation buildathon

**On est READY pour la prod!** 🚀
