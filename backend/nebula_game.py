"""
Extension TRAPPIST LEGEND : NÉBULA pour le backend TrappistAI (FastAPI + PostgreSQL)
====================================================================================
Regroupe tout ce dont le jeu a besoin côté serveur :

  🧬 POST /api/game/fuse            fusion payante (1 token) : prompt aléatoire -> FLUX -> URL
  ⚔️ POST /api/arena/deck           enregistre le deck d'arène (20 cartes) du joueur
  ⚔️ GET  /api/arena/opponent/{w}   deck d'un adversaire au hasard (JcJ asynchrone)
  ⚔️ POST /api/arena/result         enregistre win | lose | tie
  ⚔️ GET  /api/arena/leaderboard    top 20

INSTALLATION (backend TrappistAI, Render) :
    1. Copier ce fichier dans  backend/nebula_game.py
    2. Dans backend/main.py, ajouter :
           import nebula_game
           app.include_router(nebula_game.router)
    3. Push -> Render redéploie. La table arène se crée toute seule au premier appel.

La fusion débite 1 token via consume_user_tokens() APRÈS une génération réussie,
exactement comme /api/generate/image. La clé WaveSpeed reste sur le serveur (env Render).
"""

import asyncio
import json
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from db import engine, get_user_balance, consume_user_tokens
import wavespeed

router = APIRouter()

# ============================== FUSION IA (cartes d'arène du jeu) ==============================
# Tarification alignée sur les coûts WaveSpeed réels (marge protégée) :
#   fusion de base (rang 1)  -> 1 token, FLUX.1-schnell (~$0.003) — marge ~86% à 10 CSPR/token
#   re-fusion (rang 2+)      -> 2 tokens, FLUX.1-dev (~$0.025, art épique pour les hauts rangs) — marge ~40%
FUSION_COST_TOKENS = 1
REFUSION_COST_TOKENS = 2

# descriptions de base des espèces (reprises du pipeline de génération du jeu)
_SPECIES = {
    "turtle": ("a bipedal humanoid turtle warrior mascot standing upright on two strong legs, spiked dark obsidian shell "
               "on its back, muscular arms, wise determined face, glowing purple cracks on the shell", "Turtlian"),
    "elephant": ("a bipedal humanoid elephant warrior mascot standing upright on two legs, big ears, long trunk, "
                 "curved ivory tusks glowing violet at the tips, tribal stone armor plates", "Elephantian"),
    "phoenix": ("a majestic phoenix bird in flight, wings fully spread wide, golden orange and red fiery feathers, "
                "long flaming tail of fire, glowing yellow highlights", "Phenixian"),
    "dragon": ("a powerful dark dragon with huge bat-like wings, obsidian scales, horned head, long tail", "Dragon"),
}

_TRAITS = [
    "asymmetric glowing battle scars", "glowing tribal tattoos across the body",
    "crystal horns and spine spikes", "a spiked mace-like tail", "an extra pair of small arms",
    "bioluminescent dotted patterns", "scavenged metal armor implants", "tribal bone jewelry and piercings",
    "cracked obsidian armor patches", "crackling electricity arcs around the claws",
    "floating rock shards orbiting the body", "venom-dripping oversized fangs",
    "a majestic feathered crest", "rune-carved glowing shell plates", "a blazing fiery mane",
    "ice frost covering the shoulders", "smoke pouring from the nostrils", "one huge mutated muscular arm",
]
_POSES = [
    "roaring triumphantly at the sky", "charging forward aggressively", "rearing up on its hind legs",
    "crouched low ready to pounce", "striking a heroic battle stance", "mid-leap attack pose",
    "standing proudly on a rock", "unleashing its battle cry",
]
_SETTINGS = [
    "on a volcanic ridge at dusk", "inside a glowing purple crystal cave",
    "on the purple moon surface under a giant green planet in the sky",
    "in a neon-lit alien arena", "in a bioluminescent alien swamp", "on a floating rock island in a nebula sky",
]
_THEMES = [
    ("golden royal armor plates, glowing gold runes, majestic champion", "Prime", "#ffd36b"),
    ("purple crystal growths all over the body, glowing amethyst shards", "Cristal", "#c55aff"),
    ("pale silver-white lunar skin, icy blue bioluminescent glow", "Lunaire", "#bfe8ff"),
    ("molten lava veins, glowing orange cracks, ember particles", "Magma", "#ff7a3c"),
    ("spectral ghostly translucent body, cyan ethereal glow", "Spectral", "#40f0ff"),
    ("pitch black void skin, glowing crimson cracks and eyes", "Obsidienne", "#ff3355"),
]
_TIER_STYLE = {
    2: "mega evolved form, larger and even more elaborate",
    3: "ancient colossal alpha form, extremely elaborate",
    4: "godlike mythical form, majestic and divine",
}
_ROMAN = ["II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


class FuseIn(BaseModel):
    walletAddress: str
    species: str
    tier: int = 1
    themeIdx: int | None = None


@router.post("/api/game/fuse")
async def game_fuse(data: FuseIn):
    """Fusion de cartes Nébula : génère la variante IA (1 token), retourne l'URL + l'identité."""
    w = (data.walletAddress or "").lower().strip()
    if not w:
        raise HTTPException(status_code=400, detail="walletAddress requis")
    if data.species not in _SPECIES:
        raise HTTPException(status_code=400, detail="Espèce inconnue")
    tier = max(1, min(10, int(data.tier or 1)))

    tokens_needed = REFUSION_COST_TOKENS if tier >= 2 else FUSION_COST_TOKENS
    balance = await get_user_balance(w)
    if balance < tokens_needed:
        raise HTTPException(status_code=402, detail="Insufficient tokens")

    base_desc, disp = _SPECIES[data.species]
    # une re-fusion garde le thème de la lignée ; une fusion simple tire au hasard
    if tier > 1 and data.themeIdx is not None and 0 <= int(data.themeIdx) < len(_THEMES):
        theme_idx = int(data.themeIdx)
    else:
        theme_idx = random.randrange(len(_THEMES))
    frag, suffix, color = _THEMES[theme_idx]

    parts = [base_desc, frag]
    if tier > 1:
        parts.append(_TIER_STYLE.get(tier, "transcendent cosmic deity form, unimaginably elaborate"))
    parts += random.sample(_TRAITS, 2) + [random.choice(_POSES), random.choice(_SETTINGS),
             "unique legendary fusion creature, vibrant detailed concept art, dark fantasy alien style"]
    prompt = ", ".join(parts)

    try:
        gen_fn = wavespeed.generate_image_hd if tier >= 2 else wavespeed.generate_image
        url = await asyncio.get_event_loop().run_in_executor(None, gen_fn, prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    # débit APRÈS succès (comme /api/generate/image)
    if not await consume_user_tokens(w, tokens_needed, "image", f"[nebula-fusion t{tier}] {prompt[:180]}"):
        raise HTTPException(status_code=402, detail="Insufficient tokens")

    sp_name = f"{disp} {suffix}" + (f" {_ROMAN[tier - 2]}" if tier > 1 else "")
    return {
        "success": True,
        "url": url,
        "spName": sp_name,
        "color": color,
        "tier": tier,
        "themeIdx": theme_idx,
        "balance": balance - tokens_needed,
    }


# ============================== ARÈNE EN LIGNE (JcJ asynchrone) ==============================

ALLOWED_SPECIES = set(_SPECIES)
DECK_SIZE = 20

_DDL = """
CREATE TABLE IF NOT EXISTS arena_players (
    wallet_address VARCHAR(255) PRIMARY KEY,
    nickname VARCHAR(64),
    deck TEXT NOT NULL,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
)
"""


def _ensure_table():
    with engine.begin() as conn:
        conn.execute(text(_DDL))


def _clean_wallet(w: str) -> str:
    return (w or "").lower().strip()


def _clean_deck(deck: list) -> list:
    if not isinstance(deck, list) or len(deck) != DECK_SIZE:
        raise HTTPException(status_code=400, detail=f"Le deck doit contenir exactement {DECK_SIZE} cartes")
    out = []
    for c in deck:
        sp = str(c.get("sp", "")).lower()
        if sp not in ALLOWED_SPECIES:
            raise HTTPException(status_code=400, detail=f"Espèce inconnue: {sp}")
        out.append({
            "sp": sp,
            "lvl": max(1, min(50, int(c.get("lvl", 1)))),
            "name": str(c.get("name", ""))[:40],
            "tier": max(0, min(10, int(c.get("tier", 0) or 0))),
        })
    return out


class DeckIn(BaseModel):
    walletAddress: str
    deck: list
    nickname: str | None = None


class ResultIn(BaseModel):
    walletAddress: str
    result: str  # "win" | "lose" | "tie"


@router.post("/api/arena/deck")
async def arena_save_deck(data: DeckIn):
    w = _clean_wallet(data.walletAddress)
    if not w:
        raise HTTPException(status_code=400, detail="walletAddress requis")
    deck = _clean_deck(data.deck)
    _ensure_table()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO arena_players (wallet_address, nickname, deck, updated_at)
                VALUES (:w, :n, :d, CURRENT_TIMESTAMP)
                ON CONFLICT (wallet_address)
                DO UPDATE SET deck = :d, nickname = COALESCE(:n, arena_players.nickname),
                              updated_at = CURRENT_TIMESTAMP
            """),
            {"w": w, "n": (data.nickname or "")[:64] or None, "d": json.dumps(deck)},
        )
    return {"success": True}


@router.get("/api/arena/opponent/{wallet}")
async def arena_opponent(wallet: str):
    w = _clean_wallet(wallet)
    _ensure_table()
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT wallet_address, nickname, deck FROM arena_players
                WHERE wallet_address != :w
                  AND updated_at > :since
                ORDER BY RANDOM() LIMIT 1
            """),
            {"w": w, "since": datetime.utcnow() - timedelta(days=90)},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Aucun adversaire en ligne pour le moment")
    name = row[1] or (row[0][:6] + "…" + row[0][-4:])
    return {"success": True, "wallet": row[0], "name": name, "deck": json.loads(row[2])}


@router.post("/api/arena/result")
async def arena_result(data: ResultIn):
    w = _clean_wallet(data.walletAddress)
    col = {"win": "wins", "lose": "losses", "tie": "ties"}.get(data.result)
    if not w or not col:
        raise HTTPException(status_code=400, detail="result doit être win | lose | tie")
    _ensure_table()
    with engine.begin() as conn:
        conn.execute(
            text(f"""
                INSERT INTO arena_players (wallet_address, deck, {col}, updated_at)
                VALUES (:w, '[]', 1, CURRENT_TIMESTAMP)
                ON CONFLICT (wallet_address)
                DO UPDATE SET {col} = arena_players.{col} + 1
            """),
            {"w": w},
        )
    return {"success": True}


@router.get("/api/arena/leaderboard")
async def arena_leaderboard():
    _ensure_table()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT wallet_address, nickname, wins, losses, ties FROM arena_players
                WHERE deck != '[]'
                ORDER BY wins DESC, losses ASC, updated_at DESC
                LIMIT 20
            """)
        ).fetchall()
    return {
        "success": True,
        "players": [
            {
                "wallet": r[0],
                "name": r[1] or (r[0][:6] + "…" + r[0][-4:]),
                "wins": r[2], "losses": r[3], "ties": r[4],
            }
            for r in rows
        ],
    }
