"""WaveSpeed API client — image (FLUX) + music (HeartMuLa/MiniMax) + 3D"""
import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE = "https://api.wavespeed.ai/api/v3"
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

HEADERS = lambda: {
    "Authorization": f"Bearer {os.getenv('WAVESPEED_API_KEY', '')}",
    "Content-Type": "application/json",
}


class TaskTimeout(Exception):
    """Raised when polling exceeds max_wait. task_id is preserved for retry."""
    def __init__(self, task_id: str, waited: int):
        super().__init__(f"Task {task_id} timed out after {waited}s")
        self.task_id = task_id


def _submit(endpoint: str, payload: dict) -> str:
    """Submit a task and return its ID."""
    r = requests.post(f"{BASE}/{endpoint}", json=payload, headers=HEADERS(), timeout=360)
    r.raise_for_status()
    data = r.json()
    task_id = data["data"]["id"]
    return task_id


def _poll(task_id: str, max_wait: int = 180) -> str:
    """Poll until completed; return output URL."""
    url = f"{BASE}/predictions/{task_id}/result"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        r = requests.get(url, headers=HEADERS(), timeout=360)
        r.raise_for_status()
        data = r.json()["data"]
        status = data.get("status")
        if status == "completed":
            outputs = data.get("outputs", [])
            if outputs:
                return outputs[0]
            raise RuntimeError("completed but no output URL")
        if status == "failed":
            raise RuntimeError(f"Task failed: {data.get('error')}")
        time.sleep(3)
    raise TaskTimeout(task_id, max_wait)


def fetch_result(task_id: str, max_wait: int = 1200) -> str:
    """Poll an already-submitted task (e.g. after a timeout). Returns URL."""
    return _poll(task_id, max_wait=max_wait)


def generate_image(prompt: str) -> str:
    """Generate image with FLUX.1-schnell. Returns URL."""
    if TEST_MODE:
        print(f"[MOCK] Generating image: {prompt[:50]}...")
        return "https://picsum.photos/1024/1024"  # Mock image URL
    
    task_id = _submit("wavespeed-ai/flux-schnell", {
        "prompt": prompt,
        "size": "1024x1024",
        "num_inference_steps": 4,
    })
    return _poll(task_id, max_wait=60)


def generate_music(lyrics: str, tags: str = "electronic, dark, cinematic") -> str:
    """Generate music with HeartMuLa. Returns URL.

    For instrumental music, pass empty string for lyrics.
    Note: HeartMuLa has NO duration param — length is driven by lyrics + structure markers.
    """
    # Pure instrumental: use ONLY instrumental section markers (no vocal sections)
    final_lyrics = lyrics if lyrics else (
        "[intro-medium]\n[inst-medium]\n[inst-medium]\n[inst-medium]\n[outro-medium]"
    )

    task_id = _submit("wavespeed-ai/heartmula/generate-music", {
        "lyrics": final_lyrics,
        "tags": tags,
        "seed": -1,
    })
    return _poll(task_id, max_wait=600)


def _to_minimax_markers(text: str) -> str:
    """MiniMax uses (parentheses) markers, NOT [brackets]. Convert them."""
    import re
    return re.sub(r"\[([^\]]+)\]", lambda m: f"({m.group(1)})", text)


def generate_music_minimax(lyrics: str, tags: str = "electronic, dark, cinematic") -> str:
    """Generate music with MiniMax Music 2.5 (HD quality). Returns URL.

    MiniMax always sings the provided lyrics and uses (parentheses) markers.
    Note: NO duration param — length is driven by lyrics + structure.
    """
    if lyrics:
        final_lyrics = _to_minimax_markers(lyrics)
    else:
        final_lyrics = (
            "(Instrumental intro building up)\n"
            "(Instrumental main section)\n"
            "(Instrumental break)\n"
            "(Instrumental outro)"
        )

    task_id = _submit("minimax/music-2.5", {
        "prompt": tags,
        "lyrics": final_lyrics,
        "bitrate": 256000,
        "sample_rate": 44100,
    })
    return _poll(task_id, max_wait=600)


def generate_3d_from_image(image_url: str) -> str:
    """Generate 3D model with HunyuanV3.1 (no texture, monochrome). Returns GLB URL."""
    if TEST_MODE:
        print(f"[MOCK] Generating 3D (no texture) from image...")
        return "https://example.com/model_notex.glb"  # Mock GLB URL
    
    task_id = _submit("wavespeed-ai/hunyuan-3d-v3.1/image-to-3d-rapid", {
        "image": image_url,
    })
    return _poll(task_id, max_wait=600)


def generate_3d_with_texture(image_url: str) -> str:
    """Generate 3D model with Tripo3D v2.5 (with texture/color). Returns GLB URL."""
    if TEST_MODE:
        print(f"[MOCK] Generating 3D (with texture) from image...")
        return "https://example.com/model_tex.glb"  # Mock GLB URL
    
    task_id = _submit("tripo3d/v2.5/image-to-3d", {
        "image": image_url,
    })
    return _poll(task_id, max_wait=600)


def generate_video_seedance_t2v(
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    fast: bool = True,
    generate_audio: bool = True,
) -> str:
    """Text-to-video with ByteDance Seedance v1.5 Pro (WaveSpeed). Returns MP4 URL.

    fast=True uses the cheaper/quicker '-fast' variant. duration in seconds (5/10...).
    generate_audio=False is cheaper (no soundtrack generation).
    """
    if TEST_MODE:
        print(f"[MOCK] Generating video (t2v): {prompt[:50]}...")
        return "https://example.com/video.mp4"  # Mock MP4 URL

    slug = "text-to-video-fast" if fast else "text-to-video"
    task_id = _submit(f"bytedance/seedance-v1.5-pro/{slug}", {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "generate_audio": generate_audio,
        "seed": -1,
    })
    return _poll(task_id, max_wait=900)


def generate_video_seedance_i2v(
    image_url: str,
    prompt: str = "",
    duration: int = 5,
    aspect_ratio: str = "16:9",
    camera_fixed: bool = False,
    last_image: str = None,
    fast: bool = True,
    generate_audio: bool = True,
) -> str:
    """Image-to-video with ByteDance Seedance v1.5 Pro (WaveSpeed). Returns MP4 URL.

    Animates a starting image with a motion-focused prompt. last_image optionally
    guides the ending frame. camera_fixed locks the camera for stable framing.
    generate_audio=False is cheaper (no soundtrack generation).
    """
    if TEST_MODE:
        print(f"[MOCK] Generating video (i2v) from image...")
        return "https://example.com/video.mp4"  # Mock MP4 URL

    slug = "image-to-video-fast" if fast else "image-to-video"
    payload = {
        "image": image_url,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "camera_fixed": camera_fixed,
        "generate_audio": generate_audio,
        "seed": -1,
    }
    if last_image:
        payload["last_image"] = last_image
    task_id = _submit(f"bytedance/seedance-v1.5-pro/{slug}", payload)
    return _poll(task_id, max_wait=900)


if __name__ == "__main__":
    """Test WaveSpeed connection"""
    print("Testing WaveSpeed API...")
    try:
        # Test image generation
        print("Generating test image...")
        url = generate_image("A beautiful sunset over mountains")
        print(f"✅ Image generated: {url}")
    except Exception as e:
        print(f"❌ WaveSpeed test failed: {e}")
