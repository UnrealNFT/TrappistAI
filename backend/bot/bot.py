"""
TrappistAI Bot - Full Suno-like flow: Style -> Voice -> Theme -> Lyrics (AI or custom) -> Generate
"""
import asyncio, logging, os, sqlite3, tempfile, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import requests as req
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode
import wavespeed

# Import shared PostgreSQL functions
try:
    from shared_db import (
        store_username_mapping_pg,
        get_wallet_by_telegram_id_pg, 
        get_user_id_by_username_pg,
        get_tokens_pg,
        consume_tokens_pg,
        add_tokens_pg
    )
    print("✅ shared_db.py imported successfully")
except ImportError as e:
    print(f"⚠️ shared_db.py import failed: {e}")
    print("⚠️ Using lambda fallbacks - tokens will NOT work!")
    store_username_mapping_pg = lambda *args: None
    get_user_id_by_username_pg = lambda *args: None
    get_tokens_pg = lambda *args: 0
    consume_tokens_pg = lambda *args: False
    add_tokens_pg = lambda *args: 0

# Import crypto news search functions
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from news_search import search_news_fulltext, get_recent_news, format_news_for_chat, get_news_summary_for_ai
    from db import get_db_pool
    NEWS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ News search not available: {e}")
    NEWS_AVAILABLE = False

# Live on-demand RSS headlines (fallback when the news DB is empty).
# Uses the lightweight live_news module (feedparser only) so it works even if
# the heavy news stack (deep_translator/asyncpg) fails to import.
try:
    from live_news import fetch_live_headlines
    LIVE_NEWS_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Live headlines not available: {e}")
    LIVE_NEWS_AVAILABLE = False

# MP3 → MP4 converter (bundled ffmpeg)
try:
    from mp4_convert import convert_to_mp4
    MP4_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MP4 converter not available: {e}")
    MP4_AVAILABLE = False

# Import real-time crypto prices (CoinGecko, no key needed)
try:
    from prices import (
        format_prices, detect_coins, has_price_intent,
        resolve_context, should_resolve, news_query,
    )
    PRICES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Prices not available: {e}")
    PRICES_AVAILABLE = False

load_dotenv()
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")
WAVESPEED_API_KEY = os.getenv("WAVESPEED_API_KEY", "")
OLLAMA_URL        = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "llama3.2")
GROQ_KEY          = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL        = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")
DB_PATH           = os.getenv("DB_PATH",      "trappistai.db")
DATABASE_URL      = os.getenv("DATABASE_URL", "")  # PostgreSQL connection
BACKEND_API_URL   = os.getenv("BACKEND_API_URL", "https://trappistai-backend.onrender.com")
ADMIN_USERNAME    = os.getenv("ADMIN_USERNAME", "djaf77").lstrip("@").lower()

USE_POSTGRES = bool(DATABASE_URL)  # Use PostgreSQL if configured, else SQLite
print(f"🔧 USE_POSTGRES: {USE_POSTGRES}")
print(f"🔧 DATABASE_URL configured: {'Yes' if DATABASE_URL else 'No (using SQLite)'}")

# ─── Mémoire de conversation ─────────────────────────────────────────────────
_conv_history: dict[int, list] = {}  # user_id → derniers messages
_last_msg: dict[int, float] = {}     # user_id → timestamp dernière requête chat
_last_coins: dict[int, list] = {}    # user_id → dernières cryptos évoquées (pour "prix ?" en suivi)

# ─── Tokenization data storage (avoid callback_data length limit) ────────────
_tokenize_data: dict[str, dict] = {}  # short_id → {type, url, prompt}
_tokenize_counter = 0

# ─── Token DB ────────────────────────────────────────────────────────────────────
_db = sqlite3.connect(DB_PATH, check_same_thread=False)
_db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, tokens INTEGER DEFAULT 0)")
# Store username → user_id mapping for TrappistAI webhook
_db.execute("""
    CREATE TABLE IF NOT EXISTS telegram_usernames (
        username TEXT PRIMARY KEY COLLATE NOCASE,
        user_id INTEGER NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
_db.commit()

def is_new_user(user_id: int) -> bool:
    return _db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone() is None

def get_tokens(user_id: int) -> int:
    """Get token balance - uses PostgreSQL if configured, else SQLite"""
    if USE_POSTGRES:
        return get_tokens_pg(user_id)
    # SQLite fallback
    row = _db.execute("SELECT tokens FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row[0] if row else 0

def add_tokens(user_id: int, amount: int) -> int:
    """Add tokens - uses PostgreSQL if configured, else SQLite"""
    print(f"🔍 add_tokens called: user_id={user_id}, amount={amount}, USE_POSTGRES={USE_POSTGRES}")
    if USE_POSTGRES:
        result = add_tokens_pg(user_id, amount)
        print(f"🔍 add_tokens_pg returned: {result}")
        return result
    # SQLite fallback
    print(f"🔍 Using SQLite fallback for add_tokens")
    _db.execute(
        "INSERT INTO users(user_id, tokens) VALUES(?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET tokens=tokens+?",
        (user_id, amount, amount)
    )
    _db.commit()
    return get_tokens(user_id)

def consume_tokens(user_id: int, amount: int, username: str = "") -> bool:
    """
    Consume tokens - uses PostgreSQL if configured, else SQLite.
    Admin (by username) always passes.
    """
    if USE_POSTGRES:
        is_admin_user = bool(username and username.lstrip("@").lower() == ADMIN_USERNAME)
        return consume_tokens_pg(user_id, amount, ADMIN_USERNAME if is_admin_user else "")
    # SQLite fallback
    if username and username.lstrip("@").lower() == ADMIN_USERNAME:
        return True
    if get_tokens(user_id) < amount:
        return False
    _db.execute("UPDATE users SET tokens=tokens-? WHERE user_id=?", (amount, user_id))
    _db.commit()
    return True

def is_admin(user) -> bool:
    return bool(user.username and user.username.lstrip("@").lower() == ADMIN_USERNAME)

def store_username_mapping(user_id: int, username: str):
    """Store or update username → user_id mapping for webhook lookups"""
    if not username:
        return
    clean_username = username.lstrip("@").lower()
    
    # Store in local SQLite (for bot's own use)
    _db.execute(
        "INSERT OR REPLACE INTO telegram_usernames (username, user_id, updated_at) "
        "VALUES (?, ?, CURRENT_TIMESTAMP)",
        (clean_username, user_id)
    )
    _db.commit()
    
    # ALSO store in PostgreSQL (for webhook access)
    store_username_mapping_pg(user_id, username)

def get_user_id_by_username(username: str) -> int | None:
    """Get user_id from username for TrappistAI webhook"""
    clean_username = username.lstrip("@").lower()
    row = _db.execute(
        "SELECT user_id FROM telegram_usernames WHERE username = ? COLLATE NOCASE",
        (clean_username,)
    ).fetchone()
    return row[0] if row else None

# ─── Tokenization helpers ────────────────────────────────────────────────────

def create_tokenize_keyboard(asset_type: str, url: str, prompt: str) -> InlineKeyboardMarkup:
    """Create save keyboard: private save or public share."""
    global _tokenize_counter
    _tokenize_counter += 1
    short_id = f"t{_tokenize_counter}"
    
    # Store data in memory
    _tokenize_data[short_id] = {
        "type": asset_type,
        "url": url,
        "prompt": prompt
    }
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💾 Save to Gallery (Private)", callback_data=f"save:{short_id}")],
        [InlineKeyboardButton("📤 Save & Share (Public)", callback_data=f"share:{short_id}")],
        [InlineKeyboardButton("❌ Skip", callback_data="skip_save")]
    ])

# (style_key) -> (tags, emoji+label)
# Styles musicaux — tags libres sans BPM/instruments imposés
# Format: (genre_base, emoji_display)
STYLES = {
    "rap":        ("boom bap rap, hip-hop, punchy drums, vinyl texture",   "🎤 Rap"),
    "trap":       ("trap, hard 808 bass, rolling hi-hats, dark, punchy",   "💎 Trap"),
    "drill":      ("uk drill, sliding 808s, aggressive hi-hats, menacing", "🔪 Drill"),
    "pop":        ("modern pop, catchy hook, bright synths, polished",     "🎤 Pop"),
    "rnb":        ("r&b, soul, smooth, silky, warm chords",                "🎵 R&B"),
    "rock":       ("rock, electric guitars, driving drums, energetic",     "🎸 Rock"),
    "jazz":       ("jazz, smooth saxophone, walking bass, swing",          "🎷 Jazz"),
    "metal":      ("heavy metal, distorted guitars, double kick, aggressive", "🤘 Metal"),
    "reggae":     ("reggae, offbeat guitar skank, deep bass, laid-back",   "🌴 Reggae"),
    "folk":       ("folk, acoustic guitar, warm, organic",                 "🎸 Folk"),
    "electronic": ("electronic, edm, punchy synths, driving beat",         "🎛 Electronic"),
    "cyberpunk":  ("cyberpunk, dark synthwave, gritty bass, futuristic",   "🤖 Cyberpunk"),
    "lofi":       ("lofi hip-hop, mellow, dusty drums, chill, warm",       "☕ Lo-Fi"),
    "rai":        ("algerian rai, chaabi, north african melody, derbouka", "🌙 Raï"),
    "afro":       ("afrobeats, percussive groove, bright, danceable",      "🌍 Afrobeat"),
    "gospel":     ("gospel, soulful choir, uplifting organ, spiritual",    "🙏 Gospel"),
    "romantic":   ("romantic ballad, slow, emotional, tender",            "💕 Romantic"),
}

# Conversation states
S_QUALITY, S_STYLE, S_VOICE, S_DESC, S_CHOICE, S_LYRICS_CHOICE, S_OWN, S_PREVIEW, S_EDIT, S_3D_MENU, S_3D_IMAGE, S_3D_QUALITY, S_MP4_MENU, S_MP4_IMAGE, S_MP4_AUDIO = range(15)


# ─── Keyboards ──────────────────────────────────────────────────────────────

def _kb_quality():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("� HeartMuLa — 14 tokens", callback_data="ms_quality:hm")],
        [InlineKeyboardButton("💎 MiniMax 2.5 — 10 tokens", callback_data="ms_quality:hd")],
        [InlineKeyboardButton("❌ Cancel", callback_data="ms_cancel")],
    ])

def _kb_styles():
    rows, items = [], list(STYLES.items())
    for i in range(0, len(items), 3):
        rows.append([
            InlineKeyboardButton(v[1], callback_data=f"ms_style:{k}")
            for k, v in items[i:i+3]
        ])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="ms_cancel")])
    return InlineKeyboardMarkup(rows)

def _kb_voice():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👨 Male", callback_data="ms_voice:male"),
        InlineKeyboardButton("👩 Female",  callback_data="ms_voice:female"),
    ], [InlineKeyboardButton("❌ Cancel", callback_data="ms_cancel")]])

def _kb_mode():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎸 Instrumental", callback_data="ms_choice:instrumental")],
        [InlineKeyboardButton("🎤 With Lyrics", callback_data="ms_choice:lyrics")],
        [InlineKeyboardButton("❌ Cancel", callback_data="ms_cancel")],
    ])

def _kb_lyrics_method():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 AI Lyrics — FREE", callback_data="ms_lyrics:ai")],
        [InlineKeyboardButton("✍️ My Lyrics", callback_data="ms_lyrics:own")],
        [InlineKeyboardButton("❌ Cancel", callback_data="ms_cancel")],
    ])

def _kb_preview():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 Generate",  callback_data="ms_preview:go"),
        InlineKeyboardButton("🔄 Rewrite", callback_data="ms_preview:redo"),
        InlineKeyboardButton("✏️ Edit", callback_data="ms_preview:edit"),
    ], [InlineKeyboardButton("❌ Cancel", callback_data="ms_cancel")]])


# ─── Ollama parolier ─────────────────────────────────────────────────────────

def _detect_lang(text: str) -> str:
    """Return 'fr' if text is mostly French words, else 'en'."""
    fr_words = {"le","la","les","de","du","un","une","des","est","sont","dans","avec",
                "pour","sur","qui","que","ne","pas","je","tu","il","nous","vous","ils",
                "mon","ton","son","ma","ta","sa","mais","ou","et","donc","car","nuit",
                "amour","vie","mort","coeur","feu","sang","roi","guerre","argent"}
    words = set(text.lower().split())
    fr_count = len(words & fr_words)
    return "fr" if fr_count >= 2 else "en"


def _parse_hashtags(text: str):
    """Extract #hashtags as artist/style refs. Returns (clean_text, artists_list)."""
    import re
    artists = re.findall(r'#(\w+)', text)
    clean = re.sub(r'#\w+', '', text).strip()
    return clean, artists


def _ollama_lyrics(style_label: str, voice: str, theme: str) -> str:
    lang = _detect_lang(theme)
    voice_word = "male" if voice == "male" else "female"

    if lang == "en":
        prompt = (
            f"You are a world-class {style_label} songwriter. Write a complete song with strong RHYMES and punchlines.\n"
            f"Voice: {voice_word}. Theme: {theme}\n\n"
            "STRICT RULES:\n"
            "- Structure markers: [Verse], [Chorus], [Bridge] (NO intro/outro tags — start straight on [Verse])\n"
            "- Every [Verse]: 6-8 lines. End-of-line RHYMES mandatory (AABB or ABAB scheme). Punchlines, wordplay, vivid imagery.\n"
            "- Every [Chorus]: 4-6 catchy lines that stick in your head. Strong hook.\n"
            "- [Bridge]: 3-4 lines emotional twist.\n"
            "- Write TWO verses + ONE bridge + chorus repeated.\n"
            "- NEVER write the style/genre/instrument/BPM words inside the lyrics. Sing the SUBJECT, not the style.\n"
            "- NO ad-lib or filler intros: never use 'listen up', 'yeah', 'uh', 'check it', \"y'all\", 'ayy', \"let's go\", 'one two', 'yo'. Start directly with real lyrics.\n"
            "- DO NOT translate to French. Write ENTIRELY in English.\n"
            "- Output ONLY the structure markers and lyrics. NO explanations, NO comments, NO titles.\n\n"
            "Example rhyme style:\n"
            "[Verse]\n"
            "Red candle dropping, world is at war / charts are bleeding out, I can't take no more /\n"
            "WW3 on screen, hawks are in flight / moon was a dream but it vanished by night /\n\n"
            "[Verse]\n...\n[Chorus]\n...\n[Verse]\n...\n[Bridge]\n...\n[Chorus]"
        )
    else:
        detected_lang = _detect_lang(theme)
        prompt = (
            f"You are a genius lyricist in {style_label} style, {'male' if voice == 'male' else 'female'} voice.\n"
            f"Theme: {theme}\n\n"
            "STRICT RULES:\n"
            "- Markers: [Verse], [Chorus], [Bridge] (NO intro/outro tags — start straight on [Verse])\n"
            "- Each [Verse]: 6-8 lines. END rhymes mandatory (AABB or ABAB scheme). Punchlines, wordplay, strong imagery.\n"
            "- Each [Chorus]: 4-6 catchy lines, strong hook that sticks.\n"
            "- [Bridge]: 3-4 lines of emotional break.\n"
            "- Two verses + one bridge + repeated chorus.\n"
            "- NEVER write the style/genre/instrument/BPM words inside the lyrics. Sing the SUBJECT, not the style.\n"
            "- NO ad-lib or filler intros: never use 'listen up', 'yeah', 'uh', 'check it', \"y'all\", 'ayy', \"let's go\", 'one two', 'yo'. Start directly with real lyrics.\n"
            f"- Write ONLY in {detected_lang}.\n"
            "- ONLY markers and lyrics. No comments, no title, no explanations.\n\n"
            "[Verse]\n...\n[Chorus]\n...\n[Verse]\n...\n[Bridge]\n...\n[Chorus]"
        )
    r = req.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["response"].strip()


def _ollama_chat(user_id: int, prompt: str) -> str:
    """Chat gratuit via Ollama local, avec mémoire de conversation."""
    hist = _conv_history.setdefault(user_id, [])
    hist.append({"role": "user", "content": prompt})
    if len(hist) > 14:
        _conv_history[user_id] = hist[-14:]

    today = datetime.now().strftime("%d/%m/%Y")
    system = (
        f"You are TrappistAI, a cool friend, funny, intelligent and natural. "
        f"TODAY IS {today}. When asked about the date or year, you say {today}. "
        "Your training stopped in 2023 but you know we're in 2026. "
        "NEVER say we're in 2023. "
        "You talk like a real human, you love AI, music and crypto. "
        "You remember everything we talked about. "
        "Detect the user's language and always respond in that language."
    )
    # Ollama /api/chat supporte le format messages
    r = req.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}] + _conv_history[user_id],
            "stream": False,
        },
        timeout=120,
    )
    r.raise_for_status()
    answer = r.json()["message"]["content"].strip()
    _conv_history[user_id].append({"role": "assistant", "content": answer})
    return answer

# ─── Groq (primary AI, fast + free) ────────────────────────────────────────────────────────

def _groq_complete(messages: list, max_tokens: int = 1000) -> str:
    import time
    for attempt in range(2):
        r = req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.85, "max_tokens": max_tokens},
            timeout=30,
        )
        if r.status_code == 429 and attempt == 0:
            time.sleep(12)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def _groq_lyrics(style_label: str, voice: str, theme: str, artists: list = None) -> str:
    """Generate lyrics with Groq - CRITICAL separation between STYLE and SUBJECT"""
    voice_word = "male" if voice == "male" else "female"
    artist_line = ""
    if artists:
        names = ", ".join(artists)
        artist_line = (
            f"\n- ARTIST STYLE: channel the flow, delivery, wordplay and energy of: {names}. "
            "Absorb their style deeply — don't just name-drop them, WRITE like them."
        )
    
    system_msg = (
        "You are a world-class songwriter and lyricist. "
        "CRITICAL: Understand the FUNDAMENTAL difference between MUSICAL STYLE and SONG SUBJECT. "
        "STYLE defines HOW you write (flow, rhythm, energy, delivery). "
        "SUBJECT defines WHAT you write about (the content, the topic). "
        "These are COMPLETELY SEPARATE concepts. A trap song can be about ANYTHING (love, dogs, cars, life). "
        "Detect the language of the subject description and write ALL lyrics in that EXACT same language. "
        "ABSOLUTE RULE: NEVER write the name of the musical style, genre, instruments, tempo, BPM or vocal type inside the lyrics themselves. The listener must NEVER hear the style described — sing the SUBJECT, not the style. "
        "NO ad-lib or filler intros: never open with 'listen up', 'yeah', 'uh', 'check it', \"y'all\", 'ayy', \"let's go\", 'one two', 'yo'. Start directly with real, meaningful lyrics. "
        "Write ONLY lyrics with structure markers. NO explanations, NO titles."
    )
    
    user_msg = (
        f"MUSICAL STYLE: {style_label}\n"
        f"(This defines your flow, rhythm, delivery, and energy - NOT the content)\n\n"
        f"VOICE TYPE: {voice_word} vocals\n\n"
        f"SONG SUBJECT: {theme}\n"
        f"(This is WHAT the lyrics talk about - completely independent of style)\n\n"
        "CRITICAL EXAMPLES to avoid confusion:\n"
        "- Style: 'Trap' + Subject: 'black dog, great companion' → Trap FLOW about a loyal dog (NOT a dog rapping)\n"
        "- Style: 'Pop' + Subject: 'broken laptop, frustration' → Catchy pop song about tech problems\n"
        "- Style: 'Drill' + Subject: 'grandmother, warm cookies' → Dark menacing delivery about grandma\n\n"
        "STRICT TECHNICAL REQUIREMENTS:\n"
        f"- NEVER write or sing the style/genre/instrument/BPM/vocal words (e.g. from '{style_label}') inside the lyrics — sing the SUBJECT only\n"
        "- NO ad-lib or filler intros: never open with 'listen up', 'yeah', 'uh', 'check it', \"y'all\", 'ayy', \"let's go\", 'one two', 'yo'. Go straight to real lyrics\n"
        "- Structure markers: [Verse] [Chorus] [Bridge] (NO intro/outro tags — start straight on [Verse])\n"
        "- Every [Verse]: 6-8 lines with MANDATORY end-of-line rhymes (AABB or ABAB scheme)\n"
        "- Every [Chorus]: 4-6 catchy sticky hook lines (repeatable, memorable)\n"
        "- [Bridge]: 3-4 lines (emotional twist or shift in perspective)\n"
        "- TWO verses + chorus repeated + bridge\n"
        f"- Write ENTIRELY in the SAME language as this subject: '{theme}'\n"
        f"- Apply {style_label} style characteristics: flow, wordplay, delivery energy\n"
        f"- Make lyrics about: {theme}\n"
        f"{artist_line}\n"
        "\nNOW WRITE:\n"
    )
    
    return _groq_complete([{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}], max_tokens=1200)


def _groq_chat(user_id: int, prompt: str, news_context: str = None, price_context: str = None) -> str:
    hist = _conv_history.setdefault(user_id, [])
    hist.append({"role": "user", "content": prompt})
    if len(hist) > 14:  # garde 7 échanges
        _conv_history[user_id] = hist[-14:]
    
    # Base system prompt
    system_content = (
        f"Your name is TrappistAI and ONLY TrappistAI - NEVER say another name. Today is {datetime.now().strftime('%d/%m/%Y')}. "
        "You are an official Telegram bot @TrappistAI_bot offering 3 services: generate AI images (/image), "
        "compose real complete songs with instrumental music (/music with HeartMuLa or MiniMax 2.5), "
        "and chat freely with users (what you're doing right now). "
        "You talk naturally, like a friend — cool, funny, direct, casual. "
        "In French, always use 'tu' (tutoiement), never 'vous'. Match the user's vibe and slang. "
        "Keep replies SHORT and punchy (2-4 sentences max unless asked for detail). "
        "VARY your wording — never reuse the same template or the same closing question twice. "
        "You love generative AI, music production, and Casper blockchain (CSPR). "
        "You remember everything we talked about in this conversation. "
        "Your training stopped in 2023 but we're in 2026, NEVER say we're in 2023. "
        "Detect the user's language and always respond in that same language. "
        "If the language is unclear or the message is very short (a single word, a number, or a code), DEFAULT TO ENGLISH. "
        "If asked who you are, answer 'I am TrappistAI' with pride."
    )

    # Add live price context if available (real-time, authoritative)
    if price_context:
        system_content += (
            "\n\n💹 **LIVE MARKET PRICES** (real-time, use these EXACT numbers):\n"
            f"{price_context}\n"
            "Weave the numbers in naturally and briefly. Do NOT robotically repeat that they are 'real-time' "
            "every message — mention it once at most. Never invent a price."
        )

    # Add news context if available
    if news_context:
        system_content += (
            "\n\n📰 **LATEST CRYPTO NEWS** (Use this to answer crypto-related questions):\n"
            f"{news_context}\n\n"
            "IMPORTANT RULES when using news:\n"
            "1. ALWAYS cite the SOURCE NAME (e.g., 'Selon CoinTelegraph', 'D'après The Block', 'According to Decrypt')\n"
            "2. ALWAYS mention it's RECENT news (e.g., 'récemment', 'dernières actualités', 'recently')\n"
            "3. If possible, mention the LINK at the end: 'Source: [link]'\n"
            "4. Use the EXACT information from the articles - don't make up details\n"
            "5. If articles have dates, mention them (e.g., 'le 20 juin', 'published today')\n"
            "Example: 'Selon CoinTelegraph, Bitcoin a récemment franchi les $70K... [summary]. Source: https://...'"
        )
    
    messages = [{"role": "system", "content": system_content}] + _conv_history[user_id]
    answer = _groq_complete(messages, max_tokens=900)
    _conv_history[user_id].append({"role": "assistant", "content": answer})
    return answer


def _ai_lyrics(style_label: str, voice: str, theme: str, artists: list = None) -> str:
    """Try Groq first (fast + free), fallback to Ollama. Strips any style leak from the result."""
    if GROQ_KEY:
        raw = _groq_lyrics(style_label, voice, theme, artists)
    else:
        raw = _ollama_lyrics(style_label, voice, theme)
    return _strip_style_leak(raw, style_label)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_tags(beat: str, voice: str, artists: list = None, instrumental: bool = False) -> str:
    """Build tags from the free-text beat description. The beat IS the style (Suno-custom style)."""
    beat = (beat or "music").strip().rstrip(",").strip()
    
    parts = [beat]
    
    # Voice handling: don't duplicate if the beat already mentions vocals
    if instrumental:
        parts.append("instrumental")
    elif "vocal" not in beat.lower():
        parts.append("male vocals" if voice == "male" else "female vocals")
    
    # Artist inspiration
    if artists:
        parts.append(f"inspired by {', '.join(artists)}")
    
    return ", ".join(parts)

# Curated AUTHENTIC texture/production vocabulary per genre.
# Groq only adds MOOD (emotion) — textures come from here so the genre never drifts.
GENRE_TEXTURES = {
    "trap": "808 slides, hi-hat rolls, triplet flow, deep sub bass, dark ambience, snappy snares",
    "drill": "sliding 808s, sinister piano, aggressive hi-hats, gritty texture, menacing atmosphere",
    "boom bap": "dusty vinyl samples, hard-hitting drums, scratches, deep bass, head-nodding groove",
    "hip hop": "boom bap drums, vinyl samples, deep bass, punchy kicks, head-nodding groove",
    "rock": "distorted electric guitars, driving live drums, power chords, raw energy, anthemic",
    "metal": "heavy distorted riffs, double-kick drums, screaming leads, aggressive, powerful",
    "pop": "catchy hooks, bright synths, punchy drums, polished production, radio-ready shine",
    "lofi": "vinyl crackle, mellow rhodes keys, dusty drums, warm tape saturation, nostalgic haze",
    "lo-fi": "vinyl crackle, mellow rhodes keys, dusty drums, warm tape saturation, nostalgic haze",
    "house": "four-on-the-floor, deep bassline, shimmering pads, groovy swing, club-ready",
    "techno": "hypnotic loops, driving kick, industrial textures, rumbling bass, dark energy",
    "edm": "big drops, sidechain pumping, soaring supersaws, festival energy, euphoric build",
    "rnb": "smooth rhodes, silky vocals, lush chords, sensual groove, warm sub bass",
    "r&b": "smooth rhodes, silky vocals, lush chords, sensual groove, warm sub bass",
    "afrobeat": "syncopated percussion, warm bassline, bright guitars, danceable groove, log drums",
    "afrobeats": "syncopated percussion, warm bassline, bright guitars, danceable groove, log drums",
    "reggaeton": "dembow rhythm, punchy kick, catchy hooks, tropical vibe, bouncy bass",
    "jazz": "swinging brushes, walking upright bass, warm horns, smoky ambience, improvisation",
    "cinematic": "sweeping strings, epic percussion, dramatic swells, orchestral, emotional",
    "orchestral": "sweeping strings, epic brass, timpani hits, dramatic dynamics, grand scale",
    "country": "acoustic guitar, twangy leads, warm vocals, storytelling, foot-stomping rhythm",
    "funk": "slap bass, tight rhythm guitar, punchy horns, groovy pocket, danceable",
    "disco": "four-on-the-floor, funky bassline, lush strings, shimmering hats, feel-good groove",
    "punk": "fast power chords, raw drums, shouted vocals, gritty energy, rebellious",
    "ambient": "evolving pads, airy textures, subtle reverb, spacious, meditative",
    "phonk": "cowbell melodies, distorted 808s, memphis vocals, dark, aggressive bounce",
}


def _genre_texture_pack(base_tags: str) -> str:
    """Return the authentic texture vocabulary for the detected genre (or empty)."""
    low = base_tags.lower()
    # Longest key first so 'boom bap' wins over 'hip hop', etc.
    for key in sorted(GENRE_TEXTURES, key=len, reverse=True):
        if key in low:
            return GENRE_TEXTURES[key]
    return ""


def _groq_enrich_tags(lyrics: str, base_tags: str) -> str:
    """Enrich tags to the max WITHOUT drifting the genre:
    - textures/production come from a curated per-genre vocabulary (authentic)
    - Groq only adds MOOD words (emotion) that fit the lyrics
    Works in production (Groq available; Ollama is not on Render)."""
    parts = [p.strip() for p in base_tags.split(",") if p.strip()]
    seen = {p.lower() for p in parts}

    def _add(chunk: str):
        for w in chunk.split(","):
            w = w.strip()
            if w and w.lower() not in seen:
                parts.append(w)
                seen.add(w.lower())

    # 1) Authentic genre textures (rich vocabulary, no drift)
    _add(_genre_texture_pack(base_tags))

    # 2) Mood words from Groq (emotion only — cannot change the genre)
    if GROQ_KEY:
        try:
            genre = base_tags.split(",")[0].strip()
            system = (
                "You are a music tag assistant. You output ONLY mood/emotion words "
                "(feelings and energy), never genres, instruments, tempo or production terms."
            )
            user = (
                f"Genre: {genre}\n"
                f"Lyrics excerpt:\n{lyrics[:500]}\n\n"
                "Give 3 mood words that match the emotion of these lyrics "
                "(e.g. melancholic, triumphant, euphoric, cold, raw, dreamy, defiant, hopeful). "
                "Output ONE line, comma-separated, 3 words max. No explanation, no quotes."
            )
            out = _groq_complete(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=40,
            )
            out = out.strip().split("\n")[0].strip().strip('"').strip()
            moods = [m.strip() for m in out.split(",") if m.strip() and len(m.strip()) < 20][:3]
            _add(", ".join(moods))
        except Exception as e:
            logger.warning("Groq mood enrichment failed: %s", e)

    return ", ".join(parts)[:300]


def _ollama_enrich_tags(lyrics: str, base_tags: str) -> str:
    """Ollama adds mood + texture/production words to the tags. Genre stays locked."""
    # Extract the genre lock (first 3 tags) so Ollama can't change them
    genre_lock = ", ".join(base_tags.split(",")[:3]).strip()
    prompt = (
        "You are a music producer refining style tags.\n"
        f"GENRE (KEEP EXACTLY, DO NOT CHANGE): {genre_lock}\n"
        f"FULL TAGS: {base_tags}\n"
        f"LYRICS EXCERPT:\n{lyrics[:600]}\n\n"
        "TASK: Read the lyrics and enrich the vibe. Add 2 mood words AND up to 2 texture/production words that fit the feel.\n"
        "STRICT RULES:\n"
        "- Output ONLY: the original FULL TAGS + ', ' + your extra words. Nothing else.\n"
        "- Mood words = emotion/energy (e.g.: melancholic, triumphant, cold, raw, fierce, dreamy, hopeful)\n"
        "- Texture words = sonic feel/production (e.g.: reverb-heavy, lo-fi, cinematic, gritty, spacious, nocturnal, warm, hazy)\n"
        "- DO NOT change or add a GENRE. DO NOT add BPM/tempo. DO NOT add specific instruments.\n"
        "- Max 4 extra words total. DO NOT explain. ONE LINE only. Max 240 characters total."
    )
    try:
        r = req.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        r.raise_for_status()
        result = r.json()["response"].strip().split("\n")[0].strip()
        # Sanity: must start with the genre lock and be reasonable length
        if genre_lock.split(",")[0].strip().lower() in result.lower() and 30 < len(result) < 300:
            return result[:280]
    except Exception as e:
        logger.warning("Ollama tag enrichment failed: %s", e)
    return base_tags


def _format_lyrics(text: str) -> str:
    markers = {"verse","chorus","bridge","intro","outro","intro-short","outro-short",
               "intro-medium","outro-medium","inst-short","inst-medium"}
    if any(f"[{m}" in text.lower() for m in markers):
        return text
    lines = [l.strip() for l in text.splitlines() if l.strip()] or [text.strip()]
    mid = len(lines) // 2 if len(lines) >= 4 else len(lines)
    verse  = "\n".join(lines[:mid])
    chorus = "\n".join(lines[mid:] if len(lines) >= 4 else lines)
    return f"[Verse]\n{verse}\n\n[Chorus]\n{chorus}"


def _strip_style_leak(lyrics: str, beat: str) -> str:
    """Remove short lyric lines that just echo the style/beat descriptors or are cliche ad-lib fillers (anti-leak safety net)."""
    import re
    beat_words = {w.strip(" ,.-").lower() for w in re.split(r"[\s,]+", beat or "") if len(w.strip(" ,.-")) > 2}
    noise = {"bpm", "vocals", "vocal", "beat", "instrumental", "tempo", "melody", "genre", "style"}
    filler_starts = (
        "listen up", "yeah", "uh", "check it", "y'all", "yall", "ayy", "aye",
        "let's go", "lets go", "one two", "1 2", "yo", "woo", "skrrt", "brr", "uh uh",
    )
    out = []
    for line in lyrics.splitlines():
        s = line.strip()
        if not s or s.startswith("["):
            out.append(line)
            continue
        norm = re.sub(r"[^\w' ]", "", s).strip().lower()
        words = [w for w in norm.split() if w]
        if not words:
            out.append(line)
            continue
        # Drop short cliche ad-lib intros (e.g. "Listen up y'all", "Yeah, uh")
        if len(words) <= 5 and norm.startswith(filler_starts):
            continue
        styleish = sum(1 for w in words if w in beat_words or w in noise)
        # Drop only SHORT lines that are mostly style words (a leak, not a real lyric)
        if len(words) <= 6 and styleish / len(words) >= 0.6:
            continue
        out.append(line)
    return "\n".join(out)

async def _generate_and_send(update: Update, context) -> int:
    ud  = context.user_data
    uid = update.effective_user.id
    
    # Determine model and tokens based on quality choice
    quality = ud.get("quality", "hm")  # Default to HeartMuLa if not set
    tokens_needed = 14 if quality == "hm" else 10
    model_name = "HeartMuLa" if quality == "hm" else "MiniMax 2.5 HD"
    
    if not consume_tokens(uid, tokens_needed, update.effective_user.username or ""):
        bal = get_tokens(uid)
        await update.effective_message.reply_text(
            f"❌ *{tokens_needed} tokens required to generate {model_name} song* — Balance: `{bal}` token(s)\n"
            "💰 Use `/topup` to buy more.",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    beat      = ud.get("beat", "music")
    voice     = ud.get("voice", "male")
    artists   = ud.get("artists", [])
    instrumental = ud.get("instrumental", False)
    
    # Build tags with instrumental support
    base_tags = _build_tags(beat, voice, artists, instrumental)
    
    # Format lyrics (empty for instrumental)
    lyrics = "" if instrumental else _format_lyrics(ud["lyrics"])
    
    label     = (beat[:40] + "…") if len(beat) > 40 else beat
    vi        = "👨" if voice == "male" else "👩"
    mode_text = "🎸 Instrumental" if instrumental else f"{vi} With Lyrics"

    # Enrich tags: authentic per-genre textures (+ Groq mood if available).
    # Instrumental keeps the pure preset tags.
    if instrumental:
        tags = base_tags
    else:
        tags = await asyncio.get_event_loop().run_in_executor(
            None, _groq_enrich_tags, lyrics, base_tags
        )

    msg = await update.effective_message.reply_text(
        f"🎵 Composing *{label}* {mode_text} in progress…\n🎸 `{tags}`\n⏳ Generation in progress, may take 10-30 min 🙏",
        parse_mode=ParseMode.MARKDOWN,
    )

    async def _progress():
        steps = [
            (120,  "⏳ 2 min… composing 🎼"),
            (240,  "⏳ 4 min… arranging 🎸"),
            (360,  "⏳ 6 min… mixing 🎚️"),
            (480,  "⏳ 8 min… mastering 🔊"),
            (600,  "⏳ 10 min… finalizing 🎵"),
            (900,  "⏳ 15 min… still working, hang tight 💪"),
            (1200, "⏳ 20 min… almost there… 🔥"),
            (1500, "⏳ 25 min… WaveSpeed is taking its time 😅"),
            (1800, "⏳ 30 min… not giving up, sending it as soon as it's ready 🤞"),
        ]
        last = 0
        for wait, text in steps:
            await asyncio.sleep(wait - last)
            last = wait
            try:
                await msg.edit_text(
                    f"🎵 *{label}* {vi} — {text}\n🎸 `{tags[:120]}…`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass

    progress_task = asyncio.create_task(_progress())
    url = None
    try:
        # Call appropriate generator based on quality
        if quality == "hd":
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_music_minimax, lyrics, tags
            )
        else:
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_music, lyrics, tags
            )
    except wavespeed.TaskTimeout as e:
        # Task still running on WaveSpeed — keep polling up to 40 more minutes
        progress_task.cancel()
        try:
            await msg.edit_text(
                f"⏳ *{label}* {vi} — Long generation, I'll send as soon as ready…\n"
                f"_Task `{e.task_id[:16]}…` still running_",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
        try:
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.fetch_result, e.task_id, 2400
            )
        except Exception as e2:
            logger.error("Music timeout + retry failed: %s", e2)
            await msg.edit_text(
                f"❌ Generation failed after 50 min\n"
                f"🔑 Task ID: `{e.task_id}`\n"
                f"_Contact admin with this code to recover your music_",
                parse_mode=ParseMode.MARKDOWN,
            )
            context.user_data.clear()
            return ConversationHandler.END
    except Exception as e:
        progress_task.cancel()
        logger.error("Music error: %s", e)
        await msg.edit_text(f"❌ Error: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return ConversationHandler.END

    if url:
        progress_task.cancel()

        # Create tokenize keyboard with short callback_data
        keyboard = create_tokenize_keyboard("music", url, label)
        caption = f"🎵 *{label}* {vi}\n🎸 `{tags}`\n\n[Direct link]({url})"

        sent = False
        # 1) Try sending directly by URL (fastest, Telegram fetches it)
        try:
            await update.effective_message.reply_audio(
                audio=url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                title=f"TrappistAI — {label}",
                performer="HeartMuLa x WaveSpeed",
                reply_markup=keyboard,
            )
            sent = True
        except Exception as e1:
            logger.warning("reply_audio by URL failed (%s), downloading and retrying…", e1)
            # 2) Download the file ourselves and send the bytes (bypasses Telegram URL limits)
            try:
                import io
                resp = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: req.get(url, timeout=180)
                )
                resp.raise_for_status()
                buf = io.BytesIO(resp.content)
                buf.name = f"{label[:30] or 'trappistai'}.mp3"
                await update.effective_message.reply_audio(
                    audio=buf,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    title=f"TrappistAI — {label}",
                    performer="HeartMuLa x WaveSpeed",
                    reply_markup=keyboard,
                )
                sent = True
            except Exception as e2:
                logger.error("reply_audio by bytes failed too: %s", e2)

        # 3) Last resort: at least give the user the direct link so nothing is lost
        if not sent:
            try:
                await update.effective_message.reply_text(
                    f"✅ *{label}* {vi} is ready but Telegram couldn't attach the audio.\n"
                    f"👉 Download it here: {url}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                    disable_web_page_preview=False,
                )
            except Exception as e3:
                logger.error("Fallback link message failed: %s", e3)

        # Remove the progress message only after we've delivered (or attempted) the result
        try:
            await msg.delete()
        except Exception:
            pass

        logger.info("Music [%s/%s] %s → %s (sent=%s)", label, voice, update.effective_user.id, url, sent)

    context.user_data.clear()
    return ConversationHandler.END


# ─── Step 1: Style ───────────────────────────────────────────────────────────

async def cmd_music(update: Update, context) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "� *Step 1/4 — Choose your model:*\n\n"
        "🎙 *HeartMuLa* — Great quality/price ratio · 14 tokens\n"
        "💎 *MiniMax 2.5* — High fidelity, humanized voices · 10 tokens",
        reply_markup=_kb_quality(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_QUALITY

async def on_quality_choice(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    quality = q.data.split(":", 1)[1]
    context.user_data["quality"] = quality  # "hm" or "hd"
    
    model_name = "HeartMuLa" if quality == "hm" else "MiniMax 2.5 HD"
    tokens_needed = 14 if quality == "hm" else 10
    await q.edit_message_text(
        f"✅ *{model_name}* selected ({tokens_needed} tokens)\n\n"
        "🥁 *Step 2/4 — Pick a genre* — or *type your own beat*:\n"
        "_(ex: dark trap, egyptian flute, 90 bpm, female vocals)_",
        reply_markup=_kb_styles(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_STYLE

async def on_style(update: Update, context) -> int:
    """Genre preset button tapped — sets the beat from STYLES, then goes to theme."""
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    tags, label = STYLES.get(key, (key, key))
    context.user_data["beat"] = tags
    context.user_data["voice"] = "male"
    context.user_data["instrumental"] = False
    await q.edit_message_text(
        f"✅ Genre: *{label}*\n\n"
        "✍️ *Step 3/3 — What's the song about?*\n"
        "_(ex: bitcoin going up, lost love, night in the city…)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_DESC

async def on_beat(update: Update, context) -> int:
    """Free-text beat/style description (alternative to the genre buttons). Goes to theme."""
    beat = update.message.text.strip()
    context.user_data["beat"] = beat
    # Infer vocal gender from the beat description (defaults to male)
    low = beat.lower()
    if any(w in low for w in ("female", "woman", "girl")):
        context.user_data["voice"] = "female"
    else:
        context.user_data["voice"] = "male"
    context.user_data["instrumental"] = False
    await update.message.reply_text(
        f"✅ Beat: _{beat}_\n\n"
        "✍️ *Step 3/3 — What's the song about?*\n"
        "_(ex: bitcoin going up, lost love, night in the city…)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_DESC


# ─── Step 3: Theme ───────────────────────────────────────────────────────────

async def on_desc(update: Update, context) -> int:
    raw = update.message.text.strip()
    clean_theme, artists = _parse_hashtags(raw)
    context.user_data["theme"] = clean_theme or raw
    context.user_data["artists"] = artists
    
    # Protection: si beat manquant, reset la conversation
    beat = context.user_data.get("beat")
    if not beat:
        await update.message.reply_text(
            "⚠️ Corrupted state detected. Restart /music to begin again.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END
    
    vi = "👨" if context.user_data.get("voice") == "male" else "👩"
    artist_hint = f"\n🎤 Artist style: *{'  '.join('#'+a for a in artists)}*" if artists else ""
    await update.message.reply_text(
        f"✅ _{beat}_ {vi} · _{clean_theme or raw}_{artist_hint}\n\n"
        "� *How do you want the lyrics?*",
        reply_markup=_kb_lyrics_method(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_LYRICS_CHOICE


# ─── Step 4: Lyrics or Instrumental ─────────────────────────────────────────

async def on_choice_lyrics(update: Update, context) -> int:
    """User wants vocals - ask for the song theme, then the lyrics method."""
    q = update.callback_query
    await q.answer()
    context.user_data["instrumental"] = False
    await q.edit_message_text(
        "✍️ *Step 4/4 — What's the song about?*\n"
        "_(ex: bitcoin going up, lost love, night in the city…)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_DESC

async def on_choice_instrumental(update: Update, context) -> int:
    """User wants instrumental only - skip lyrics and generate."""
    q = update.callback_query
    await q.answer()
    context.user_data["instrumental"] = True
    context.user_data["lyrics"] = ""  # Empty lyrics for instrumental
    return await _generate_and_send(update, context)


# ─── Step 5a: Own lyrics ─────────────────────────────────────────────────────

async def on_lyrics_own(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data["instrumental"] = False
    await q.edit_message_text(
        "✍️ *Send your lyrics now:*\n"
        "_(You can use `[Verse]`, `[Chorus]`, `[Bridge]` or free text)_\n"
        "_(or /cancel)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_OWN

async def on_own_lyrics(update: Update, context) -> int:
    context.user_data["lyrics"] = update.message.text.strip()
    return await _generate_and_send(update, context)


# ─── Step 5b: AI lyrics ──────────────────────────────────────────────────────

async def on_lyrics_ai(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    ud = context.user_data
    ud["instrumental"] = False
    label = ud.get("beat", "music")
    vi = "👨" if ud["voice"] == "male" else "👩"
    await q.edit_message_text(
        f"🤖 *AI songwriter is writing…*\n"
        f"Style: *{label}* {vi} · Theme: _{ud.get('theme', '')}_\n"
        "_(~15 seconds)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        lyrics = await asyncio.get_event_loop().run_in_executor(
            None, _ai_lyrics, label, ud["voice"], ud.get("theme", ""), ud.get("artists", [])
        )
        context.user_data["lyrics"] = lyrics
        preview = lyrics[:3500] + ("…" if len(lyrics) > 3500 else "")
        await q.edit_message_text(
            f"📝 *Lyrics generated by AI:*\n\n```\n{preview}\n```\n\n_What do you want to do?_",
            reply_markup=_kb_preview(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return S_PREVIEW
    except Exception as e:
        logger.error("AI lyrics error: %s", e)
        await q.edit_message_text(
            f"❌ AI unavailable: `{str(e)[:120]}`\n\n"
            "✍️ *Send your lyrics manually:*\n_(or /cancel)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return S_OWN


# ─── Step 5: Preview ─────────────────────────────────────────────────────────

async def on_preview(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    action = q.data.split(":", 1)[1]

    if action == "go":
        return await _generate_and_send(update, context)

    if action == "redo":
        ud = context.user_data
        label = ud.get("beat", "music")
        vi = "👨" if ud["voice"] == "male" else "👩"
        await q.edit_message_text(
            f"🔄 *Rewriting in progress…*\nStyle: *{label}* {vi} · Theme: _{ud.get('theme', '')}_",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            lyrics = await asyncio.get_event_loop().run_in_executor(
                None, _ai_lyrics, label, ud["voice"], ud.get("theme", ""), ud.get("artists", [])
            )
            context.user_data["lyrics"] = lyrics
            preview = lyrics[:3500] + ("…" if len(lyrics) > 3500 else "")
            await q.edit_message_text(
                f"📝 *New lyrics:*\n\n```\n{preview}\n```\n\n_What do you want to do?_",
                reply_markup=_kb_preview(),
                parse_mode=ParseMode.MARKDOWN,
            )
            return S_PREVIEW
        except Exception as e:
            await q.edit_message_text(f"❌ AI Error: `{str(e)[:150]}`", parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END

    if action == "edit":
        await q.edit_message_text(
            "✍️ *Send your modified lyrics:*\n_(or /cancel)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return S_EDIT

    return ConversationHandler.END

async def on_edit_lyrics(update: Update, context) -> int:
    context.user_data["lyrics"] = update.message.text.strip()
    return await _generate_and_send(update, context)


# ─── Cancel ──────────────────────────────────────────────────────────────────

async def on_cancel_cb(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("❌ Cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def cmd_cancel(update: Update, context) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ─── /image ──────────────────────────────────────────────────────────────────

async def cmd_image(update: Update, context) -> None:
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text("❌ Use: `/image your prompt`", parse_mode=ParseMode.MARKDOWN)
        return
    uid = update.effective_user.id
    if not consume_tokens(uid, 1, update.effective_user.username or ""):
        bal = get_tokens(uid)
        await update.message.reply_text(
            f"❌ *Insufficient tokens* — Balance: `{bal}` token(s)\n💰 Use `/topup` to buy more.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    msg = await update.message.reply_text("⏳ Generation in progress…")
    try:
        url = await asyncio.get_event_loop().run_in_executor(None, wavespeed.generate_image, prompt)
        try:
            await msg.delete()
        except Exception:
            pass
        
        # Create tokenize keyboard with short callback_data
        keyboard = create_tokenize_keyboard("image", url, prompt)
        
        await update.message.reply_photo(
            photo=url,
            caption=f"🎨 *{prompt[:80]}*\n\n[Direct link]({url})",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        logger.info("Image %s: %s", update.effective_user.id, url)
    except Exception as e:
        logger.error("Image generation error: %s", e)
        try:
            await msg.edit_text(f"❌ Error: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(f"❌ Error: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)


# ─── /trappist3d ─────────────────────────────────────────────────────────────────

async def cmd_trappist3d(update: Update, context) -> int:
    context.user_data.clear()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ From Image", callback_data="3d:image")],
        [InlineKeyboardButton("✍️ From Text (Soon)", callback_data="3d:text_soon")],
        [InlineKeyboardButton("❌ Cancel", callback_data="3d:cancel")],
    ])
    await update.message.reply_text(
        "🎨 *TrappistAI 3D Generator*\n\n"
        "Choose your generation mode:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_3D_MENU


async def on_3d_menu(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    choice = q.data.split(":")[1]
    
    if choice == "cancel":
        await q.edit_message_text("❌ Annulé.")
        context.user_data.clear()
        return ConversationHandler.END
    
    if choice == "text_soon":
        await q.edit_message_text("✍️ Text mode available soon! Use *From Image* for now.", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return ConversationHandler.END
    
    if choice == "image":
        await q.edit_message_text(
            "📷 *Send me your image*\n_(or /cancel)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return S_3D_IMAGE
    
    return S_3D_MENU


async def on_3d_image(update: Update, context) -> int:
    """Store uploaded image and show quality menu."""
    uid = update.effective_user.id
    
    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        await update.message.reply_text("❌ Envoie une image valide ou /cancel")
        return S_3D_IMAGE
    
    # Get and store image URL
    file = await context.bot.get_file(photo.file_id)
    context.user_data['3d_image_url'] = file.file_path
    
    # Show quality menu
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Without texture (20 tokens)", callback_data="3dq:notex")],
        [InlineKeyboardButton("🎨 With texture (30 tokens)", callback_data="3dq:tex")],
        [InlineKeyboardButton("❌ Cancel", callback_data="3dq:cancel")],
    ])
    await update.message.reply_text(
        "🎨 *Choose 3D model quality:*\n\n"
        "⚡ *Without texture* — 20 tokens (~2 min)\n"
        "   └ Pure geometry, monochrome\n\n"
        "🎨 *With texture* — 30 tokens (~5 min)\n"
        "   └ Full colors and textures",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_3D_QUALITY


async def on_3d_quality(update: Update, context) -> int:
    """Generate 3D model based on quality choice."""
    q = update.callback_query
    await q.answer()
    
    uid = update.effective_user.id
    image_url = context.user_data.get('3d_image_url')
    
    if not image_url:
        await q.edit_message_text("❌ Session expired. Use /trappist3d to restart.")
        context.user_data.clear()
        return ConversationHandler.END
    
    choice = q.data.split(":")[1]
    
    if choice == "cancel":
        await q.edit_message_text("❌ Annulé.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Determine model and cost
    if choice == "notex":
        cost = 20
        model_name = "Hunyuan-3D V3.1"
        use_texture = False
    else:  # tex
        cost = 30
        model_name = "Tripo3D v2.5"
        use_texture = True
    
    # Check tokens
    if not consume_tokens(uid, cost, update.effective_user.username or ""):
        bal = get_tokens(uid)
        await q.answer(f"❌ {cost} tokens required (balance: {bal})", show_alert=True)
        return S_3D_QUALITY
    
    try:
        await q.edit_message_text(f"🎨 *3D Generation in progress…*\n_Model: {model_name}_\n⏳ May take up to 10 min", parse_mode=ParseMode.MARKDOWN)
        
        # Generate 3D
        if use_texture:
            glb_url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_3d_with_texture, image_url
            )
        else:
            glb_url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_3d_from_image, image_url
            )
    except wavespeed.TaskTimeout as e:
        # Task still running on WaveSpeed — keep polling up to 20 more minutes
        logger.warning("3D task %s timed out initial poll, continuing...", e.task_id)
        try:
            await q.message.edit_text(
                f"⏳ *Still generating 3D…*\n_Taking longer than expected_\n🕐 Checking again in a moment…",
                parse_mode=ParseMode.MARKDOWN,
            )
            glb_url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.fetch_result, e.task_id, 1200
            )
        except Exception as retry_err:
            logger.error("3D retry failed: %s", retry_err)
            await q.message.edit_text(
                f"❌ *3D generation timed out*\n\n"
                f"⚠️ The model may still be generating on WaveSpeed.\n"
                f"🆔 Task ID: `{e.task_id}`\n\n"
                f"💰 Your {cost} tokens have been refunded.",
                parse_mode=ParseMode.MARKDOWN,
            )
            # Refund tokens on timeout
            _db.execute("UPDATE users SET tokens = tokens + ? WHERE user_id = ?", (cost, uid))
            _db.commit()
            context.user_data.clear()
            return ConversationHandler.END
    except Exception as e:
        logger.error("3D generation error: %s", e)
        await q.message.edit_text(f"❌ Error: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return ConversationHandler.END
    
    # Download GLB file and send
    viewer_url = f"https://trappist.land/viewer3d.html?url={urllib.parse.quote(glb_url)}"
    texture_info = "with texture" if use_texture else "without texture"
    
    # Create save/share keyboard
    keyboard = create_tokenize_keyboard("3d", glb_url, context.user_data.get("3d_prompt", "3D Model"))
    
    try:
        # Download with longer timeout (GLB files can be large)
        glb_data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: req.get(glb_url, timeout=180).content
        )
        
        # Send GLB file
        await q.message.reply_document(
            document=glb_data,
            caption=f"✅ *3D Model generated!* ({texture_info})\n\n"
                    f"📦 Format: GLB\n"
                    f"🎨 Model: {model_name}\n"
                    f"🔗 [View in 3D]({viewer_url})",
            parse_mode=ParseMode.MARKDOWN,
            filename="model3d.glb",
            reply_markup=keyboard,
        )
        logger.info("3D model [%s]: %s (%s)", uid, glb_url, texture_info)
    except Exception as e:
        logger.error("3D file download/send error: %s", e)
        # Fallback: send viewer link even if download failed
        await q.message.reply_text(
            f"✅ *3D Model generated!* ({texture_info})\n\n"
            f"⚠️ File too large to download directly.\n"
            f"🔗 [View in 3D]({viewer_url})\n"
            f"💾 [Direct download]({glb_url})",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        logger.info("3D model [%s]: %s (link only, download failed)", uid, glb_url)
    
    context.user_data.clear()
    return ConversationHandler.END


async def on_3d_cancel(update: Update, context) -> int:
    await update.message.reply_text("❌ 3D Generation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


# ─── /start /help ────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context) -> None:
    uid  = update.effective_user.id
    user = update.effective_user
    
    # Store username mapping for TrappistAI integration
    if user.username:
        store_username_mapping(uid, user.username)
    
    if is_admin(user):
        bonus = "\n\n🔑 *Admin mode active — unlimited access*"
    elif is_new_user(uid):
        _db.execute("INSERT OR IGNORE INTO users(user_id, tokens) VALUES(?,0)", (uid,))
        _db.commit()
        bonus = "\n\n💬 Free chat available — */topup* to generate images/music"
    else:
        bal = get_tokens(uid)
        bonus = f"\n\n💰 Your balance: *{bal} token(s)*"
    await update.message.reply_text(
        "🎨 *TrappistAI* — AI Images & Music\n\n"
        "🖼 */image* `prompt` → FLUX.1 image *(~5s)* — *1 token*\n"
        "🎵 */music* → Complete song *(2-3 min)* — *10 tokens*\n"
        "🧊 */3d* → turn an image into a 3D model — *20 tokens*\n"
        "🎬 */mp4c* → MP3 → MP4 converter *(free)*\n"
        "💬 */text* `question` → Llama 3.3 chat *(free)*\n"
        "💰 */balance* → Check your tokens\n"
        "🔋 */topup* → Buy more tokens"
        f"{bonus}",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_link(update: Update, context) -> None:
    """Link Telegram account with TrappistAI website"""
    user = update.effective_user
    uid = user.id
    username = user.username
    
    if not username:
        await update.message.reply_text(
            "❌ *No Telegram username detected*\n\n"
            "Set up a @username in Telegram Settings to use this feature.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Store mapping
    store_username_mapping(uid, username)
    
    await update.message.reply_text(
        f"✅ *Account linked successfully!*\n\n"
        f"📱 Telegram: @{username}\n"
        f"🆔 User ID: `{uid}`\n\n"
        f"🔗 You can now link your account at:\n"
        f"[trappist.land/profile](https://trappist.land/profile)\n\n"
        f"💡 Enter **@{username}** on the website to receive your verification code here!",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )

async def cmd_verify(update: Update, context) -> None:
    """Verify code from TrappistAI website (user types: /verify 123456)"""
    user = update.effective_user
    uid = user.id
    username = user.username
    
    if not username:
        await update.message.reply_text(
            "❌ *No Telegram username detected*\n\n"
            "Set up a @username in Telegram Settings.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Get code from command args
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ *Incorrect format*\n\n"
            "Usage: `/verify 123456`\n\n"
            "💡 Get your code at trappist.land/profile",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    code = context.args[0].strip()
    
    if len(code) != 6 or not code.isdigit():
        await update.message.reply_text(
            "❌ *Invalid code*\n\n"
            "Code must be 6 digits.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Store username mapping first
    store_username_mapping(uid, username)
    
    # Verify code in PostgreSQL (read-only, no import needed)
    try:
        import psycopg
        import os
        from datetime import datetime
        
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            print("❌ DATABASE_URL not set in environment")
            await update.message.reply_text(
                "❌ *Missing configuration*\n\n"
                "Contact @djaf77 - DATABASE_URL not configured.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        
        print(f"🔍 Attempting to verify code {code} for @{username}")
        
        conn = psycopg.connect(DATABASE_URL)
        try:
            with conn.cursor() as cur:
                # Check if code exists and matches username
                cur.execute("""
                    SELECT wallet_address, telegram_username, expires_at, verified
                    FROM telegram_verification
                    WHERE verification_code = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (code,))
                
                result = cur.fetchone()
                
                if not result:
                    print(f"❌ Code {code} not found in database")
                    await update.message.reply_text(
                        "❌ *Code not found*\n\n"
                        "Make sure you copied the code from the website.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                
                wallet, stored_username, expires_at, verified = result
                print(f"✓ Code found: wallet={wallet[:10]}..., username={stored_username}, verified={verified}")
                
                if verified:
                    await update.message.reply_text(
                        "❌ *Code already used*\n\n"
                        "Generate a new code on the website.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                
                # Handle timezone-aware comparison
                from datetime import timezone
                if isinstance(expires_at, str):
                    from dateutil import parser as dateutil_parser
                    expires_at = dateutil_parser.parse(expires_at)
                
                # Make both datetime objects timezone-aware for comparison
                now = datetime.now(timezone.utc)
                if expires_at.tzinfo is None:
                    # PostgreSQL timestamp is UTC, make it timezone-aware
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                
                print(f"⏰ Expiration check: now={now.isoformat()}, expires={expires_at.isoformat()}")
                
                if now > expires_at:
                    await update.message.reply_text(
                        "❌ *Code expired*\n\n"
                        "Generate a new code on the website (valid for 10 min).",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                
                if stored_username.lower() != username.lower():
                    print(f"❌ Username mismatch: expected {stored_username}, got {username}")
                    await update.message.reply_text(
                        f"❌ *Incorrect username*\n\n"
                        f"This code is for @{stored_username}, but you are @{username}.\n\n"
                        f"Register @{username} on the website first.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                
                # Mark as verified and store telegram_user_id
                cur.execute("""
                    UPDATE telegram_verification
                    SET verified = TRUE
                    WHERE verification_code = %s
                """, (code,))
                
                # Transfer any tokens gifted before linking (placeholder row)
                placeholder_wallet = f"telegram:{uid}"
                cur.execute(
                    "SELECT tokens FROM users WHERE wallet_address = %s",
                    (placeholder_wallet,)
                )
                ph_row = cur.fetchone()
                gifted = ph_row[0] if ph_row else 0
                
                # Also update users table (link telegram + carry over gifted tokens)
                cur.execute("""
                    UPDATE users
                    SET telegram_verified = TRUE, telegram_user_id = %s, tokens = tokens + %s
                    WHERE wallet_address = %s
                """, (uid, gifted, wallet))
                
                # Remove the placeholder so there is only one row per telegram id
                if ph_row is not None:
                    cur.execute(
                        "DELETE FROM users WHERE wallet_address = %s",
                        (placeholder_wallet,)
                    )
                    print(f"🔄 Transferred {gifted} gifted tokens from placeholder to {wallet[:10]}...")
                
                # Get user's token balance
                cur.execute("""
                    SELECT tokens FROM users WHERE wallet_address = %s
                """, (wallet,))
                balance_row = cur.fetchone()
                tokens = balance_row[0] if balance_row else 0
                
                conn.commit()
                
                print(f"✅ Verified @{username} (uid={uid}) for wallet {wallet[:10]}... with code {code} - Balance: {tokens} tokens")
                
                await update.message.reply_text(
                    "✅ *Account verified successfully!*\n\n"
                    f"📱 Telegram: @{username}\n"
                    f"💼 Wallet: `{wallet[:20]}...`\n"
                    f"💰 Balance: *{tokens} token(s)*\n\n"
                    "🎨 Your generations are now synced between website and Telegram!",
                    parse_mode=ParseMode.MARKDOWN,
                )
        finally:
            conn.close()
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        await update.message.reply_text(
            "❌ *Missing module*\n\n"
            f"Error: `{str(e)}`\n\n"
            "Contact @djaf77 - psycopg not installed.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except psycopg.Error as e:
        print(f"❌ PostgreSQL error: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ *Database error*\n\n"
            f"Error: `{str(e)[:100]}`\n\n"
            "Contact @djaf77 if the problem persists.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        print(f"❌ Failed to verify code: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ *Verification error*\n\n"
            f"Error: `{str(e)[:100]}`\n\n"
            "Try again in a few seconds.",
            parse_mode=ParseMode.MARKDOWN,
        )

async def cmd_help(update: Update, context) -> None:
    await update.message.reply_text(
        "📖 *TrappistAI Help*\n\n"
        "🖼 */image* `prompt` — FLUX.1 image **(1 token)**\n"
        "🎵 */music* — wizard style→voice→theme→lyrics **(10 tokens)**\n"
        "🧊 */3d* — turn an image into a 3D model **(20 tokens)**\n"
        "🎬 */mp4c* — MP3 → MP4 converter **(free)**\n"
        "💬 */text* `question` — Llama 3.3 AI chat **(free)**\n"
        "� */news* `[topic]` — latest crypto news **(free)**\n"
        "💰 */balance* — check your balance\n"
        "🔋 */topup* — buy more tokens\n"
        "🔗 */link* — link with TrappistAI website\n\n"
        "⚡ WaveSpeed + HeartMuLa + Groq",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_news(update: Update, context) -> None:
    """Get latest crypto news or search by topic."""
    if not NEWS_AVAILABLE:
        await update.message.reply_text(
            "❌ News feature not available yet.\n"
            "The crypto news database is still loading."
        )
        return
    
    query = " ".join(context.args) if context.args else ""
    
    try:
        pool = await get_db_pool()
        
        if query:
            # Search specific topic
            articles = await search_news_fulltext(query, pool, limit=3)
            if not articles:
                live = None
                if LIVE_NEWS_AVAILABLE:
                    live = await asyncio.get_event_loop().run_in_executor(
                        None, fetch_live_headlines, query, 5)
                if live:
                    await update.message.reply_text(
                        f"🔍 *{query}* — latest headlines:\n\n{live}",
                        parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
                else:
                    await update.message.reply_text(
                        f"🔍 No news found for: *{query}*\n\n"
                        "Try: `/news Bitcoin`, `/news Ethereum`, `/news DeFi`",
                        parse_mode=ParseMode.MARKDOWN)
                return
            response = f"🔍 *Search results for:* {query}\n\n"
            response += await format_news_for_chat(articles, max_articles=3)
        else:
            # Get recent news (last 24 hours)
            articles = await get_recent_news(pool, hours=24, limit=5)
            if not articles:
                live = None
                if LIVE_NEWS_AVAILABLE:
                    live = await asyncio.get_event_loop().run_in_executor(
                        None, fetch_live_headlines, None, 5)
                if live:
                    await update.message.reply_text(
                        f"📰 *Latest Crypto Headlines*\n\n{live}",
                        parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
                else:
                    await update.message.reply_text(
                        "📰 No recent news available yet.\n"
                        "The news fetcher is still collecting articles.")
                return
            response = "📰 *Latest Crypto News (24h)*\n\n"
            response += await format_news_for_chat(articles, max_articles=5)
        
        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text(
            "❌ Error fetching news. Try again later."
        )


async def cmd_about(update: Update, context) -> None:
    await update.message.reply_text(
        "🧠 *AI Stack — TrappistAI*\n\n"
        "🎵 *Music — HeartMuLa*\n"
        "┣ HeartMuLa LLM : *3B params* (Llama 3.2 backbone)\n"
        "┣ HeartCodec : *1.5B params* — audio tokenizer 12.5 Hz\n"
        "┃   → generates long songs without exploding VRAM\n"
        "┣ HeartCLAP : text↔audio alignment\n"
        "┗ HeartTranscriptor : lyrics → tokens\n\n"
        "⚡ Total pipeline ~4-5B params — runs on RTX 3090/4090\n"
        "_(7B internal version in dev — coming soon)_\n\n"
        "🖼 *Image — FLUX.1-schnell*\n"
        "┗ 12B params, 4 steps, distilled by Black Forest Labs\n\n"
        "💬 *Lyrics & Chat — Groq + Llama 3.3 70B*\n"
        "┗ Ultra-fast inference via Groq Cloud (~1s)\n\n"
        "🚀 API Hosting: *WaveSpeed AI*",
        parse_mode=ParseMode.MARKDOWN,
    )

# ─── /balance  /topup  /text ─────────────────────────────────────────────────────────

async def cmd_balance(update: Update, context) -> None:
    uid = update.effective_user.id
    bal = get_tokens(uid)
    await update.message.reply_text(
        f"💰 *Your TrappistAI balance:* `{bal}` token(s)\n\n"
        "🖼 Image = 1 token\n"
        "🎵 Music = 10 tokens\n"
        "💬 Chat = *free* (Ollama local)\n\n"
        "_/topup to buy more_",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_topup(update: Update, context) -> None:
    uid = update.effective_user.id
    bal = get_tokens(uid)
    await update.message.reply_text(
        f"💵 <b>Current balance:</b> {bal} token(s)\n\n"
        "🔋 <b>Buy tokens on the website:</b>\n"
        "👉 https://trappist.land/buy-credits\n\n"
        "Secure crypto payment (CSPR)",
        parse_mode=ParseMode.HTML,
    )


async def cmd_gift(update: Update, context) -> None:
    """Admin command to gift tokens to users. Alias for /admin topup."""
    if not is_admin(update.effective_user):
        await update.message.reply_text("❌ This command is admin-only.")
        return
    
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "🎁 *Gift Tokens Command*\n\n"
            "Usage: `/gift @username AMOUNT`\n"
            "   or: `/gift USER_ID AMOUNT`\n\n"
            "Examples:\n"
            "`/gift @turtlian 50` — gift 50 tokens to @turtlian\n"
            "`/gift 123456 20` — gift 20 tokens to user 123456",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    target_input = args[0]
    try:
        amount = int(args[1])
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive.")
            return
    except ValueError:
        await update.message.reply_text("❌ Amount must be a number.", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Resolve target user (username or user_id)
    if target_input.startswith("@"):
        target_id = get_user_id_by_username(target_input)
        if not target_id:
            await update.message.reply_text(
                f"❌ User `{target_input}` not found.\n\n"
                "💡 Tip: User must have used the bot at least once.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        target_display = target_input
    else:
        try:
            target_id = int(target_input)
            target_display = f"`{target_id}`"
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid format. Use:\n"
                "`/gift @username AMOUNT` or `/gift USER_ID AMOUNT`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Add tokens
    new_bal = add_tokens(target_id, amount)
    
    # Notify admin
    await update.message.reply_text(
        f"✅ *Gift sent!*\n\n"
        f"👤 Recipient: {target_display}\n"
        f"🎁 Amount: *{amount} token(s)*\n"
        f"💰 New balance: *{new_bal} token(s)*",
        parse_mode=ParseMode.MARKDOWN,
    )
    
    # Notify recipient
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🎁 *Gift received!*\n\n"
                 f"You received *{amount} token(s)* from the TrappistAI team!\n\n"
                 f"💰 New balance: *{new_bal} token(s)*\n\n"
                 f"🖼 Try `/image your prompt` to generate AI images\n"
                 f"🎵 Or `/music` to create custom songs!",
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info(f"✅ Notified user {target_id} about gift of {amount} tokens")
    except Exception as e:
        logger.warning(f"⚠️ Could not notify user {target_id}: {e}")
        await update.message.reply_text(
            f"⚠️ Tokens added but could not notify user.\n"
            f"User may have blocked the bot or hasn't started it yet.",
            parse_mode=ParseMode.MARKDOWN
        )


# ─── Tokenize Assets as RWA ──────────────────────────────────────────────────

async def on_save_asset(update: Update, context) -> None:
    """Handle private save to gallery button clicks."""
    q = update.callback_query
    await q.answer()
    
    data = q.data  # Format: "save:{short_id}" or "skip_save"
    
    # Handle skip
    if data == "skip_save":
        try:
            await q.edit_message_reply_markup(reply_markup=None)  # Remove buttons
        except Exception:
            pass
        return
    
    # Extract short_id from callback_data
    parts = data.split(":", 1)
    if len(parts) < 2:
        await q.edit_message_text("❌ Invalid data")
        return
    
    short_id = parts[1]
    
    # Get data from memory
    if short_id not in _tokenize_data:
        await q.edit_message_text("❌ Session expired, regenerate your content")
        return
    
    asset_data = _tokenize_data[short_id]
    uid = update.effective_user.id
    
    # Get user's wallet address
    wallet = get_wallet_by_telegram_id_pg(uid)
    if not wallet:
        # Remove buttons and send new message
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await q.message.reply_text(
            "❌ *Connect your Casper Wallet first*\n\n"
            "👉 Go to https://trappist.land/profile\n"
            "🔗 Connect wallet and link your Telegram\n\n"
            "Then you can save your creations!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Keep buttons but update them to show saved status
    try:
        saved_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Saved to Gallery", callback_data="noop")],
            [InlineKeyboardButton("📤 Save & Share (Public)", callback_data=f"share:{short_id}")],
        ])
        await q.edit_message_reply_markup(reply_markup=saved_keyboard)
    except Exception:
        pass
    
    # Show progress message
    progress_msg = await q.message.reply_text("💾 Saving to your gallery...")
    
    # Call backend mint API with default 100 shares (user can tokenize properly on website later)
    try:
        mint_url = f"{BACKEND_API_URL}/api/rwa/mint"
        mint_payload = {
            "walletAddress": wallet,
            "assetType": asset_data["type"],
            "assetUrl": asset_data["url"],
            "ipfsHash": "",
            "prompt": asset_data["prompt"],
            "model": "ai_generator",
            "telegramUserId": uid,
            "metadata": {},
            "totalShares": 100  # Default for gallery, user can tokenize on website
        }
        
        resp = req.post(mint_url, json=mint_payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get("success"):
            token_id = result.get("tokenId", "?")
            # Update buttons to show both actions done
            try:
                both_saved_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Saved to Gallery", callback_data="noop")],
                    [InlineKeyboardButton("✅ Shared with Community", callback_data="noop")],
                ])
                await q.message.edit_reply_markup(reply_markup=both_saved_keyboard)
            except Exception:
                pass
            
            await progress_msg.edit_text(
                f"✅ *Saved to your private gallery!*\n\n"
                f"📦 Item ID: #{token_id}\n"
                f"🌐 View: https://trappist.land/profile\n\n"
                f"💡 Only you can see this item",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        else:
            await progress_msg.edit_text(f"❌ Save failed: {result.get('message', 'Unknown error')}")
    
    except req.exceptions.Timeout:
        await progress_msg.edit_text("❌ Timeout - backend too slow")
    except req.exceptions.RequestException as e:
        await progress_msg.edit_text(f"❌ Network error: {str(e)}")
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)}")


async def on_share_asset(update: Update, context) -> None:
    """Handle save & share button clicks - save as public item."""
    q = update.callback_query
    await q.answer()
    
    data = q.data  # Format: "share:{short_id}"
    
    # Extract short_id from callback_data
    parts = data.split(":", 1)
    if len(parts) < 2:
        await q.edit_message_text("❌ Invalid data")
        return
    
    short_id = parts[1]
    
    # Get data from memory
    if short_id not in _tokenize_data:
        await q.edit_message_text("❌ Session expired, regenerate your content")
        return
    
    asset_data = _tokenize_data[short_id]
    uid = update.effective_user.id
    
    # Get user's wallet address
    wallet = get_wallet_by_telegram_id_pg(uid)
    if not wallet:
        # Remove buttons and send new message
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await q.message.reply_text(
            "❌ *Connect your Casper Wallet first*\n\n"
            "👉 Go to https://trappist.land/profile\n"
            "🔗 Connect wallet and link your Telegram\n\n"
            "Then you can share your creations!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Update buttons to show sharing in progress
    try:
        sharing_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Save to Gallery (Private)", callback_data=f"save:{short_id}")],
            [InlineKeyboardButton("⏳ Sharing...", callback_data="noop")],
        ])
        await q.edit_message_reply_markup(reply_markup=sharing_keyboard)
    except Exception:
        pass
    
    # Show progress message
    progress_msg = await q.message.reply_text("📤 Saving & sharing to community...")
    
    # Call backend share API
    try:
        share_url = f"{BACKEND_API_URL}/api/share"
        share_payload = {
            "walletAddress": wallet,
            "assetType": asset_data["type"],
            "assetUrl": asset_data["url"],
            "prompt": asset_data["prompt"],
            "telegramUserId": uid,
            "isPublic": True  # Share publicly
        }
        
        resp = req.post(share_url, json=share_payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get("success"):
            item_id = result.get("tokenId", "?")
            
            # Update buttons to show both actions available
            try:
                shared_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💾 Also Save Private", callback_data=f"save:{short_id}")],
                    [InlineKeyboardButton("✅ Shared with Community", callback_data="noop")],
                ])
                await q.message.edit_reply_markup(reply_markup=shared_keyboard)
            except Exception:
                pass
            
            await progress_msg.edit_text(
                f"✅ *Saved and shared with community!*\n\n"
                f"📦 Item ID: #{item_id}\n"
                f"🌐 View in feed: https://trappist.land/explore\n\n"
                f"💡 Everyone can see this creation now!",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        else:
            await progress_msg.edit_text(f"❌ Share failed: {result.get('message', 'Unknown error')}")
    
    except req.exceptions.Timeout:
        await progress_msg.edit_text("❌ Timeout - backend too slow")
    except req.exceptions.RequestException as e:
        await progress_msg.edit_text(f"❌ Network error: {str(e)}")
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)}")


async def cmd_text(update: Update, context) -> None:
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text("💬 Send me your message directly, no need for /text !", parse_mode=ParseMode.MARKDOWN)
        return
    msg = await update.message.reply_text("💬 Thinking…")
    try:
        answer = await asyncio.get_event_loop().run_in_executor(None, _groq_chat, update.effective_user.id, prompt)
        await msg.edit_text(f"🤖 {answer[:4000]}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)


async def on_free_message(update: Update, context) -> None:
    """Chat libre gratuit via Groq avec RAG automatique des crypto news."""
    if not update.message or not update.message.text:
        return
    uid = update.effective_user.id
    now = asyncio.get_event_loop().time()
    if now - _last_msg.get(uid, 0) < 4:
        return  # anti-spam: ignore si < 4s depuis dernier message
    _last_msg[uid] = now
    prompt = update.message.text.strip()

    # Detect bare verification code (6 digits typed without /verify)
    if prompt.isdigit() and len(prompt) == 6:
        await update.message.reply_text(
            "🔑 *That looks like a verification code!*\n\n"
            f"To verify your account, use:\n`/verify {prompt}`\n\n"
            "💡 Get your code at trappist.land/profile",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    msg = await update.message.reply_text("💬 Thinking…")

    prompt_lower = prompt.lower()
    # Generic "latest news" style request (no specific coin needed)
    generic_news = any(k in prompt_lower for k in (
        "news", "actu", "nouvelles", "quoi de neuf", "latest", "headlines",
        "derniere", "dernière", "actus",
    ))

    # Automatic news context injection for crypto-related questions
    news_context = None

    # Live price context (real-time, CoinGecko) — independent of the news DB
    price_context = None
    turn_ids = []  # coin ids referenced this turn (shared with news search)
    if PRICES_AVAILABLE:
        try:
            coins = detect_coins(prompt)
            if coins:
                # Known coin(s) named directly
                turn_ids = coins
                _last_coins[uid] = coins
                price_context = await asyncio.get_event_loop().run_in_executor(
                    None, format_prices, coins
                )
            elif has_price_intent(prompt) and _last_coins.get(uid):
                # Follow-up like "prix ?" → reuse the last coin discussed
                turn_ids = _last_coins[uid]
                price_context = await asyncio.get_event_loop().run_in_executor(
                    None, format_prices, turn_ids
                )
            elif should_resolve(prompt) and not generic_news:
                # Unknown coin (e.g. EGLD) → dynamic search CoinGecko + DexScreener.
                # Skipped for generic news questions to avoid resolving junk tokens.
                price_context, ids = await asyncio.get_event_loop().run_in_executor(
                    None, resolve_context, prompt
                )
                if ids:
                    turn_ids = ids
                    _last_coins[uid] = ids
            if price_context:
                logger.info("💰 Injected live price context")
        except Exception as e:
            logger.error("❌ Could not fetch price context: %s", e)
    
    logger.info(f"📝 User {uid} message: {prompt[:50]}")
    logger.info(f"🔍 NEWS_AVAILABLE: {NEWS_AVAILABLE}")
    
    if NEWS_AVAILABLE or LIVE_NEWS_AVAILABLE:
        # Clean keyword: coin name if a coin was referenced this turn.
        # NEVER pass the raw sentence (French words poison plainto_tsquery → 0 matches).
        news_q = news_query(prompt, turn_ids) if turn_ids else None

        if news_q or generic_news:
            # 1) Try the news DB (populated by the fetcher worker)
            if NEWS_AVAILABLE:
                try:
                    pool = await get_db_pool()
                    if news_q:
                        logger.info(f"📡 News search keyword: {news_q!r}")
                        news_context = await get_news_summary_for_ai(news_q, pool, max_context=3)
                    if not news_context and generic_news:
                        recent = await get_recent_news(pool, hours=48, limit=5)
                        if recent:
                            news_context = await format_news_for_chat(recent, max_articles=5)
                except Exception as e:
                    logger.error(f"❌ DB news fetch failed: {e}", exc_info=True)

            # 2) Fallback: live RSS headlines (no DB) if the DB returned nothing
            if not news_context and LIVE_NEWS_AVAILABLE:
                try:
                    news_context = await asyncio.get_event_loop().run_in_executor(
                        None, fetch_live_headlines, news_q, 5
                    )
                    if news_context:
                        logger.info("📰 Injected LIVE RSS headlines (DB fallback)")
                except Exception as e:
                    logger.error(f"❌ Live headlines failed: {e}")

            if news_context:
                logger.info(f"✅ News context injected ({len(news_context)} chars)")
            else:
                logger.warning("⚠️ No news found (DB + live)")
    else:
        logger.warning("⚠️ News search not available (import failed)")
    
    try:
        answer = await asyncio.get_event_loop().run_in_executor(
            None, _groq_chat, uid, prompt, news_context, price_context
        )
        await msg.edit_text(f"🤖 {answer[:4000]}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_myid(update: Update, context) -> None:
    uid = update.effective_user.id
    uname = update.effective_user.username or "?"
    await update.message.reply_text(
        f"🔑 Your Telegram ID: `{uid}`\n👤 Username: @{uname}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_admin(update: Update, context) -> None:
    if not is_admin(update.effective_user):
        await update.message.reply_text("❌ Access denied.")
        return
    args = context.args
    # /admin topup <user_id|@username> <amount>
    if len(args) == 3 and args[0] == "topup":
        target_input = args[1]
        try:
            amount = int(args[2])
        except ValueError:
            await update.message.reply_text("Use: `/admin topup USER_ID|@USERNAME AMOUNT`", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Resolve target user (username or user_id)
        if target_input.startswith("@"):
            target_id = get_user_id_by_username(target_input)
            if not target_id:
                await update.message.reply_text(f"❌ User `{target_input}` not found in database.", parse_mode=ParseMode.MARKDOWN)
                return
            target_display = target_input
        else:
            try:
                target_id = int(target_input)
                target_display = f"`{target_id}`"
            except ValueError:
                await update.message.reply_text("Use: `/admin topup USER_ID|@USERNAME AMOUNT`", parse_mode=ParseMode.MARKDOWN)
                return
        
        new_bal = add_tokens(target_id, amount)
        
        # Notify admin
        await update.message.reply_text(
            f"✅ +{amount} tokens for {target_display} — new balance: *{new_bal}*",
            parse_mode=ParseMode.MARKDOWN,
        )
        
        # Notify recipient
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎁 *Gift received!*\n\n"
                     f"You received *{amount} token(s)* from the TrappistAI team!\n\n"
                     f"💰 New balance: *{new_bal} token(s)*\n\n"
                     f"Use `/image` to generate images or `/music` to create songs!",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.warning(f"Could not notify user {target_id}: {e}")
    # /admin balance <user_id>
    elif len(args) == 2 and args[0] == "balance":
        try:
            target_id = int(args[1])
        except ValueError:
            await update.message.reply_text("Use: `/admin balance USER_ID`", parse_mode=ParseMode.MARKDOWN)
            return
        bal = get_tokens(target_id)
        await update.message.reply_text(f"`{target_id}` : *{bal} token(s)*", parse_mode=ParseMode.MARKDOWN)
    # /admin fetch <task_id> <user_id>
    elif len(args) == 3 and args[0] == "fetch":
        task_id   = args[1]
        try:
            target_id = int(args[2])
        except ValueError:
            await update.message.reply_text("Use: `/admin fetch TASK_ID USER_ID`", parse_mode=ParseMode.MARKDOWN)
            return
        await update.message.reply_text(f"⏳ Poll task `{task_id[:16]}…` en cours (max 5 min)...", parse_mode=ParseMode.MARKDOWN)
        try:
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.fetch_result, task_id, 300
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Task not ready or failed: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            await context.bot.send_audio(
                chat_id=target_id,
                audio=url,
                caption=f"🎵 Your song is ready!\n[Direct link]({url})",
                parse_mode=ParseMode.MARKDOWN,
                performer="HeartMuLa x WaveSpeed",
            )
            await update.message.reply_text(f"✅ Envoyé à `{target_id}`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Send failed: `{str(e)[:200]}`\nURL: {url}", parse_mode=ParseMode.MARKDOWN)
    # /admin list
    elif len(args) == 1 and args[0] == "list":
        rows = _db.execute("SELECT user_id, tokens FROM users ORDER BY tokens DESC LIMIT 20").fetchall()
        if not rows:
            await update.message.reply_text("Empty DB.")
            return
        lines = "\n".join(f"`{r[0]}` : {r[1]} tokens" for r in rows)
        await update.message.reply_text(f"📊 *Users (top 20):*\n{lines}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            "*Admin commands:*\n"
            "`/admin topup USER_ID|@USERNAME AMOUNT`\n"
            "`/admin balance USER_ID`\n"
            "`/admin list`\n"
            "`/admin fetch TASK_ID USER_ID`\n\n"
            "*Quick alias:*\n"
            "`/gift @username AMOUNT` — gift tokens to user",
            parse_mode=ParseMode.MARKDOWN,
        )


# ─── Main ────────────────────────────────────────────────────────────────────

async def error_handler(update: object, context) -> None:
    """Log errors and reset corrupted conversation state."""
    logger.error(f"Error: {context.error}", exc_info=context.error)
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ *Internal error detected*\n"
                "Your conversation state has been reset.\n"
                "Please restart your command (/music, /pira3d, etc.)",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

# ─── MP4 Converter (/mp4c) ───────────────────────────────────────────────────

async def _post_init(app):
    """Register the command suggestion menu shown when typing '/' in Telegram."""
    await app.bot.set_my_commands([
        BotCommand("start", "Welcome & menu"),
        BotCommand("image", "Generate an AI image (FLUX.1)"),
        BotCommand("music", "Compose a full song"),
        BotCommand("3d", "Turn an image into a 3D model"),
        BotCommand("mp4c", "Convert MP3 to MP4"),
        BotCommand("text", "Chat with the AI"),
        BotCommand("news", "Latest crypto news"),
        BotCommand("balance", "Check your token balance"),
        BotCommand("topup", "Buy more tokens"),
        BotCommand("link", "Link the TrappistAI website"),
        BotCommand("help", "Show help"),
        BotCommand("cancel", "Cancel the current action"),
    ])


def _kb_mp4_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 With image", callback_data="mp4:image")],
        [InlineKeyboardButton("🎵 Audio only (black background)", callback_data="mp4:audio")],
        [InlineKeyboardButton("❌ Cancel", callback_data="mp4:cancel")],
    ])


async def cmd_mp4c(update: Update, context) -> int:
    """Start the MP3 → MP4 converter flow."""
    if not MP4_AVAILABLE:
        await update.message.reply_text("❌ MP4 converter is temporarily unavailable.")
        return ConversationHandler.END
    context.user_data["mp4_image_path"] = None
    await update.message.reply_text(
        "🎬 *MP3 → MP4 Converter*\n\n"
        "Do you want a cover image?",
        reply_markup=_kb_mp4_menu(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_MP4_MENU


async def on_mp4_menu(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    choice = q.data.split(":", 1)[1]
    if choice == "cancel":
        await q.edit_message_text("❌ Cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    if choice == "image":
        await q.edit_message_text(
            "🖼 *Send me the cover image* (photo or image file)\n_(or /cancel)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return S_MP4_IMAGE
    await q.edit_message_text(
        "🎵 *Send me the MP3* (audio or file)\n_(or /cancel)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_MP4_AUDIO


async def on_mp4_image(update: Update, context) -> int:
    msg = update.message
    file_id = None
    if msg.photo:
        file_id = msg.photo[-1].file_id
    elif msg.document and (msg.document.mime_type or "").startswith("image"):
        file_id = msg.document.file_id
    if not file_id:
        await msg.reply_text("❌ Send a valid image (photo or image file), or /cancel")
        return S_MP4_IMAGE
    f = await context.bot.get_file(file_id)
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    await f.download_to_drive(path)
    context.user_data["mp4_image_path"] = path
    await msg.reply_text(
        "✅ Image received.\n\n🎵 *Now send me the MP3* (audio or file)\n_(or /cancel)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_MP4_AUDIO


async def on_mp4_audio(update: Update, context) -> int:
    msg = update.message
    file_id = None
    fname = "audio.mp3"
    if msg.audio:
        file_id = msg.audio.file_id
        fname = msg.audio.file_name or fname
    elif msg.voice:
        file_id = msg.voice.file_id
    elif msg.document and (
        (msg.document.mime_type or "").startswith("audio")
        or (msg.document.file_name or "").lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac"))
    ):
        file_id = msg.document.file_id
        fname = msg.document.file_name or fname
    if not file_id:
        await msg.reply_text("❌ Send a valid audio file (MP3), or /cancel")
        return S_MP4_AUDIO

    status = await msg.reply_text("🎬 Converting to MP4… ⏳")
    image_path = context.user_data.get("mp4_image_path")
    audio_path = out_path = None
    try:
        f = await context.bot.get_file(file_id)
        ext = os.path.splitext(fname)[1] or ".mp3"
        fd, audio_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        await f.download_to_drive(audio_path)

        out_path = await asyncio.get_event_loop().run_in_executor(
            None, convert_to_mp4, audio_path, image_path, None
        )
        with open(out_path, "rb") as vid:
            await msg.reply_video(vid, caption="✅ Here is your MP4!", supports_streaming=True)
        try:
            await status.delete()
        except Exception:
            pass
    except Exception as e:
        await status.edit_text(f"❌ Conversion failed: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
    finally:
        for p in (image_path, audio_path, out_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        context.user_data.clear()
    return ConversationHandler.END


async def on_mp4_cancel(update: Update, context) -> int:
    p = context.user_data.get("mp4_image_path")
    if p and os.path.exists(p):
        try:
            os.remove(p)
        except Exception:
            pass
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


def main():
    if not WAVESPEED_API_KEY:
        logger.error("WAVESPEED_API_KEY not set!")
        return

    # Thread pool : 1 thread par génération audio simultanée possible (50 = 50 users en parallèle)
    executor = ThreadPoolExecutor(max_workers=50, thread_name_prefix="trappistai")
    
    # Fix for Python 3.10+ - create event loop explicitly
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.set_default_executor(executor)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)   # each user processed in parallel, no queue
        .post_init(_post_init)      # register the "/" command suggestion menu
        .build()
    )
    
    # Global error handler
    app.add_error_handler(error_handler)

    conv = ConversationHandler(
        entry_points=[CommandHandler("music", cmd_music)],
        states={
            S_QUALITY: [CallbackQueryHandler(on_quality_choice, pattern=r"^ms_quality:"),
                        CallbackQueryHandler(on_cancel_cb,  pattern=r"^ms_cancel$")],
            S_STYLE:   [CallbackQueryHandler(on_style,      pattern=r"^ms_style:"),
                        CallbackQueryHandler(on_cancel_cb,  pattern=r"^ms_cancel$"),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, on_beat),
                        CommandHandler("cancel", cmd_cancel)],
            S_DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, on_desc),
                        CommandHandler("cancel", cmd_cancel)],
            S_LYRICS_CHOICE: [CallbackQueryHandler(on_lyrics_own, pattern=r"^ms_lyrics:own$"),
                        CallbackQueryHandler(on_lyrics_ai,  pattern=r"^ms_lyrics:ai$"),
                        CallbackQueryHandler(on_cancel_cb,  pattern=r"^ms_cancel$")],
            S_OWN:     [MessageHandler(filters.TEXT & ~filters.COMMAND, on_own_lyrics),
                        CommandHandler("cancel", cmd_cancel)],
            S_PREVIEW: [CallbackQueryHandler(on_preview,    pattern=r"^ms_preview:"),
                        CallbackQueryHandler(on_cancel_cb,  pattern=r"^ms_cancel$")],
            S_EDIT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, on_edit_lyrics),
                        CommandHandler("cancel", cmd_cancel)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)

    conv_3d = ConversationHandler(
        entry_points=[CommandHandler("3d", cmd_trappist3d),
                      CommandHandler("trappist3d", cmd_trappist3d)],
        states={
            S_3D_MENU: [CallbackQueryHandler(on_3d_menu, pattern=r"^3d:")],
            S_3D_IMAGE: [MessageHandler(filters.PHOTO, on_3d_image),
                         CommandHandler("cancel", on_3d_cancel)],
            S_3D_QUALITY: [CallbackQueryHandler(on_3d_quality, pattern=r"^3dq:")],
        },
        fallbacks=[CommandHandler("cancel", on_3d_cancel)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(conv_3d)

    conv_mp4 = ConversationHandler(
        entry_points=[CommandHandler("mp4c", cmd_mp4c)],
        states={
            S_MP4_MENU: [CallbackQueryHandler(on_mp4_menu, pattern=r"^mp4:")],
            S_MP4_IMAGE: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_mp4_image),
                          CommandHandler("cancel", on_mp4_cancel)],
            S_MP4_AUDIO: [MessageHandler(
                              filters.AUDIO | filters.VOICE | filters.Document.AUDIO | filters.Document.ALL,
                              on_mp4_audio),
                          CommandHandler("cancel", on_mp4_cancel)],
        },
        fallbacks=[CommandHandler("cancel", on_mp4_cancel)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(conv_mp4)

    # Save/Share gallery callbacks (must be before other handlers to avoid conflicts)
    app.add_handler(CallbackQueryHandler(on_save_asset, pattern=r"^save:"))
    app.add_handler(CallbackQueryHandler(on_share_asset, pattern=r"^share:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.edit_message_reply_markup(reply_markup=None), pattern=r"^skip_save$"))
    # Handle noop callbacks (disabled buttons)
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer("✅"), pattern=r"^noop$"))

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("link",    cmd_link))
    app.add_handler(CommandHandler("verify",  cmd_verify))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("news",    cmd_news))
    app.add_handler(CommandHandler("image",   cmd_image))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("topup",   cmd_topup))
    app.add_handler(CommandHandler("text",    cmd_text))
    app.add_handler(CommandHandler("about",   cmd_about))
    app.add_handler(CommandHandler("myid",    cmd_myid))
    app.add_handler(CommandHandler("admin",   cmd_admin))
    app.add_handler(CommandHandler("gift",    cmd_gift))
    # Handler texte libre — doit être en DERNIER (priorité basse, le wizard /music passe avant)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_free_message))

    logger.info("TrappistAI Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
