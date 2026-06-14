# 🤖 Changement Bot Telegram - Variables à mettre à jour

## 📋 Étapes pour nouveau bot

### 1️⃣ Créer nouveau bot avec @BotFather
```
/newbot
Nom: TrappistAI Bot (ou ton nouveau nom)
Username: TrappistAI_bot (doit finir par _bot)
```

Tu recevras un token comme : `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

---

## 🔧 Variables à changer sur Render

**Backend: `trappistai-backend`**

1. Va sur https://dashboard.render.com/
2. Sélectionne `trappistai-backend`
3. Onglet **Environment**
4. Change cette variable :

```env
BOT_TOKEN=NOUVEAU_TOKEN_ICI
```

**⚠️ IMPORTANT:** Remplace TOUT le token (avant et après les `:`)

---

## 📁 Fichiers locaux à mettre à jour (optionnel)

Si tu veux tester en local, change dans ces fichiers :

### `backend/bot/bot.py` (ligne 39)
```python
BOT_TOKEN = os.getenv("BOT_TOKEN", "TON_NOUVEAU_TOKEN")
```

### `backend/bot/bot_webhook.py` (ligne 20)
```python
BOT_TOKEN = os.getenv("BOT_TOKEN", "TON_NOUVEAU_TOKEN")
```

### `backend/bot/.env.example` (ligne 4)
```env
BOT_TOKEN=TON_NOUVEAU_TOKEN
```

---

## ✅ Vérification

Après avoir changé sur Render :

1. **Render redéploie automatiquement** (~2-3 min)
2. **Teste le bot** en envoyant `/start` sur Telegram
3. **Vérifie les logs Render** pour voir :
   ```
   ✅ Bot initialized: @TrappistAI_bot
   ```

---

## 🎥 Pour la vidéo

**Nom du bot actuel dans le code :**
- Token : `8641629385:AAGibWxAiHRqirqrk9Rawt6FAE_DDVtlTmk`
- Bot : `@PiraAi_bot`

**À mentionner :**
- ✅ Manual Transfer fonctionne (1000 CSPR → 100 crédits)
- 🚧 x402 Auto coming soon
- ✅ Bot Telegram intégré
- ✅ Image/Music/3D generation
- ✅ Community feed

---

## 🚀 Statut actuel

- ✅ x402 mis en "Coming Soon" (commit 2718451)
- ⏳ Attends Netlify redeploy pour voir le badge
- 📝 Prêt pour nouveau BOT_TOKEN quand tu l'auras
