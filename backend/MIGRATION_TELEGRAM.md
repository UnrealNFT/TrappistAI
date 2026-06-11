# 🔧 Migration Base de Données - Telegram Linking

## ⚠️ PROBLÈME:
```
column "telegram_username" does not exist
```

La base PostgreSQL n'a pas les colonnes pour le linking Telegram!

---

## ✅ SOLUTION RAPIDE (2 minutes):

### **1️⃣ Sur Render Dashboard:**

Va sur: **trappistai-backend** → **Shell** (onglet du haut)

### **2️⃣ Dans le Shell, exécute:**

```bash
# Connexion à PostgreSQL
psql $DATABASE_URL

# Colle ces commandes SQL (ligne par ligne):
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS telegram_user_id BIGINT,
ADD COLUMN IF NOT EXISTS telegram_verified BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_username);

CREATE TABLE IF NOT EXISTS telegram_verification (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(255) NOT NULL,
    telegram_username VARCHAR(255) NOT NULL,
    verification_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telegram_verification_wallet ON telegram_verification(wallet_address);
CREATE INDEX IF NOT EXISTS idx_telegram_verification_code ON telegram_verification(verification_code);

# Vérifie que tout est OK:
\d users

# Tu devrais voir:
# - telegram_username
# - telegram_user_id  
# - telegram_verified

# Quitte psql:
\q
```

---

## ✅ RÉSULTAT ATTENDU:

```
ALTER TABLE
CREATE INDEX
CREATE TABLE
CREATE INDEX
CREATE INDEX
```

---

## 🚀 APRÈS LA MIGRATION:

Le backend fonctionnera directement! Pas besoin de redéployer.

Teste sur le site: **Profile → Link Telegram Account → @Djaf77**

---

## 📝 NOTE:

Le fichier `backend/schema.sql` est maintenant à jour pour les futures installations.
Le fichier `backend/migrations/add_telegram_columns.sql` est la migration complète.
