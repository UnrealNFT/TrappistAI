# 🚀 DÉPLOIEMENT TRAPPISTAI - GUIDE COMPLET

## ⚡ PRÉPARATION (1min)

Push tout sur GitHub :
```bash
cd C:\Users\Djaf\scai\TrappistAI
git add .
git commit -m "Ready for deployment"
git push origin main
```

---

## 1️⃣ BACKEND SUR RENDER (5min - 100% GRATUIT)

### Étape 1 : Créer le Web Service
1. Va sur **https://render.com**
2. **Sign Up** avec GitHub (gratuit)
3. **Dashboard** → **New +** → **Web Service**
4. **Connect** ton repo GitHub **trappist** (ou le nom exact de ton repo)
5. Autorise Render à accéder au repo

### Étape 2 : Configuration
Remplis les champs :
```
Name: trappistai-backend
Region: Frankfurt (EU) ou Oregon (US)
Branch: main
Root Directory: backend
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Étape 3 : Plan gratuit
1. Scroll en bas
2. Sélectionne **Free** (pas Starter)
3. ⚠️ Free tier = app dort après 15min inactivité (réveil = 30s)

### Étape 4 : Variables d'environnement
Avant de cliquer **Create Web Service**, ajoute :
```
WAVESPEED_API_KEY=ta_clé_wavespeed_ici
CASPER_WALLET_PUBLIC_KEY=ta_clé_publique_casper
CASPER_ACCOUNT_HASH=ton_account_hash
CASPER_RPC_URL=https://rpc.mainnet.casperlabs.io/rpc
ALLOWED_ORIGINS=http://localhost:5173,https://trappistai.netlify.app
```

### Étape 5 : Déployer
1. Clique **Create Web Service**
2. Attends 3-5min (build + deploy)
3. Copie l'URL (ex: `https://trappistai-backend.onrender.com`)
4. ✅ **Backend déployé gratuitement !**

---

## 2️⃣ FRONTEND SUR NETLIFY (3min)

### Étape 1 : Créer le site
1. Va sur **https://app.netlify.com**
2. **Add new site** → **Import an existing project**
3. Connecte GitHub → Sélectionne **trappist** (ton repo)

### Étape 2 : Configuration build
```
Base directory: frontend
Build command: npm run build
Publish directory: dist
```

### Étape 3 : Variable d'environnement
**AVANT DE DÉPLOYER**, ajoute :
```
VITE_API_URL=https://trappistai-backend.onrender.com
```
*(remplace par ton URL Render)*

### Étape 4 : Déployer
1. **Deploy site**
2. Attends 2min (build + deploy)
3. ✅ **Frontend déployé !**

### Étape 5 : Nom de domaine personnalisé
1. **Site settings** → **Domain management**
2. **Change site name** → `trappistai`
3. URL finale : **https://trappistai.netlify.app**

---

## ✅ VÉRIFICATION FINALE

### Teste ton app :
1. Va sur **https://trappistai.netlify.app**
2. Clique **Connect Wallet**
3. ✅ **Casper Wallet se connecte !** (HTTPS obligatoire)
4. Teste une génération d'image

### Si Casper Wallet ne se connecte pas :
- Vérifie que tu es sur HTTPS (pas localhost)
- Vérifie que l'extension Casper Wallet est installée
- Ouvre la console (F12) → cherche les erreurs

---

## 🔧 APRÈS LE DÉPLOIEMENT

### Mettre à jour le backend CORS
Si tu changes le nom du site Netlify, mets à jour Railway :
1. Railway → Variables
2. `ALLOWED_ORIGINS` → ajoute ta nouvelle URL
3. Redeploy

### Logs en temps réel
- **Railway** : Onglet **Logs**
- **Netlify** : Onglet **Deploys** → clic sur un deploy → **Deploy log**

---

## 🚨 TROUBLESHOOTING

### Backend timeout
- Railway free tier = cold start (30s)
- Première requête peut être lente
- Solution : upgrade plan ou garde l'app "awake"

### CORS errors
- Vérifie `ALLOWED_ORIGINS` dans Railway
- Doit contenir l'URL Netlify exacte

### Image generation fails
- Vérifie `WAVESPEED_API_KEY` dans Railway
- Teste avec curl : `curl https://ton-backend.up.railway.app/health`

---

## 💰 COÛTS

- **Render** : 750h/mois gratuit (app dort après 15min, réveil = 30s)
- **Netlify** : 100GB/mois gratuit (largement suffisant)
- **Total** : **0€/mois** 🎉

## 🔥 ALTERNATIVE : VERCEL (frontend + backend serverless)

Si tu veux **0 cold start**, déploie tout sur Vercel :
1. Converti le backend en API Routes serverless
2. Frontend + Backend sur même domaine HTTPS
3. 100% gratuit, 0 sleep
4. Mais : nécessite refactor du code backend

**Recommandation** : Commence avec Render (5min), optimise plus tard si besoin.
