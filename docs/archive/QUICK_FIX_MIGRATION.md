# Quick Fix: Run Database Migration NOW

## The Error

```
column "is_public" of relation "rwa_tokens" does not exist
```

## Solution: Connect to Render Database

### Step 1: Get Database URL from Render

1. Go to: https://dashboard.render.com/
2. Click on your **PostgreSQL database** (probably named `trappistai-db` or similar)
3. Scroll to **"Connections"** section
4. Copy the **"External Database URL"** (starts with `postgresql://`)
5. It looks like: `postgresql://user:password@host:port/database`

### Step 2: Run Migration

**Option A - One Command (Fastest)**

Copy this command and replace `<DATABASE_URL>` with your URL from step 1:

```bash
psql "<DATABASE_URL>" -c "ALTER TABLE rwa_tokens ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE; CREATE INDEX IF NOT EXISTS idx_rwa_tokens_is_public ON rwa_tokens(is_public, created_at DESC); UPDATE rwa_tokens SET is_public = FALSE WHERE is_public IS NULL;"
```

**Option B - Interactive (Safer)**

```bash
# 1. Connect to database
psql "<DATABASE_URL>"

# 2. Once connected, run these commands:
ALTER TABLE rwa_tokens ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_rwa_tokens_is_public ON rwa_tokens(is_public, created_at DESC);
UPDATE rwa_tokens SET is_public = FALSE WHERE is_public IS NULL;

# 3. Verify
\d rwa_tokens

# 4. Exit
\q
```

### Step 3: Test

After migration, test on Telegram:
```
/image test
```

Click "📤 Save & Share" → Should work now! ✅

## Don't have psql installed?

### Windows:
```powershell
# Install PostgreSQL client
winget install PostgreSQL.PostgreSQL
```

### Or use Render Web Shell:
1. Render Dashboard → Your Database
2. Click **"Shell"** tab at the top
3. Paste the SQL commands directly there

## Verification Query

```sql
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'rwa_tokens' 
AND column_name = 'is_public';
```

Should return:
```
 column_name | data_type | is_nullable 
-------------+-----------+-------------
 is_public   | boolean   | YES
```

---

**Once this is done, everything will work!** The backend is already deployed with the new code, it's just waiting for the database schema to match.
