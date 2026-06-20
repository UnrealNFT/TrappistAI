# 🗞️ Crypto News Integration for TrappistAI

## 📋 Vue d'Ensemble

Intégration complète des flux RSS crypto dans TrappistAI pour permettre au bot de répondre aux questions sur l'actualité crypto en temps réel.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CRYPTO NEWS SYSTEM                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐         ┌─────────┐        ┌─────────┐
   │   RSS   │         │  Ollama │        │PostgreSQL│
   │ 20 flux │─────────│  Llama3 │────────│   DB    │
   └─────────┘         └─────────┘        └─────────┘
        │                   │                   │
        │              Résumé/Traduction        │
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  TrappistAI Bot │
                   │  (Telegram)     │
                   └─────────────────┘
```

---

## 🚀 Installation

### 1. Créer la table PostgreSQL

```bash
cd backend
psql -U postgres -d trappistai -f news-schema.sql
```

Ou via Python:
```python
import asyncpg
pool = await asyncpg.create_pool(DATABASE_URL)
async with pool.acquire() as conn:
    await conn.execute(open('news-schema.sql').read())
```

### 2. Installer les dépendances

```bash
pip install feedparser deep-translator python-dateutil asyncpg
```

### 3. Vérifier qu'Ollama fonctionne

```bash
# Tester Ollama
curl http://localhost:11434/api/tags

# Si pas installé:
# Windows: https://ollama.ai/download
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama3.2
ollama pull llama3.2:latest
```

---

## 📡 Lancer le Fetcher RSS

### Option A: Exécution unique (test)

```bash
cd backend
python news-fetcher.py
```

**Output attendu:**
```
🚀 Starting crypto news fetch cycle...
✅ CoinTelegraph: 5 articles
✅ CoinDesk: 5 articles
✅ Decrypt: 4 articles
...
📰 Total articles fetched: 87
✅ Stored: Bitcoin Hits New ATH Amid ETF...
✅ Stored: Ethereum Upgrade Scheduled for...
...
✅ Fetch cycle complete!
   Stored: 45/87 articles
   Time: 234.5s
```

### Option B: Daemon mode (production)

```bash
# Lance le fetcher en boucle (toutes les 5 minutes)
python news-fetcher.py --daemon
```

### Option C: Cron job (recommandé)

```bash
# Editer crontab
crontab -e

# Ajouter cette ligne (fetch toutes les 5 minutes)
*/5 * * * * cd /path/to/TrappistAI/backend && python news-fetcher.py >> /var/log/news-fetcher.log 2>&1
```

### Option D: Systemd service (Linux production)

Créer `/etc/systemd/system/news-fetcher.service`:

```ini
[Unit]
Description=TrappistAI Crypto News Fetcher
After=network.target postgresql.service

[Service]
Type=simple
User=trappistai
WorkingDirectory=/opt/TrappistAI/backend
ExecStart=/usr/bin/python3 news-fetcher.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable news-fetcher
sudo systemctl start news-fetcher
sudo systemctl status news-fetcher
```

---

## 🔍 Tester la Recherche

```bash
cd backend
python news-search.py
```

**Output attendu:**
```
🔍 Search: 'Bitcoin regulation'
  - SEC Approves Bitcoin ETF Applications (relevance: 0.87)
  - New Crypto Regulation Framework in EU (relevance: 0.72)
  - Bitcoin Mining Ban Lifted in Texas (relevance: 0.65)

📰 Recent news (last 24h):
  - Ethereum 2.0 Staking Rewards Hit Record High
  - Binance Faces New Regulatory Challenges
  - DeFi Protocol Exploited for $10M
  ...
```

---

## 🤖 Intégration avec le Bot Telegram

### 1. Ajouter le command handler `/news`

Dans `backend/bot/bot.py`:

```python
from news_search import search_news_fulltext, get_recent_news, format_news_for_chat
from db import get_db_pool

async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get latest crypto news."""
    query = " ".join(context.args) if context.args else ""
    
    pool = await get_db_pool()
    
    if query:
        # Search specific topic
        articles = await search_news_fulltext(query, pool, limit=3)
        response = await format_news_for_chat(articles)
    else:
        # Get recent news
        articles = await get_recent_news(pool, hours=24, limit=5)
        response = await format_news_for_chat(articles)
    
    await update.message.reply_text(response, parse_mode="Markdown", disable_web_page_preview=True)

# Register handler
app.add_handler(CommandHandler("news", cmd_news))
```

**Utilisation:**
```
/news                    → Last 24h news
/news Bitcoin            → Search "Bitcoin"
/news Ethereum DeFi      → Search "Ethereum DeFi"
```

### 2. Intégration avec l'assistant IA (RAG)

Pour que l'IA réponde aux questions avec contexte crypto:

```python
from news_search import get_news_summary_for_ai

async def generate_ai_response(user_message: str, chat_history: list):
    """Generate AI response with crypto news context."""
    
    # Detect if user asks about crypto news
    crypto_keywords = ["bitcoin", "ethereum", "crypto", "blockchain", "defi", "nft"]
    if any(kw in user_message.lower() for kw in crypto_keywords):
        pool = await get_db_pool()
        news_context = await get_news_summary_for_ai(user_message, pool, max_context=3)
        
        # Add news context to LLM prompt
        system_prompt = f"""You are TrappistAI, a crypto expert assistant.

{news_context}

Answer user questions using the recent news context above when relevant.
Always cite sources and provide links when mentioning specific news."""
    else:
        system_prompt = "You are TrappistAI, a helpful AI assistant."
    
    # Call your LLM (Ollama, OpenAI, etc.)
    response = await call_llm(system_prompt, user_message, chat_history)
    return response
```

**Exemple de conversation:**

```
User: "What's happening with Bitcoin lately?"

AI: "Based on recent news:

📰 Bitcoin has reached a new all-time high of $XX,XXX after the SEC approved multiple Bitcoin ETF applications. This is a major milestone for crypto adoption.

Additionally, there's been positive news about Bitcoin mining regulations in Texas, where previous bans have been lifted.

Sources:
- SEC Approves Bitcoin ETF Applications (CoinTelegraph)
- Bitcoin Mining Ban Lifted in Texas (CoinDesk)

Would you like more details on any of these developments?"
```

---

## 🎯 Use Cases

### 1. **Commande `/news` simple**
```
User: /news
Bot: 📰 Latest Crypto News:
     1. Bitcoin Hits New ATH...
     2. Ethereum Upgrade Scheduled...
     3. DeFi Protocol Exploited...
```

### 2. **Recherche par sujet**
```
User: /news Ethereum
Bot: 📰 Latest News on Ethereum:
     1. Ethereum 2.0 Staking...
     2. New EIP Proposal...
```

### 3. **Questions en langage naturel**
```
User: "What's the latest on Bitcoin ETFs?"
AI: "Great question! According to recent news from CoinTelegraph..."
    [Utilise RAG avec get_news_summary_for_ai()]
```

### 4. **Résumé quotidien automatique**
```python
# Scheduled task (daily 9am)
async def send_daily_crypto_summary():
    """Send daily crypto news summary to all users."""
    pool = await get_db_pool()
    articles = await get_recent_news(pool, hours=24, limit=10)
    
    summary = "🌅 Good morning! Here's your daily crypto briefing:\n\n"
    summary += await format_news_for_chat(articles, max_articles=5)
    
    # Send to all subscribed users
    for user in subscribed_users:
        await bot.send_message(user.telegram_id, summary, parse_mode="Markdown")
```

---

## 📊 Monitoring

### Vérifier le nombre d'articles stockés

```sql
-- Total articles
SELECT COUNT(*) FROM crypto_news;

-- Articles par source
SELECT source, COUNT(*) as count 
FROM crypto_news 
GROUP BY source 
ORDER BY count DESC;

-- Articles des dernières 24h
SELECT COUNT(*) FROM crypto_news 
WHERE fetched_at > NOW() - INTERVAL '24 hours';
```

### Logs du fetcher

```bash
# Voir les logs en temps réel
tail -f /var/log/news-fetcher.log

# Vérifier si le daemon tourne
ps aux | grep news-fetcher

# Systemd status
sudo systemctl status news-fetcher
```

---

## 🔧 Configuration Avancée

### Ajuster la fréquence de fetch

Dans `news-fetcher.py`:
```python
# Change interval (default: 5 minutes)
time.sleep(300)  # 300 seconds = 5 minutes
time.sleep(600)  # 10 minutes
time.sleep(1800) # 30 minutes
```

### Filtrer certaines sources

```python
# Dans NEWS_SOURCES, commenter les sources non désirées:
NEWS_SOURCES = [
    # {"name": "CoinTelegraph", ...},  # Désactivé
    {"name": "CoinDesk", ...},         # Actif
]
```

### Nettoyer les vieux articles

```sql
-- Supprimer articles > 30 jours
DELETE FROM crypto_news 
WHERE fetched_at < NOW() - INTERVAL '30 days';

-- Créer un cron job pour nettoyage automatique
-- Ajouter à crontab:
0 2 * * * psql -U postgres -d trappistai -c "DELETE FROM crypto_news WHERE fetched_at < NOW() - INTERVAL '30 days';"
```

---

## 🚨 Troubleshooting

### Problème: Ollama timeout
```
Solution: Augmenter timeout dans news-fetcher.py
response = requests.post(..., timeout=180)  # 3 minutes
```

### Problème: Database connection error
```
Solution: Vérifier DATABASE_URL dans db.py
Tester: psql -U postgres -d trappistai
```

### Problème: RSS feed blocked
```
Solution: Les proxies CORS sont déjà configurés
Si ça persiste, ajouter d'autres proxies dans CORS_PROXIES
```

### Problème: Trop de doublons
```
Solution: Le dedupe est automatique (article_id unique)
Si doublons persistent, vérifier generate_article_id()
```

---

## 📈 Futures Améliorations

1. **Embeddings sémantiques** (GPT, Sentence-BERT)
   ```python
   # Ajouter colonne embedding VECTOR(1536) déjà dans schema
   # Implémenter avec OpenAI ou HuggingFace
   ```

2. **Analyse de sentiment**
   ```python
   # Bullish / Bearish / Neutral
   from textblob import TextBlob
   sentiment = TextBlob(article['summary']).sentiment.polarity
   ```

3. **Détection de tendances**
   ```sql
   -- Top trending topics
   SELECT unnest(hashtags) as tag, COUNT(*) as mentions
   FROM crypto_news
   WHERE fetched_at > NOW() - INTERVAL '24 hours'
   GROUP BY tag
   ORDER BY mentions DESC
   LIMIT 10;
   ```

4. **Notifications push**
   ```python
   # Détecter breaking news et notifier users
   if "breaking" in article['title'].lower():
       await notify_all_users(article)
   ```

---

## ✅ Checklist de Déploiement

- [ ] PostgreSQL table créée (`news-schema.sql`)
- [ ] Ollama installé et Llama3.2 téléchargé
- [ ] Dependencies installées (`feedparser`, `deep-translator`)
- [ ] Test manuel du fetcher (`python news-fetcher.py`)
- [ ] Test de la recherche (`python news-search.py`)
- [ ] Systemd service configuré (ou cron job)
- [ ] Command `/news` ajouté au bot
- [ ] RAG intégré pour questions en langage naturel
- [ ] Monitoring mis en place (logs, database)

---

**🎉 FAIT ! Ton bot peut maintenant répondre aux questions crypto en temps réel ! 🚀**
