# Migration: Add is_public Column

## Problème résolu

1. ✅ Boutons Save/Share maintenant **permanents** (ne disparaissent plus)
2. ✅ Community feed `/explore` montre les vrais items partagés (pas les listings)
3. ✅ Boutons changent d'état après action: "✅ Saved" / "✅ Shared"

## Migration base de données REQUISE

La colonne `is_public` doit être ajoutée à la table `rwa_tokens`.

### Option 1: Via Render Shell (recommandé)

1. **Aller sur Render Dashboard**: https://dashboard.render.com/
2. **Sélectionner votre service PostgreSQL**: `trappistai-db` (ou nom similaire)
3. **Cliquer "Connect" → "External Connection"**
4. **Copier la commande de connexion** (format: `PGPASSWORD=xxx psql -h xxx -U xxx`)
5. **Ouvrir un terminal local** et coller la commande
6. **Exécuter la migration**:
   ```sql
   -- Add is_public column
   ALTER TABLE rwa_tokens 
   ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;

   -- Create index for performance
   CREATE INDEX IF NOT EXISTS idx_rwa_tokens_is_public 
   ON rwa_tokens(is_public, created_at DESC);

   -- Set existing items to private
   UPDATE rwa_tokens 
   SET is_public = FALSE 
   WHERE is_public IS NULL;
   ```
7. **Vérifier**: `SELECT column_name FROM information_schema.columns WHERE table_name='rwa_tokens' AND column_name='is_public';`

### Option 2: Via TablePlus / DBeaver

1. **Ouvrir votre client SQL préféré**
2. **Se connecter à votre base Render** (credentials dans Render dashboard)
3. **Copier/coller le contenu de** `backend/migrations/add_is_public_column.sql`
4. **Exécuter**

### Option 3: Via fichier SQL

```bash
# Depuis votre machine locale
psql <RENDER_DATABASE_URL> < backend/migrations/add_is_public_column.sql
```

## Vérification

Après migration, vérifier que tout fonctionne :

```sql
-- Voir la structure de la table
\d rwa_tokens

-- Compter les items publics
SELECT COUNT(*) FROM rwa_tokens WHERE is_public = TRUE;

-- Voir les derniers items publics
SELECT token_id, asset_type, prompt, is_public, created_at 
FROM rwa_tokens 
WHERE is_public = TRUE 
ORDER BY created_at DESC 
LIMIT 5;
```

## Redéploiement

Après la migration :

1. **Backend va se redéployer automatiquement** (GitHub push détecté)
2. **Frontend Netlify aussi**
3. **Bot**: Si sur service séparé, il faut le redéployer manuellement

## Test

1. **Telegram**: Générer une image avec `/image test`
2. **Cliquer "📤 Save & Share"** → Item devient public
3. **Aller sur** `https://trappist.land/explore` → Voir l'item dans le feed
4. **Cliquer "💾 Save to Gallery"** → Item privé dans galerie
5. **Vérifier que les boutons restent visibles** ✅

## Troubleshooting

### "column is_public does not exist"
→ Migration pas encore exécutée, suivre les étapes ci-dessus

### "Community feed is empty"
→ Aucun item avec `is_public=TRUE` encore. Partager un item via bot.

### "Buttons disappear after click"
→ Code pas encore redéployé. Attendre fin du déploiement Render (~3-5 min).

### Items de test dans le feed
→ Supprimer manuellement :
```sql
DELETE FROM rwa_tokens WHERE prompt LIKE '%test%' OR prompt LIKE '%fake%';
```

## Rollback (si problème)

```sql
ALTER TABLE rwa_tokens DROP COLUMN IF EXISTS is_public;
DROP INDEX IF EXISTS idx_rwa_tokens_is_public;
```

---

**Status actuel** :
- ✅ Code déployé sur GitHub (commit 3ddcd1d)
- ⏳ Attente: Migration SQL manuelle
- ⏳ Attente: Redéploiement automatique Render/Netlify
