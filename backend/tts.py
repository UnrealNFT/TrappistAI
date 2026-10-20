"""
Text-to-Speech module — Microsoft Edge TTS (free, no API key required).

Public API:
- VOICES: dict of named voices (fr/en × female/male)
- resolve_voice(requested, text) -> edge-tts voice id (auto-detects FR/EN)
- synthesize(text, voice=None, out_path=None) -> MP3 path (async)
- mp3_to_ogg(mp3_path, out_path=None) -> OGG/Opus path (Telegram voice notes)
"""
import os
import re
import subprocess
import tempfile

try:
    import edge_tts
    TTS_AVAILABLE = True
except ImportError as e:  # pragma: no cover
    TTS_AVAILABLE = False
    print(f"⚠️ edge-tts not available: {e}")


# Named voices exposed to the API / bot
VOICES = {
    "fr-female": "fr-FR-DeniseNeural",
    "fr-male": "fr-FR-HenriNeural",
    "en-female": "en-US-AriaNeural",
    "en-male": "en-US-GuyNeural",
}
DEFAULT_VOICE = VOICES["fr-female"]

# Max characters per synthesis (keeps latency + payload size reasonable)
MAX_CHARS = 2000

_FR_HINT = re.compile(
    r"[àâäçéèêëîïôöùûüœ]"
    r"|\b(le|la|les|un|une|des|du|de|et|est|je|tu|il|elle|nous|vous|ils|"
    r"pour|avec|sur|dans|pas|qui|que|quoi|bonjour|salut|merci|oui|non)\b",
    re.IGNORECASE,
)
_EN_HINT = re.compile(
    r"\b(the|a|an|is|are|was|and|or|you|i|we|they|he|she|it|"
    r"hello|hi|please|thanks|yes|no|what|how|with|from|this|that)\b",
    re.IGNORECASE,
)


def detect_voice(text: str) -> str:
    """Pick a default voice based on the dominant language (FR vs EN)."""
    fr_score = len(_FR_HINT.findall(text))
    en_score = len(_EN_HINT.findall(text))
    return VOICES["fr-female"] if fr_score >= en_score else VOICES["en-female"]


def resolve_voice(requested: str = None, text: str = "") -> str:
    """Resolve a requested voice name/id to a valid edge-tts voice id.

    Accepts: a key of VOICES ('fr-female'), a raw edge-tts voice id
    ('fr-FR-DeniseNeural'), 'auto'/None (language detection), anything else
    falls back to detection.
    """
    if requested:
        req = requested.strip()
        if req in VOICES:
            return VOICES[req]
        if re.match(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z0-9]+Neural$", req):
            return req
    return detect_voice(text) if text else DEFAULT_VOICE


async def synthesize(text: str, voice: str = None, out_path: str = None) -> str:
    """Synthesize text to an MP3 file. Returns the file path.

    Args:
        text: text to speak (truncated to MAX_CHARS)
        voice: voice key ('fr-female'), raw voice id, or None for auto-detect
        out_path: destination MP3 path (temp file if None)
    """
    if not TTS_AVAILABLE:
        raise RuntimeError("edge-tts package is not installed")

    text = (text or "").strip()
    if not text:
        raise ValueError("Text is empty")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    voice_id = resolve_voice(voice, text)

    if out_path is None:
        fd, out_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(out_path)

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("TTS produced no audio")
    return out_path


def mp3_to_ogg(mp3_path: str, out_path: str = None) -> str:
    """Convert MP3 → OGG/Opus (Telegram voice-note format) using the bundled
    static ffmpeg (imageio-ffmpeg, no system ffmpeg needed)."""
    import imageio_ffmpeg

    if out_path is None:
        fd, out_path = tempfile.mkstemp(suffix=".ogg")
        os.close(fd)

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "48k", out_path]
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="ignore")[-300:]
        raise RuntimeError(f"ffmpeg failed: {err}")
    return out_path


if __name__ == "__main__":
    import asyncio

    async def _test():
        path = await synthesize("Bonjour, ceci est un test de synthèse vocale.")
        print(f"✅ TTS ok: {path} ({os.path.getsize(path)} bytes)")
        ogg = mp3_to_ogg(path)
        print(f"✅ OGG ok: {ogg} ({os.path.getsize(ogg)} bytes)")

    asyncio.run(_test())
