# Configuration Variables d'Environnement Render

## Problème actuel

Le bot retourne "❌ Erreur lors de la vérification" car **DATABASE_URL n'est pas configuré** dans le service PiraBot.

## Solution : Configurer DATABASE_URL sur Render

### Étape 1 : Obtenir l'URL PostgreSQL

1. Aller sur https://dashboard.render.com
2. Projet **Trappistai**
3. Cliquer sur la **base de données PostgreSQL** : `trappistai`
4. Copier **Internal Connection String** (commence par `postgres://trappistai_user:...`)

**Exemple** :
```
postgres://trappistai_user:KPtom4TkeqRXxr5KieVRIIiVpclq2sq0@dpg-ct7c4pbtq21c738l9760-a/trappistai
```

### Étape 2 : Ajouter à PiraBot

1. Dans Render Dashboard, aller sur le service **PiraBot** (Background Worker)
2. Onglet **Environment**
3. Cliquer **Add Environment Variable**
4. Ajouter :

```
Key: DATABASE_URL
Value: postgres://trappistai_user:KPtom4TkeqRXxr5KieVRIIiVpclq2sq0@dpg-ct7c4pbtq21c738l9760-a/trappistai
```

5. **Save Changes** → Le service redémarre automatiquement

### Étape 3 : Vérifier les autres variables

Assure-toi que **PiraBot** a aussi :

```
BOT_TOKEN=<ton_bot_token>
WAVESPEED_API_KEY=<ta_cle_wavespeed>
GROQ_API_KEY=<ta_cle_groq>
DB_PATH=/tmp/piranai.db
ADMIN_USERNAME=djaf77
```

**Note** : Les clés sont dans le fichier `.env` local (ne jamais les commiter sur GitHub)

## Test après déploiement

1. Attendre 1-2 minutes que le service redémarre
2. Sur Telegram, taper : `/verify 841218` (ou un nouveau code)
3. Le bot devrait maintenant afficher des **logs détaillés** :
   - `🔍 Attempting to verify code...`
   - `✓ Code found: wallet=...`
   - `⏰ Expiration check: ...`
   - `✅ Verified @username...`

## Logs Render

Pour voir les logs en temps réel :

1. Dashboard Render → Service **PiraBot**
2. Onglet **Logs**
3. Les erreurs détaillées s'affichent maintenant avec :
   - Type d'erreur (PostgreSQL / Import / Generic)
   - Message d'erreur complet
   - Traceback Python

## Améliorations apportées

### 1. Gestion d'erreur améliorée
- Messages d'erreur spécifiques envoyés à l'utilisateur
- Logs détaillés pour debug
- Catch séparé pour psycopg2.Error vs ImportError vs Exception

### 2. Gestion timezone
- Fix comparaison `datetime.now()` vs PostgreSQL timestamp (UTC)
- Support timezone-aware datetime objects
- Log des timestamps pour debug

### 3. Dependencies
- Ajout `python-dateutil` pour parser les dates
- Ajout `wavespeed` (manquait)

## Commit

Changements dans :
- `backend/bot/bot.py` : Gestion erreur + timezone
- `backend/bot/requirements.txt` : python-dateutil + wavespeed
