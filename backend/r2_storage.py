"""
Cloudflare R2 storage helper.

Downloads temporary WaveSpeed/CloudFront URLs and re-uploads them to a
Cloudflare R2 bucket so the asset stays available permanently.

R2 is S3-compatible, so we use boto3.

Required environment variables (set on Render):
    R2_ACCOUNT_ID         your Cloudflare account id
    R2_ACCESS_KEY_ID      R2 API token access key
    R2_SECRET_ACCESS_KEY  R2 API token secret key
    R2_BUCKET             bucket name (e.g. trappist-images)
    R2_PUBLIC_URL         public base url of the bucket, no trailing slash
                          (r2.dev dev url or your custom domain)

If any variable is missing, upload_asset() simply returns the original URL
so nothing breaks (graceful degradation).
"""
import os
import uuid
import mimetypes

import requests

try:
    import boto3
    from botocore.config import Config as _BotoConfig
    _BOTO_AVAILABLE = True
except Exception as _e:  # pragma: no cover
    _BOTO_AVAILABLE = False
    print(f"⚠️ boto3 not available: {_e}")


R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

# Default file extension per asset type
_EXT = {"image": ".png", "music": ".mp3", "3d": ".glb"}


def is_configured() -> bool:
    """True if all R2 settings are present and boto3 is importable."""
    return bool(
        _BOTO_AVAILABLE
        and R2_ACCOUNT_ID
        and R2_ACCESS_KEY_ID
        and R2_SECRET_ACCESS_KEY
        and R2_BUCKET
        and R2_PUBLIC_URL
    )


def _client():
    """Create an S3 client pointed at the R2 endpoint."""
    endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=_BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def _guess_ext(url: str, content_type: str, asset_type: str) -> str:
    """Pick a sensible file extension."""
    # 1. from URL path
    path = url.split("?")[0]
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".mp4", ".glb"):
        if path.lower().endswith(ext):
            return ext
    # 2. from content-type
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    # 3. fallback by asset type
    return _EXT.get(asset_type, ".bin")


def upload_asset(source_url: str, asset_type: str = "image") -> str:
    """
    Download `source_url` and upload it to R2.

    Returns the permanent public R2 URL on success, or the original
    `source_url` if R2 is not configured or anything fails.
    """
    if not source_url:
        return source_url

    if not is_configured():
        # Not set up yet — keep the temporary URL so nothing breaks.
        return source_url

    try:
        resp = requests.get(source_url, timeout=120)
        resp.raise_for_status()
        content = resp.content
        content_type = resp.headers.get("Content-Type", "")

        ext = _guess_ext(source_url, content_type, asset_type)
        key = f"{asset_type}/{uuid.uuid4().hex}{ext}"

        if not content_type:
            content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"

        _client().put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        permanent_url = f"{R2_PUBLIC_URL}/{key}"
        print(f"✅ Uploaded to R2: {permanent_url}")
        return permanent_url

    except Exception as e:
        print(f"⚠️ R2 upload failed ({e}); keeping original URL")
        return source_url


def delete_asset(asset_url: str) -> bool:
    """
    Best-effort delete of an object from R2 given its public URL.

    Returns True if a delete request was issued, False otherwise.
    Only deletes objects that live under our R2_PUBLIC_URL (our own bucket).
    """
    if not asset_url or not is_configured():
        return False

    # Only handle URLs that belong to our public bucket.
    if not asset_url.startswith(R2_PUBLIC_URL + "/"):
        return False

    try:
        key = asset_url[len(R2_PUBLIC_URL) + 1:].split("?")[0]
        if not key:
            return False
        _client().delete_object(Bucket=R2_BUCKET, Key=key)
        print(f"🗑️ Deleted from R2: {key}")
        return True
    except Exception as e:
        print(f"⚠️ R2 delete failed ({e})")
        return False
