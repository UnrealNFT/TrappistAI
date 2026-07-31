# 🐘 PostgreSQL Setup sur Render - Guide Complet

## ✅ Pourquoi PostgreSQL ?
- ✅ **Persistance garantie** - Les tokens ne disparaissent JAMAIS entre déploiements
- ✅ **Gratuit** sur Render (90 jours)
- ✅ **Professionnel** - Production-ready
- ✅ **Rapide** - Plus performant que SQLite

---

## 📝 Étape 1 : Créer la base PostgreSQL sur Render

1. **Va sur ton Dashboard Render** : https://dashboard.render.com/
2. Clique sur **"New +"** → **"PostgreSQL"**
3. **Remplis le formulaire :**
   - **Name** : `trappistai-db`
   - **Database** : `trappistai` (nom de la DB)
   - **User** : `trappistai_user` (auto-généré)
   - **Region** : `Frankfurt (EU Central)` (choisir le plus proche)
   - **Plan** : **Free** ✅
4. Clique sur **"Create Database"**
5. ⏳ **Attends 1-2 minutes** que la DB soit provisionnée

---

## 🔑 Étape 2 : Copier l'URL de connexion

1. Sur la page de ta nouvelle DB, trouve la section **"Connections"**
2. **Copie l'URL complète** sous **"Internal Database URL"** :
   ```
   postgresql://user:password@dpg-xxxxx.frankfurt-postgres.render.com/trappistai
   ```
   ⚠️ **Copie cette URL COMPLÈTE avec le mot de passe !**

---

## ⚙️ Étape 3 : Configurer le Backend sur Render

1. Va sur ton **Web Service** `trappistai-backend` : https://dashboard.render.com/
2. Clique sur ton service → **Environment** (à gauche)
3. **Ajoute une nouvelle variable :**
   - **Key** : `DATABASE_URL`
   - **Value** : `postgresql://user:password@dpg-xxxxx.frankfurt-postgres.render.com/trappistai`
     *(colle l'URL copiée à l'étape 2)*
4. Clique sur **"Save Changes"**

---

## 🚀 Étape 4 : Redéployer

Le backend va **automatiquement redéployer** après avoir changé les variables d'environnement.

**OU** tu peux forcer un redéploiement :
1. Va dans **Manual Deploy**
2. Clique sur **"Deploy latest commit"**

---

## ✅ Étape 5 : Vérifier que ça marche

1. Va sur les **Logs** de ton backend : https://dashboard.render.com/
2. Cherche ce message :
   ```
   🔧 Initializing database: postgresql://user:***@dpg-xxxxx...
   ✅ PostgreSQL database initialized successfully!
   ```

3. **Teste sur le site** : https://trappisai.netlify.app
   - Connecte ton wallet
   - Achète des tokens
   - **Recharge la page** → Les tokens sont toujours là ! ✅
   - **Git push un changement** → Les tokens sont TOUJOURS là ! 🎉

---

## 🎯 C'est fini !

**Tes tokens vont maintenant persister POUR TOUJOURS** ! 🚀

Même si tu :
- Redéploies le backend
- Changes le code
- Restart le service
- Attends 1 mois

**Les tokens resteront dans PostgreSQL ! ✅**

---

## 🔧 Troubleshooting

### ❌ Erreur "could not connect to server"
→ Vérifie que `DATABASE_URL` dans Render commence bien par `postgresql://`

### ❌ Erreur "password authentication failed"
→ Re-copie l'URL depuis la page de la DB (section "Internal Database URL")

### ❌ Les tokens sont toujours à 0
→ Vérifie les logs du backend pour voir si l'init a marché
→ Assure-toi que `DATABASE_URL` est bien configuré dans Environment

---

## 📊 ScreenerLand utilise aussi PostgreSQL

C'est exactement comme ça que ScreenerLand fait ! Base PostgreSQL persistante. 💪
