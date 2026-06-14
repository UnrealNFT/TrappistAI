"""
PiranAI Bot - Full Suno-like flow: Style -> Voice -> Theme -> Lyrics (AI or custom) -> Generate
"""
import asyncio, logging, os, sqlite3, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import requests as req
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
except ImportError:
    print("⚠️ shared_db.py not found - PostgreSQL sync disabled")
    store_username_mapping_pg = lambda *args: None
    get_user_id_by_username_pg = lambda *args: None
    get_tokens_pg = lambda *args: 0
    consume_tokens_pg = lambda *args: False
    add_tokens_pg = lambda *args: 0

load_dotenv()
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN         = os.getenv("BOT_TOKEN", "8641629385:AAGibWxAiHRqirqrk9Rawt6FAE_DDVtlTmk")
WAVESPEED_API_KEY = os.getenv("WAVESPEED_API_KEY", "")
OLLAMA_URL        = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "llama3.2")
GROQ_KEY          = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL        = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")
DB_PATH           = os.getenv("DB_PATH",      "piranai.db")
DATABASE_URL      = os.getenv("DATABASE_URL", "")  # PostgreSQL connection
BACKEND_API_URL   = os.getenv("BACKEND_API_URL", "https://trappistai-backend.onrender.com")
ADMIN_USERNAME    = os.getenv("ADMIN_USERNAME", "djaf77").lstrip("@").lower()

USE_POSTGRES = bool(DATABASE_URL)  # Use PostgreSQL if configured, else SQLite

# ─── Mémoire de conversation ─────────────────────────────────────────────────
_conv_history: dict[int, list] = {}  # user_id → derniers messages
_last_msg: dict[int, float] = {}     # user_id → timestamp dernière requête chat

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
    if USE_POSTGRES:
        return add_tokens_pg(user_id, amount)
    # SQLite fallback
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
        return consume_tokens_pg(user_id, amount, ADMIN_USERNAME if username else "")
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
    """Create tokenize keyboard with short callback_data to avoid 64-byte limit."""
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
        [InlineKeyboardButton("💎 Tokenize as RWA (5 CSPR)", callback_data=f"tokenize:{short_id}")],
        [InlineKeyboardButton("❌ Non merci", callback_data="tokenize:skip")]
    ])

# (style_key) -> (tags, emoji+label)
# Styles musicaux — tags libres sans BPM/instruments imposés
# Format: (genre_base, emoji_display)
STYLES = {
    "rap":        ("rap hip-hop",                 "🎤 Rap"),
    "trap":       ("trap",                        "💎 Trap"),
    "drill":      ("drill uk drill",              "🔪 Drill"),
    "pop":        ("pop",                         "🎤 Pop"),
    "rnb":        ("r&b soul",                    "🎵 R&B"),
    "rock":       ("rock",                        "🎸 Rock"),
    "jazz":       ("jazz",                        "🎷 Jazz"),
    "metal":      ("metal heavy",                 "🤘 Metal"),
    "reggae":     ("reggae",                      "🌴 Reggae"),
    "folk":       ("folk acoustic",               "🎸 Folk"),
    "electronic": ("electronic edm",              "🎛 Electronic"),
    "cyberpunk":  ("cyberpunk dark synth",        "🤖 Cyberpunk"),
    "lofi":       ("lofi chill",                  "☕ Lo-Fi"),
    "rai":        ("rai algerian chaabi",         "🌙 Raï"),
    "afro":       ("afrobeat",                    "🌍 Afrobeat"),
    "gospel":     ("gospel spiritual",            "🙏 Gospel"),
    "romantic":   ("romantic slow",               "💕 Romantique"),
}

# Conversation states
S_QUALITY, S_STYLE, S_VOICE, S_DESC, S_CHOICE, S_LYRICS_CHOICE, S_OWN, S_PREVIEW, S_EDIT, S_3D_MENU, S_3D_IMAGE, S_3D_QUALITY = range(12)


# ─── Keyboards ──────────────────────────────────────────────────────────────

def _kb_quality():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Standard (HM) - 10 tokens", callback_data="ms_quality:hm")],
        [InlineKeyboardButton("🎶 HD Premium (MiniMax 2.5) - 15 tokens", callback_data="ms_quality:hd")],
        [InlineKeyboardButton("❌ Annuler", callback_data="ms_cancel")],
    ])

def _kb_styles():
    rows, items = [], list(STYLES.items())
    for i in range(0, len(items), 3):
        rows.append([
            InlineKeyboardButton(v[1], callback_data=f"ms_style:{k}")
            for k, v in items[i:i+3]
        ])
    rows.append([InlineKeyboardButton("❌ Annuler", callback_data="ms_cancel")])
    return InlineKeyboardMarkup(rows)

def _kb_voice():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👨 Masculine", callback_data="ms_voice:male"),
        InlineKeyboardButton("👩 Féminine",  callback_data="ms_voice:female"),
    ], [InlineKeyboardButton("❌ Annuler", callback_data="ms_cancel")]])

def _kb_choice():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎤 Avec paroles", callback_data="ms_choice:lyrics"),
        InlineKeyboardButton("🎸 Instrumental", callback_data="ms_choice:instrumental"),
    ], [
        InlineKeyboardButton("✏️ Mes paroles",    callback_data="ms_choice:own"),
        InlineKeyboardButton("🤖 Générer via IA", callback_data="ms_choice:ai"),
    ], [InlineKeyboardButton("❌ Annuler", callback_data="ms_cancel")]])

def _kb_preview():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎵 Générer",  callback_data="ms_preview:go"),
        InlineKeyboardButton("🔄 Réécrire", callback_data="ms_preview:redo"),
        InlineKeyboardButton("✏️ Modifier", callback_data="ms_preview:edit"),
    ], [InlineKeyboardButton("❌ Annuler", callback_data="ms_cancel")]])


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
            "- Structure markers: [intro-short], [Verse], [Chorus], [Bridge], [outro-short]\n"
            "- Every [Verse]: 6-8 lines. End-of-line RHYMES mandatory (AABB or ABAB scheme). Punchlines, wordplay, vivid imagery.\n"
            "- Every [Chorus]: 4-6 catchy lines that stick in your head. Strong hook.\n"
            "- [Bridge]: 3-4 lines emotional twist.\n"
            "- Write TWO verses + ONE bridge + chorus repeated.\n"
            "- DO NOT translate to French. Write ENTIRELY in English.\n"
            "- Output ONLY the structure markers and lyrics. NO explanations, NO comments, NO titles.\n\n"
            "Example rhyme style:\n"
            "[Verse]\n"
            "Red candle dropping, world is at war / charts are bleeding out, I can't take no more /\n"
            "WW3 on screen, hawks are in flight / moon was a dream but it vanished by night /\n\n"
            "[intro-short]\n[Verse]\n...\n[Chorus]\n...\n[Verse]\n...\n[Bridge]\n...\n[Chorus]\n...\n[outro-short]"
        )
    else:
        prompt = (
            f"Tu es un parolier de génie style {style_label}, voix {'masculine' if voice == 'male' else 'féminine'}.\n"
            f"Thème: {theme}\n\n"
            "RÈGLES STRICTES:\n"
            "- Marqueurs: [intro-short], [Verse], [Chorus], [Bridge], [outro-short]\n"
            "- Chaque [Verse]: 6-8 lignes. RIMES en fin de ligne obligatoires (schéma AABB ou ABAB). Punchlines, jeux de mots, images fortes.\n"
            "- Chaque [Chorus]: 4-6 lignes accrocheuses, hook fort qui reste en tête.\n"
            "- [Bridge]: 3-4 lignes de rupture émotionnelle.\n"
            "- Deux couplets + un bridge + refrain répété.\n"
            "- Écris UNIQUEMENT en français.\n"
            "- UNIQUEMENT les marqueurs et les paroles. Aucun commentaire, aucun titre, aucune explication.\n\n"
            "[intro-short]\n[Verse]\n...\n[Chorus]\n...\n[Verse]\n...\n[Bridge]\n...\n[Chorus]\n...\n[outro-short]"
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
        f"Tu es PiranAI, un pote cash, drôle, intelligent et naturel. "
        f"AUJOURD'HUI C'EST LE {today}. Quand on te demande la date ou l'année, tu réponds {today}. "
        "Ton training s'arrête en 2023 mais tu sais qu'on est en 2026. "
        "Ne dis JAMAIS qu'on est en 2023. "
        "Tu parles comme un vrai humain, tu kiffes l'IA, la musique et le crypto. "
        "Tu te souviens de tout ce qu'on s'est dit. "
        "Détecte la langue de l'utilisateur et réponds toujours dans cette langue."
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
    voice_word = "male" if voice == "male" else "female"
    artist_line = ""
    if artists:
        names = ", ".join(artists)
        artist_line = (
            f"\n- ARTIST STYLE: channel the flow, delivery, wordplay and energy of: {names}. "
            "Absorb their style deeply — don't just name-drop them, WRITE like them."
        )
    sys_msg = (
        "You are a world-class songwriter. "
        "CRITICAL: detect the language of the theme text written by the user and write ALL lyrics in that EXACT same language. "
        "If the theme is in French, write in French. If Spanish, write in Spanish. If Arabic, write in Arabic. Etc. "
        "Write ONLY lyrics with structure markers. NO explanations, NO titles, NO language labels."
    )
    user_msg = (
        f"Style: {style_label}. Voice: {voice_word}. Theme: {theme}\n\n"
        "STRICT RULES:\n"
        "- Use markers: [intro-short] [Verse] [Chorus] [Bridge] [outro-short]\n"
        "- Every [Verse]: 6-8 lines, AABB or ABAB end rhymes mandatory, punchlines, vivid imagery\n"
        "- Every [Chorus]: 4-6 catchy sticky hook lines\n"
        "- [Bridge]: 3-4 emotional twist lines\n"
        "- TWO verses + chorus + bridge + chorus repeated\n"
        f"- Write ENTIRELY in the SAME language as this theme: '{theme}'. Do NOT switch languages."
        f"{artist_line}"
    )
    return _groq_complete([{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}])


def _groq_chat(user_id: int, prompt: str) -> str:
    hist = _conv_history.setdefault(user_id, [])
    hist.append({"role": "user", "content": prompt})
    if len(hist) > 14:  # garde 7 échanges
        _conv_history[user_id] = hist[-14:]
    messages = [
        {"role": "system", "content": (
            f"Tu es PiranAI. Aujourd'hui on est le {datetime.now().strftime('%d/%m/%Y')}. "
            "Tu es un bot Telegram qui peut faire 3 trucs : générer des images IA (/image), "
            "composer de vraies chansons complètes avec musique (/music), "
            "et discuter librement (c'est ce que tu fais là). "
            "Tu parles naturellement, comme un pote — cash, drôle, direct. "
            "Tu kiffes l'IA, la musique et le crypto. "
            "Tu te souviens de tout ce qu'on s'est dit dans cette conversation. "
            "Ton training s'arrête en 2023 mais on est en 2026, ne dis JAMAIS qu'on est en 2023. "
            "Détecte la langue de l'utilisateur et réponds toujours dans cette langue."
        )}
    ] + _conv_history[user_id]
    answer = _groq_complete(messages, max_tokens=900)
    _conv_history[user_id].append({"role": "assistant", "content": answer})
    return answer


def _ai_lyrics(style_label: str, voice: str, theme: str, artists: list = None) -> str:
    """Try Groq first (fast + free), fallback to Ollama."""
    if GROQ_KEY:
        return _groq_lyrics(style_label, voice, theme, artists)
    return _ollama_lyrics(style_label, voice, theme)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_tags(style_key: str, voice: str, artists: list = None, instrumental: bool = False) -> str:
    """Build tags in creative format: 'theme --Style genre' (no fixed BPM/instruments)."""
    base_genre = STYLES.get(style_key, ("music", "🎵"))[0]
    
    # Voice handling
    if instrumental:
        voice_tag = "instrumental"
    else:
        voice_tag = "male vocals" if voice == "male" else "female vocals"
    
    # Artist inspiration
    artist_tag = f", inspired by {', '.join(artists)}" if artists else ""
    
    # Format libre: "voice --Style genre" (HeartMuLa choisit BPM/instruments)
    return f"{voice_tag} --{base_genre.title()}{artist_tag}"

def _ollama_enrich_tags(lyrics: str, base_tags: str) -> str:
    """Ollama adds MAX 2 mood words to the tags based on lyrics. Genre is locked."""
    # Extract the genre lock (first 3 tags) so Ollama can't change them
    genre_lock = ", ".join(base_tags.split(",")[:3]).strip()
    prompt = (
        "You are a music mood analyst.\n"
        f"GENRE (DO NOT CHANGE): {genre_lock}\n"
        f"FULL TAGS: {base_tags}\n"
        f"LYRICS EXCERPT:\n{lyrics[:600]}\n\n"
        "TASK: Read the lyrics. Add EXACTLY 2 mood/emotion words that match the feel.\n"
        "STRICT RULES:\n"
        "- Output ONLY: the original FULL TAGS + ', ' + your 2 mood words. Nothing else.\n"
        "- Your 2 words must be mood/energy ONLY (e.g.: melancholic, triumphant, cold, raw, desperate, fierce)\n"
        "- DO NOT add instruments, DO NOT add genres, DO NOT add BPM, DO NOT add production terms\n"
        "- DO NOT explain. ONE LINE only. Max 200 characters total."
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
        if genre_lock.split(",")[0].strip().lower() in result.lower() and 30 < len(result) < 250:
            return result[:240]
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
    return f"[intro-short]\n[Verse]\n{verse}\n\n[Chorus]\n{chorus}\n\n[outro-short]"

async def _generate_and_send(update: Update, context) -> int:
    ud  = context.user_data
    uid = update.effective_user.id
    
    # Determine model and tokens based on quality choice
    quality = ud.get("quality", "hm")  # Default to HeartMuLa if not set
    tokens_needed = 10 if quality == "hm" else 15
    model_name = "HeartMuLa" if quality == "hm" else "MiniMax 2.5 HD"
    
    if not consume_tokens(uid, tokens_needed, update.effective_user.username or ""):
        bal = get_tokens(uid)
        await update.effective_message.reply_text(
            f"❌ *{tokens_needed} tokens requis pour générer une chanson {model_name}* — Solde: `{bal}` token(s)\n"
            "💰 Utilise `/topup` pour recharger.",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    style_key = ud["style_key"]
    voice     = ud["voice"]
    artists   = ud.get("artists", [])
    instrumental = ud.get("instrumental", False)
    
    # Build tags with instrumental support
    base_tags = _build_tags(style_key, voice, artists, instrumental)
    
    # Format lyrics (empty for instrumental)
    lyrics = "" if instrumental else _format_lyrics(ud["lyrics"])
    
    _, label  = STYLES[style_key]
    vi        = "👨" if voice == "male" else "👩"
    mode_text = "🎸 Instrumental" if instrumental else f"{vi} Avec paroles"

    # Ollama enrichit les tags selon le contenu réel des paroles (skip pour instrumental)
    if instrumental:
        tags = base_tags
    else:
        tags = await asyncio.get_event_loop().run_in_executor(
            None, _ollama_enrich_tags, lyrics, base_tags
        )

    msg = await update.effective_message.reply_text(
        f"🎵 Composition *{label}* {mode_text} en cours…\n🎸 `{tags}`\n⏳ Génération en cours, peut prendre 10-30 min 🙏",
        parse_mode=ParseMode.MARKDOWN,
    )

    async def _progress():
        steps = [
            (120,  "⏳ 2 min… HeartMuLa compose 🎼"),
            (240,  "⏳ 4 min… Arrangement en cours 🎸"),
            (360,  "⏳ 6 min… Mixage 🎚️"),
            (480,  "⏳ 8 min… Mastering 🔊"),
            (600,  "⏳ 10 min… Finalisation 🎵"),
            (900,  "⏳ 15 min… Toujours en cours, tiens bon 💪"),
            (1200, "⏳ 20 min… Presque là… 🔥"),
            (1500, "⏳ 25 min… WaveSpeed prend son temps 😅"),
            (1800, "⏳ 30 min… J'abandonne pas, je t'envoie dès que c'est prêt 🤞"),
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
                f"⏳ *{label}* {vi} — Génération longue, je t'envoie dès que c'est prêt…\n"
                f"_Task `{e.task_id[:16]}…` toujours en cours_",
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
                f"❌ Génération échouée après 50 min\n"
                f"🔑 Task ID: `{e.task_id}`\n"
                f"_Contacte l'admin avec ce code pour récupérer ta musique_",
                parse_mode=ParseMode.MARKDOWN,
            )
            context.user_data.clear()
            return ConversationHandler.END
    except Exception as e:
        progress_task.cancel()
        logger.error("Music error: %s", e)
        await msg.edit_text(f"❌ Erreur: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return ConversationHandler.END

    if url:
        progress_task.cancel()
        try:
            await msg.delete()
        except Exception:
            pass
        
        # Create tokenize keyboard with short callback_data
        keyboard = create_tokenize_keyboard("music", url, label)
        
        await update.effective_message.reply_audio(
            audio=url,
            caption=f"🎵 *{label}* {vi}\n🎸 `{tags}`\n\n[Lien direct]({url})",
            parse_mode=ParseMode.MARKDOWN,
            title=f"PiranAI — {label}",
            performer="HeartMuLa x WaveSpeed",
            reply_markup=keyboard,
        )
        logger.info("Music [%s/%s] %s → %s", label, voice, update.effective_user.id, url)

    context.user_data.clear()
    return ConversationHandler.END


# ─── Step 1: Style ───────────────────────────────────────────────────────────

async def cmd_music(update: Update, context) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "🎼 *Choisis la qualité de génération:*\n\n"
        "🎵 **Standard (HeartMuLa)** — Rapide, bon rapport qualité/prix\n"
        "🎶 **HD Premium (MiniMax 2.5)** — Haute fidélité, voix humanisées",
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
    tokens_needed = 10 if quality == "hm" else 15
    await q.edit_message_text(
        f"✅ *{model_name}* sélectionné ({tokens_needed} tokens)\n\n🎼 *Étape 2/4 — Choisis ton style:*",
        reply_markup=_kb_styles(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_STYLE

async def on_style(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    if key not in STYLES:
        await q.edit_message_text("❌ Style inconnu.")
        return ConversationHandler.END
    context.user_data["style_key"] = key
    _, label = STYLES[key]
    await q.edit_message_text(
        f"✅ Style: *{label}*\n\n🎤 *Étape 2/3 — Voix:*",
        reply_markup=_kb_voice(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_VOICE


# ─── Step 2: Voice ───────────────────────────────────────────────────────────

async def on_voice(update: Update, context) -> int:
    q = update.callback_query
    await q.answer()
    voice = q.data.split(":", 1)[1]
    context.user_data["voice"] = voice
    _, label = STYLES[context.user_data["style_key"]]
    vi = "👨 Masculine" if voice == "male" else "👩 Féminine"
    await q.edit_message_text(
        f"✅ *{label}* · {vi}\n\n"
        "✍️ *Étape 3/3 — Décris le thème de ta chanson:*\n"
        "_(ex: bitcoin qui monte, amour perdu, nuit en ville…)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_DESC


# ─── Step 3: Theme ───────────────────────────────────────────────────────────

async def on_desc(update: Update, context) -> int:
    raw = update.message.text.strip()
    clean_theme, artists = _parse_hashtags(raw)
    context.user_data["theme"] = clean_theme or raw
    context.user_data["artists"] = artists
    
    # Protection: si style_key manquant, reset la conversation
    style_key = context.user_data.get("style_key")
    if not style_key or style_key not in STYLES:
        await update.message.reply_text(
            "⚠️ État corrompu détecté. Relance /music pour recommencer.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END
    
    _, label = STYLES[style_key]
    vi = "👨" if context.user_data.get("voice") == "male" else "👩"
    artist_hint = f"\n🎤 Style artiste: *{'  '.join('#'+a for a in artists)}*" if artists else ""
    await update.message.reply_text(
        f"✅ *{label}* {vi} · _{clean_theme or raw}_{artist_hint}\n\n"
        "🎵 *Tu veux des paroles ou juste l'instrumental?*",
        reply_markup=_kb_choice(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_CHOICE


# ─── Step 4: Lyrics or Instrumental ─────────────────────────────────────────

async def on_choice_lyrics(update: Update, context) -> int:
    """User wants vocals - ask for own lyrics or AI generation."""
    q = update.callback_query
    await q.answer()
    context.user_data["instrumental"] = False
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ J'écris mes paroles", callback_data="ms_lyrics:own")],
        [InlineKeyboardButton("🤖 IA génère les paroles", callback_data="ms_lyrics:ai")],
        [InlineKeyboardButton("❌ Annuler", callback_data="ms_cancel")],
    ])
    await q.edit_message_text(
        "🎤 *Comment veux-tu créer les paroles?*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
    return S_LYRICS_CHOICE

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
    await q.edit_message_text(
        "✍️ *Envoie tes paroles maintenant:*\n"
        "_(Tu peux utiliser `[Verse]`, `[Chorus]`, `[Bridge]` ou texte libre)_\n"
        "_(ou /cancel)_",
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
    _, label = STYLES[ud["style_key"]]
    vi = "👨" if ud["voice"] == "male" else "👩"
    await q.edit_message_text(
        f"🤖 *IA parolière en train d\'écrire…*\n"
        f"Style: *{label}* {vi} · Thème: _{ud.get('theme', '')}_\n"
        "_(~15 secondes)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        lyrics = await asyncio.get_event_loop().run_in_executor(
            None, _ai_lyrics, label, ud["voice"], ud.get("theme", ""), ud.get("artists", [])
        )
        context.user_data["lyrics"] = lyrics
        preview = lyrics[:3500] + ("…" if len(lyrics) > 3500 else "")
        await q.edit_message_text(
            f"📝 *Paroles g\u00e9n\u00e9r\u00e9es par l\'IA:*\n\n```\n{preview}\n```\n\n_Que veux-tu faire?_",
            reply_markup=_kb_preview(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return S_PREVIEW
    except Exception as e:
        logger.error("AI lyrics error: %s", e)
        await q.edit_message_text(
            f"❌ IA indisponible: `{str(e)[:120]}`\n\n"
            "✍️ *Envoie tes paroles manuellement:*\n_(ou /cancel)_",
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
        _, label = STYLES[ud["style_key"]]
        vi = "👨" if ud["voice"] == "male" else "👩"
        await q.edit_message_text(
            f"🔄 *Réécriture en cours…*\nStyle: *{label}* {vi} · Thème: _{ud.get('theme', '')}_",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            lyrics = await asyncio.get_event_loop().run_in_executor(
                None, _ai_lyrics, label, ud["voice"], ud.get("theme", ""), ud.get("artists", [])
            )
            context.user_data["lyrics"] = lyrics
            preview = lyrics[:3500] + ("…" if len(lyrics) > 3500 else "")
            await q.edit_message_text(
                f"📝 *Nouvelles paroles:*\n\n```\n{preview}\n```\n\n_Que veux-tu faire?_",
                reply_markup=_kb_preview(),
                parse_mode=ParseMode.MARKDOWN,
            )
            return S_PREVIEW
        except Exception as e:
            await q.edit_message_text(f"❌ Erreur IA: `{str(e)[:150]}`", parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END

    if action == "edit":
        await q.edit_message_text(
            "✍️ *Envoie tes paroles modifiées:*\n_(ou /cancel)_",
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
    await q.edit_message_text("❌ Annulé.")
    context.user_data.clear()
    return ConversationHandler.END

async def cmd_cancel(update: Update, context) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Annulé.")
    return ConversationHandler.END


# ─── /image ──────────────────────────────────────────────────────────────────

async def cmd_image(update: Update, context) -> None:
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text("❌ Utilise: `/image ton prompt`", parse_mode=ParseMode.MARKDOWN)
        return
    uid = update.effective_user.id
    if not consume_tokens(uid, 1, update.effective_user.username or ""):
        bal = get_tokens(uid)
        await update.message.reply_text(
            f"❌ *Token insuffisant* \u2014 Solde: `{bal}` token(s)\n💰 Utilise `/topup` pour recharger.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    msg = await update.message.reply_text("⏳ Génération en cours…")
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
            caption=f"🎨 *{prompt[:80]}*\n\n[Lien direct]({url})",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        logger.info("Image %s: %s", update.effective_user.id, url)
    except Exception as e:
        logger.error("Image generation error: %s", e)
        try:
            await msg.edit_text(f"❌ Erreur: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(f"❌ Erreur: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)


# ─── /pira3d ─────────────────────────────────────────────────────────────────

async def cmd_pira3d(update: Update, context) -> int:
    context.user_data.clear()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ From Image", callback_data="3d:image")],
        [InlineKeyboardButton("✍️ From Text (Soon)", callback_data="3d:text_soon")],
        [InlineKeyboardButton("❌ Cancel", callback_data="3d:cancel")],
    ])
    await update.message.reply_text(
        "🎨 *PiranAI 3D Generator*\n\n"
        "Choisis ton mode de génération:",
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
        await q.edit_message_text("✍️ Mode texte disponible bientôt ! Utilise *From Image* pour l'instant.", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return ConversationHandler.END
    
    if choice == "image":
        await q.edit_message_text(
            "📷 *Envoie-moi ton image*\n_(ou /cancel)_",
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
        [InlineKeyboardButton("⚡ Sans texture (2 tokens)", callback_data="3dq:notex")],
        [InlineKeyboardButton("🎨 Avec texture (30 tokens)", callback_data="3dq:tex")],
        [InlineKeyboardButton("❌ Annuler", callback_data="3dq:cancel")],
    ])
    await update.message.reply_text(
        "🎨 *Choisis la qualité du modèle 3D:*\n\n"
        "⚡ *Sans texture* — 2 tokens (~2 min)\n"
        "   └ Géométrie pure, monochrome\n\n"
        "🎨 *Avec texture* — 30 tokens (~5 min)\n"
        "   └ Couleurs et textures complètes",
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
        await q.edit_message_text("❌ Session expirée. Utilise /pira3d pour recommencer.")
        context.user_data.clear()
        return ConversationHandler.END
    
    choice = q.data.split(":")[1]
    
    if choice == "cancel":
        await q.edit_message_text("❌ Annulé.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Determine model and cost
    if choice == "notex":
        cost = 2
        model_name = "Hunyuan-3D V3.1"
        use_texture = False
    else:  # tex
        cost = 30
        model_name = "Tripo3D v2.5"
        use_texture = True
    
    # Check tokens
    if not consume_tokens(uid, cost, update.effective_user.username or ""):
        bal = get_tokens(uid)
        await q.answer(f"❌ {cost} tokens requis (solde: {bal})", show_alert=True)
        return S_3D_QUALITY
    
    try:
        await q.edit_message_text(f"🎨 *Génération 3D en cours…*\n_Modèle: {model_name}_\n⏳ Peut prendre jusqu'à 5 min", parse_mode=ParseMode.MARKDOWN)
        
        # Generate 3D
        if use_texture:
            glb_url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_3d_with_texture, image_url
            )
        else:
            glb_url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.generate_3d_from_image, image_url, None
            )
        
        # Download GLB file
        glb_data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: req.get(glb_url, timeout=60).content
        )
        
        # Create viewer link
        viewer_url = f"https://deluxe-souffle-bc6b1c.netlify.app/?url={urllib.parse.quote(glb_url)}"
        
        # Send GLB file
        texture_info = "avec texture" if use_texture else "sans texture"
        await q.message.reply_document(
            document=glb_data,
            caption=f"✅ *Modèle 3D généré !* ({texture_info})\n\n"
                    f"📦 Format: GLB\n"
                    f"🎨 Modèle: {model_name}\n"
                    f"🔗 [Visualiser en 3D]({viewer_url})",
            parse_mode=ParseMode.MARKDOWN,
            filename="model3d.glb",
        )
        logger.info("3D model [%s]: %s (%s)", uid, glb_url, texture_info)
    except Exception as e:
        logger.error("3D generation error: %s", e)
        try:
            await msg.edit_text(f"❌ Erreur: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(f"❌ Erreur: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
    
    context.user_data.clear()
    return ConversationHandler.END


async def on_3d_cancel(update: Update, context) -> int:
    await update.message.reply_text("❌ Génération 3D annulée.")
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
        bonus = "\n\n🔑 *Mode admin actif — accès illimité*"
    elif is_new_user(uid):
        _db.execute("INSERT OR IGNORE INTO users(user_id, tokens) VALUES(?,0)", (uid,))
        _db.commit()
        bonus = "\n\n💬 Chat gratuit disponible — */topup* pour générer images/musique"
    else:
        bal = get_tokens(uid)
        bonus = f"\n\n💰 Ton solde: *{bal} token(s)*"
    await update.message.reply_text(
        "🎨 *PiranAI* — Images & Musique IA\n\n"
        "🖼 */image* `prompt` → FLUX.1 image *(~5s)* — *1 token*\n"
        "🎵 */music* → Chanson complète *(2-3 min)* — *10 tokens*\n"
        "💬 */text* `question` → Chat Llama 3.3 *(gratuit)*\n"
        "💰 */balance* → Voir tes tokens\n"
        "🔋 */topup* → Recharger des tokens"
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
            "❌ *Pas de username Telegram détecté*\n\n"
            "Configure un @username dans Telegram Settings pour utiliser cette fonctionnalité.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Store mapping
    store_username_mapping(uid, username)
    
    await update.message.reply_text(
        f"✅ *Compte lié avec succès!*\n\n"
        f"📱 Telegram: @{username}\n"
        f"🆔 User ID: `{uid}`\n\n"
        f"🔗 Tu peux maintenant linker ton compte sur:\n"
        f"[trappistai.netlify.app/profile](https://trappistai.netlify.app/profile)\n\n"
        f"💡 Entre **@{username}** sur le site pour recevoir ton code de vérification ici!",
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
            "❌ *Pas de username Telegram détecté*\n\n"
            "Configure un @username dans Telegram Settings.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Get code from command args
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ *Format incorrect*\n\n"
            "Usage: `/verify 123456`\n\n"
            "💡 Obtiens ton code sur trappistai.netlify.app/profile",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    code = context.args[0].strip()
    
    if len(code) != 6 or not code.isdigit():
        await update.message.reply_text(
            "❌ *Code invalide*\n\n"
            "Le code doit être 6 chiffres.",
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
                "❌ *Configuration manquante*\n\n"
                "Contacte @djaf77 - DATABASE_URL non configuré.",
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
                        "❌ *Code introuvable*\n\n"
                        "Vérifie que tu as bien copié le code depuis le site.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                
                wallet, stored_username, expires_at, verified = result
                print(f"✓ Code found: wallet={wallet[:10]}..., username={stored_username}, verified={verified}")
                
                if verified:
                    await update.message.reply_text(
                        "❌ *Code déjà utilisé*\n\n"
                        "Génère un nouveau code sur le site.",
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
                        "❌ *Code expiré*\n\n"
                        "Génère un nouveau code sur le site (valable 10 min).",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                
                if stored_username.lower() != username.lower():
                    print(f"❌ Username mismatch: expected {stored_username}, got {username}")
                    await update.message.reply_text(
                        f"❌ *Username incorrect*\n\n"
                        f"Ce code est pour @{stored_username}, mais tu es @{username}.\n\n"
                        f"Enregistre @{username} sur le site d'abord.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                
                # Mark as verified and store telegram_user_id
                cur.execute("""
                    UPDATE telegram_verification
                    SET verified = TRUE
                    WHERE verification_code = %s
                """, (code,))
                
                # Also update users table
                cur.execute("""
                    UPDATE users
                    SET telegram_verified = TRUE, telegram_user_id = %s
                    WHERE wallet_address = %s
                """, (uid, wallet))
                
                # Get user's token balance
                cur.execute("""
                    SELECT tokens FROM users WHERE wallet_address = %s
                """, (wallet,))
                balance_row = cur.fetchone()
                tokens = balance_row[0] if balance_row else 0
                
                conn.commit()
                
                print(f"✅ Verified @{username} (uid={uid}) for wallet {wallet[:10]}... with code {code} - Balance: {tokens} tokens")
                
                await update.message.reply_text(
                    "✅ *Compte vérifié avec succès!*\n\n"
                    f"📱 Telegram: @{username}\n"
                    f"💼 Wallet: `{wallet[:20]}...`\n"
                    f"💰 Solde: *{tokens} token(s)*\n\n"
                    "🎨 Tes générations sont maintenant synchronisées entre le site et Telegram!",
                    parse_mode=ParseMode.MARKDOWN,
                )
        finally:
            conn.close()
            
    except psycopg.Error as e:
        print(f"❌ PostgreSQL error: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ *Erreur de base de données*\n\n"
            f"Erreur: `{str(e)[:100]}`\n\n"
            "Contacte @djaf77 si le problème persiste.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        await update.message.reply_text(
            "❌ *Module manquant*\n\n"
            f"Erreur: `{str(e)}`\n\n"
            "Contacte @djaf77 - psycopg non installé.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        print(f"❌ Failed to verify code: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ *Erreur lors de la vérification*\n\n"
            f"Erreur: `{str(e)[:100]}`\n\n"
            "Réessaye dans quelques secondes.",
            parse_mode=ParseMode.MARKDOWN,
        )

async def cmd_help(update: Update, context) -> None:
    await update.message.reply_text(
        "📖 *Aide PiranAI*\n\n"
        "🖼 */image* `prompt` \u2014 image FLUX.1 **(1 token)**\n"
        "🎵 */music* \u2014 wizard style\u2192voix\u2192th\u00e8me\u2192paroles **(10 tokens)**\n"
        "💬 */text* `question` \u2014 chat IA Llama 3.3 **(gratuit)**\n"
        "💰 */balance* \u2014 voir ton solde\n"
        "🔋 */topup* \u2014 recharger des tokens\n"
        "🔗 */link* \u2014 linker avec TrappistAI website\n\n"
        "⚡ WaveSpeed + HeartMuLa + Groq",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_about(update: Update, context) -> None:
    await update.message.reply_text(
        "🧠 *Stack IA — PiranAI*\n\n"
        "🎵 *Musique — HeartMuLa*\n"
        "┣ HeartMuLa LLM : *3B paramètres* (Llama 3.2 backbone)\n"
        "┣ HeartCodec : *1.5B params* — tokenizer audio 12.5 Hz\n"
        "┃   → génère des chansons longues sans exploser la VRAM\n"
        "┣ HeartCLAP : alignement texte↔audio\n"
        "┗ HeartTranscriptor : paroles → tokens\n\n"
        "⚡ Pipeline total ~4-5B params — tourne sur une RTX 3090/4090\n"
        "_(version 7B interne en dev — coming soon)_\n\n"
        "🖼 *Image — FLUX.1-schnell*\n"
        "┗ 12B params, 4 steps, distillé par Black Forest Labs\n\n"
        "💬 *Paroles & Chat — Groq + Llama 3.3 70B*\n"
        "┗ Inférence ultra-rapide via Groq Cloud (~1s)\n\n"
        "🚀 Hébergement API : *WaveSpeed AI*",
        parse_mode=ParseMode.MARKDOWN,
    )

# ─── /balance  /topup  /text ─────────────────────────────────────────────────────────

async def cmd_balance(update: Update, context) -> None:
    uid = update.effective_user.id
    bal = get_tokens(uid)
    await update.message.reply_text(
        f"💰 *Ton solde PiranAI:* `{bal}` token(s)\n\n"
        "🖼 Image = 1 token\n"
        "🎵 Musique = 10 tokens\n"
        "💬 Chat = *gratuit* (Ollama local)\n\n"
        "_/topup pour recharger_",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_topup(update: Update, context) -> None:
    uid = update.effective_user.id
    bal = get_tokens(uid)
    await update.message.reply_text(
        f"� <b>Solde actuel:</b> {bal} token(s)\n\n"
        "🔋 <b>Recharge tes tokens sur le site:</b>\n"
        "👉 https://trappistai.netlify.app/buy\n\n"
        "Paiement sécurisé en crypto (CSPR)",
        parse_mode=ParseMode.HTML,
    )


# ─── Tokenize Assets as RWA ──────────────────────────────────────────────────

async def on_tokenize_asset(update: Update, context) -> None:
    """Handle tokenize button clicks - ask for number of shares."""
    q = update.callback_query
    await q.answer()
    
    data = q.data  # Format: "tokenize:{short_id}" or "tokenize:skip"
    
    # Handle skip
    if data == "tokenize:skip":
        try:
            await q.edit_message_reply_markup(reply_markup=None)  # Remove buttons
        except Exception:
            pass
        return
    
    # Extract short_id from callback_data
    parts = data.split(":", 1)
    if len(parts) < 2:
        await q.edit_message_text("❌ Données invalides")
        return
    
    short_id = parts[1]
    
    # Get data from memory
    if short_id not in _tokenize_data:
        await q.edit_message_text("❌ Session expirée, régénère ton contenu")
        return
    
    uid = update.effective_user.id
    
    # Get user's wallet address
    wallet = get_wallet_by_telegram_id_pg(uid)
    if not wallet:
        # Remove buttons and send new message (can't edit_message_text on photo/audio)
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await q.message.reply_text(
            "❌ *Tu dois d'abord connecter ton wallet Casper*\n\n"
            "👉 Va sur https://trappistai.netlify.app/profile\n"
            "🔗 Connecte ton wallet et lie ton compte Telegram\n\n"
            "Ensuite tu pourras tokenizer tes créations !",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Remove buttons and ask for number of shares
    try:
        await q.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    # Create keyboard for share selection
    keyboard = [
        [
            InlineKeyboardButton("100 parts (1%)", callback_data=f"shares:{short_id}:100"),
            InlineKeyboardButton("1,000 parts (0.1%)", callback_data=f"shares:{short_id}:1000"),
        ],
        [
            InlineKeyboardButton("10,000 parts (0.01%)", callback_data=f"shares:{short_id}:10000"),
        ],
        [InlineKeyboardButton("❌ Annuler", callback_data="tokenize:skip")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await q.message.reply_text(
        "💎 *Combien de parts pour ce token ?*\n\n"
        "🟢 *100 parts* = Simple (1 part = 1%)\n"
        "🟡 *1,000 parts* = Standard (1 part = 0.1%)\n"
        "🔵 *10,000 parts* = Pro (1 part = 0.01%)\n\n"
        "➡️ Plus de parts = Plus de flexibilité pour vendre",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
    )


async def on_tokenize_shares_choice(update: Update, context) -> None:
    """Handle share count selection and mint RWA token."""
    q = update.callback_query
    await q.answer()
    
    data = q.data  # Format: "shares:{short_id}:{count}"
    parts = data.split(":")
    if len(parts) != 3:
        await q.edit_message_text("❌ Données invalides")
        return
    
    short_id = parts[1]
    total_shares = int(parts[2])
    
    # Get data from memory
    if short_id not in _tokenize_data:
        await q.edit_message_text("❌ Session expirée, régénère ton contenu")
        return
    
    asset_info = _tokenize_data[short_id]
    asset_type = asset_info["type"]
    asset_url = asset_info["url"]
    prompt = asset_info["prompt"]
    
    uid = update.effective_user.id
    wallet = get_wallet_by_telegram_id_pg(uid)
    
    if not wallet:
        await q.edit_message_text(
            "❌ Wallet non connecté. Va sur https://trappistai.netlify.app/profile",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    # Remove buttons and send progress message
    try:
        await q.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    progress_msg = await q.message.reply_text(
        f"💎 *Tokenization en cours...*\n\n"
        f"Type: {asset_type}\n"
        f"Wallet: `{wallet[:20]}...`",
        parse_mode=ParseMode.MARKDOWN,
    )
    
    try:
        # Call backend API to mint RWA token
        response = req.post(
            f"{BACKEND_API_URL}/api/rwa/mint",
            json={
                "walletAddress": wallet,
                "assetType": asset_type,
                "assetUrl": asset_url,
                "prompt": prompt,
                "model": "wavespeed",
                "telegramUserId": uid,
                "totalShares": total_shares,
            },
            timeout=10,
        )
        
        if response.status_code == 200:
            data = response.json()
            token_id = data.get("tokenId", "?")
            await progress_msg.edit_text(
                f"✅ *RWA Token créé !*\n\n"
                f"🎫 Token ID: `#{token_id}`\n"
                f"💎 Type: {asset_type}\n"
                f"📊 Parts: {total_shares:,} (1 part = {100/total_shares:.2f}%)\n\n"
                f"👉 Voir tes NFTs: https://trappistai.netlify.app/my-rwa\n"
                f"💰 Vendre sur le marketplace: https://trappistai.netlify.app/marketplace",
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info("Tokenized %s for user %s: token #%s with %d shares", asset_type, uid, token_id, total_shares)
            
            # Clean up memory
            del _tokenize_data[short_id]
        else:
            error_msg = response.json().get("detail", "Unknown error")
            await progress_msg.edit_text(
                f"❌ *Échec de la tokenization*\n\n"
                f"Erreur: `{error_msg[:200]}`\n\n"
                "Contacte @Djaf77 si le problème persiste.",
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        logger.error("Tokenize API error: %s", e)
        await progress_msg.edit_text(
            f"❌ *Erreur de connexion à l'API*\n\n"
            f"`{str(e)[:200]}`\n\n"
            "Vérifie que le backend est en ligne.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def cmd_text(update: Update, context) -> None:
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text("💬 Envoie-moi directement ton message, pas besoin de /text !", parse_mode=ParseMode.MARKDOWN)
        return
    msg = await update.message.reply_text("💬 En réflexion…")
    try:
        answer = await asyncio.get_event_loop().run_in_executor(None, _groq_chat, update.effective_user.id, prompt)
        await msg.edit_text(f"🤖 {answer[:4000]}")
    except Exception as e:
        await msg.edit_text(f"❌ Erreur: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)


async def on_free_message(update: Update, context) -> None:
    """Chat libre gratuit via Groq."""
    if not update.message or not update.message.text:
        return
    uid = update.effective_user.id
    now = asyncio.get_event_loop().time()
    if now - _last_msg.get(uid, 0) < 4:
        return  # anti-spam: ignore si < 4s depuis dernier message
    _last_msg[uid] = now
    prompt = update.message.text.strip()
    msg = await update.message.reply_text("💬 En réflexion…")
    try:
        answer = await asyncio.get_event_loop().run_in_executor(None, _groq_chat, uid, prompt)
        await msg.edit_text(f"🤖 {answer[:4000]}")
    except Exception as e:
        await msg.edit_text(f"❌ Erreur: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_myid(update: Update, context) -> None:
    uid = update.effective_user.id
    uname = update.effective_user.username or "?"
    await update.message.reply_text(
        f"🔑 Ton Telegram ID : `{uid}`\n👤 Username : @{uname}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_admin(update: Update, context) -> None:
    if not is_admin(update.effective_user):
        await update.message.reply_text("❌ Accès refusé.")
        return
    args = context.args
    # /admin topup <user_id> <amount>
    if len(args) == 3 and args[0] == "topup":
        try:
            target_id = int(args[1])
            amount    = int(args[2])
        except ValueError:
            await update.message.reply_text("Utilise: `/admin topup USER_ID AMOUNT`", parse_mode=ParseMode.MARKDOWN)
            return
        new_bal = add_tokens(target_id, amount)
        await update.message.reply_text(
            f"✅ +{amount} tokens pour `{target_id}` — nouveau solde: *{new_bal}*",
            parse_mode=ParseMode.MARKDOWN,
        )
    # /admin balance <user_id>
    elif len(args) == 2 and args[0] == "balance":
        try:
            target_id = int(args[1])
        except ValueError:
            await update.message.reply_text("Utilise: `/admin balance USER_ID`", parse_mode=ParseMode.MARKDOWN)
            return
        bal = get_tokens(target_id)
        await update.message.reply_text(f"`{target_id}` : *{bal} token(s)*", parse_mode=ParseMode.MARKDOWN)
    # /admin fetch <task_id> <user_id>
    elif len(args) == 3 and args[0] == "fetch":
        task_id   = args[1]
        try:
            target_id = int(args[2])
        except ValueError:
            await update.message.reply_text("Utilise: `/admin fetch TASK_ID USER_ID`", parse_mode=ParseMode.MARKDOWN)
            return
        await update.message.reply_text(f"⏳ Poll task `{task_id[:16]}…` en cours (max 5 min)...", parse_mode=ParseMode.MARKDOWN)
        try:
            url = await asyncio.get_event_loop().run_in_executor(
                None, wavespeed.fetch_result, task_id, 300
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Task pas prête ou échouée: `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            await context.bot.send_audio(
                chat_id=target_id,
                audio=url,
                caption=f"🎵 Ta chanson est prête!\n[Lien direct]({url})",
                parse_mode=ParseMode.MARKDOWN,
                performer="HeartMuLa x WaveSpeed",
            )
            await update.message.reply_text(f"✅ Envoyé à `{target_id}`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Envoi échoué: `{str(e)[:200]}`\nURL: {url}", parse_mode=ParseMode.MARKDOWN)
    # /admin list
    elif len(args) == 1 and args[0] == "list":
        rows = _db.execute("SELECT user_id, tokens FROM users ORDER BY tokens DESC LIMIT 20").fetchall()
        if not rows:
            await update.message.reply_text("DB vide.")
            return
        lines = "\n".join(f"`{r[0]}` : {r[1]} tokens" for r in rows)
        await update.message.reply_text(f"📊 *Users (top 20):*\n{lines}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            "*Commandes admin:*\n"
            "`/admin topup USER_ID AMOUNT`\n"
            "`/admin balance USER_ID`\n"
            "`/admin list`\n"
            "`/admin fetch TASK_ID USER_ID`",
            parse_mode=ParseMode.MARKDOWN,
        )


# ─── Main ────────────────────────────────────────────────────────────────────

async def error_handler(update: object, context) -> None:
    """Log errors and reset corrupted conversation state."""
    logger.error(f"Error: {context.error}", exc_info=context.error)
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ *Erreur interne détectée*\n"
                "Ton état de conversation a été réinitialisé.\n"
                "Relance ta commande (/music, /pira3d, etc.)",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

def main():
    if not WAVESPEED_API_KEY:
        logger.error("WAVESPEED_API_KEY not set!")
        return

    # Thread pool : 1 thread par génération audio simultanée possible (50 = 50 users en parallèle)
    executor = ThreadPoolExecutor(max_workers=50, thread_name_prefix="piranai")
    
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
        .concurrent_updates(True)   # chaque user traité en parallèle, pas de file d'attente
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
                        CallbackQueryHandler(on_cancel_cb,  pattern=r"^ms_cancel$")],
            S_VOICE:   [CallbackQueryHandler(on_voice,      pattern=r"^ms_voice:"),
                        CallbackQueryHandler(on_cancel_cb,  pattern=r"^ms_cancel$")],
            S_DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, on_desc),
                        CommandHandler("cancel", cmd_cancel)],
            S_CHOICE:  [CallbackQueryHandler(on_choice_lyrics, pattern=r"^ms_choice:lyrics$"),
                        CallbackQueryHandler(on_choice_instrumental,  pattern=r"^ms_choice:instrumental$"),
                        CallbackQueryHandler(on_cancel_cb,  pattern=r"^ms_cancel$")],
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
        entry_points=[CommandHandler("pira3d", cmd_pira3d)],
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

    # Tokenize callback (must be before other handlers to avoid conflicts)
    app.add_handler(CallbackQueryHandler(on_tokenize_asset, pattern=r"^tokenize:"))
    app.add_handler(CallbackQueryHandler(on_tokenize_shares_choice, pattern=r"^shares:"))

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("link",    cmd_link))
    app.add_handler(CommandHandler("verify",  cmd_verify))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("image",   cmd_image))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("topup",   cmd_topup))
    app.add_handler(CommandHandler("text",    cmd_text))
    app.add_handler(CommandHandler("about",   cmd_about))
    app.add_handler(CommandHandler("myid",    cmd_myid))
    app.add_handler(CommandHandler("admin",   cmd_admin))
    # Handler texte libre — doit être en DERNIER (priorité basse, le wizard /music passe avant)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_free_message))

    logger.info("PiranAI Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
