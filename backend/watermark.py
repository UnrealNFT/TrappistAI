"""
Adds a "trappist.land" watermark (Trappist logo + text) to generated images.

Used to brand images produced during the x402 testnet demo so every shared
image promotes trappist.land. Fails gracefully: if Pillow is missing, the
image can't be fetched, or R2 isn't configured, the original URL is returned
untouched so nothing breaks.

Toggle with env WATERMARK_ENABLED ("true"/"false", default true).
"""
import io
import os

import requests

import r2_storage

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except Exception as _e:  # pragma: no cover
    _PIL_OK = False
    print(f"⚠️ Pillow not available, watermark disabled: {_e}")

WATERMARK_ENABLED = os.getenv("WATERMARK_ENABLED", "true").lower() == "true"
WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "trappist.land")

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "trappist1.png")
_FONT_CANDIDATES = [
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "arialbd.ttf",
]


def _load_font(size: int):
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10
    except Exception:
        return ImageFont.load_default()


def _apply(content: bytes) -> bytes:
    """Return PNG bytes of the image with the trappist.land watermark."""
    img = Image.open(io.BytesIO(content)).convert("RGBA")
    width, height = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(18, width // 28)
    font = _load_font(font_size)
    margin = max(10, width // 50)

    text = WATERMARK_TEXT
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Optional logo to the left of the text
    logo_img = None
    logo_w = 0
    if os.path.exists(_LOGO_PATH):
        try:
            logo = Image.open(_LOGO_PATH).convert("RGBA")
            logo_h = font_size + 6
            logo_w_scaled = max(1, int(logo.width * (logo_h / logo.height)))
            logo_img = logo.resize((logo_w_scaled, logo_h))
            # 80% opacity so it reads as a watermark
            alpha = logo_img.split()[3].point(lambda a: int(a * 0.8))
            logo_img.putalpha(alpha)
            logo_w = logo_w_scaled + 8
        except Exception:
            logo_img = None
            logo_w = 0

    block_w = logo_w + text_w
    x = width - block_w - margin
    y = height - text_h - margin

    if logo_img is not None:
        logo_y = y - (logo_img.height - text_h) // 2
        overlay.paste(logo_img, (x, logo_y), logo_img)

    text_x = x + logo_w
    # shadow for readability on any background, then the white text
    draw.text((text_x + 1, y + 1), text, font=font, fill=(0, 0, 0, 170))
    draw.text((text_x, y), text, font=font, fill=(255, 255, 255, 215))

    out = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def process_image_url(source_url: str) -> str:
    """
    Download `source_url`, stamp the trappist.land watermark, and upload the
    result to R2. Returns the new permanent URL, or the original URL on any
    failure / when watermarking is disabled.
    """
    if not source_url or not WATERMARK_ENABLED or not _PIL_OK:
        return source_url
    try:
        resp = requests.get(source_url, timeout=120)
        resp.raise_for_status()
        watermarked = _apply(resp.content)
        new_url = r2_storage.upload_bytes(watermarked, "image", "image/png")
        return new_url or source_url
    except Exception as e:
        print(f"⚠️ watermark failed ({e}); keeping original URL")
        return source_url
