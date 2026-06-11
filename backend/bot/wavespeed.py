"""WaveSpeed API client — image (FLUX) + music (HeartMuLa)."""
import os
import time
import requests

BASE = "https://api.wavespeed.ai/api/v3"

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
    r = requests.post(f"{BASE}/{endpoint}", json=payload, headers=HEADERS(), timeout=30)
    r.raise_for_status()
    data = r.json()
    task_id = data["data"]["id"]
    return task_id


def _poll(task_id: str, max_wait: int = 180) -> str:
    """Poll until completed; return output URL."""
    url = f"{BASE}/predictions/{task_id}/result"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        r = requests.get(url, headers=HEADERS(), timeout=30)
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
    task_id = _submit("wavespeed-ai/flux-schnell", {
        "prompt": prompt,
        "size": "1024x1024",
        "num_inference_steps": 4,
    })
    return _poll(task_id, max_wait=60)


def generate_music(lyrics: str, tags: str = "electronic, dark, cinematic, cyberpunk, energetic, 120bpm") -> str:
    """Generate music with HeartMuLa. Returns URL.
    
    For instrumental music, pass empty string for lyrics - it will be converted to [Instrumental].
    """
    # WaveSpeed API requires 'lyrics' field - use placeholder for instrumental
    final_lyrics = lyrics if lyrics else "[Instrumental]"
    
    task_id = _submit("wavespeed-ai/heartmula/generate-music", {
        "lyrics": final_lyrics,
        "tags": tags,
        "seed": -1,
    })
    return _poll(task_id, max_wait=600)


def generate_music_minimax(lyrics: str, tags: str = "electronic, dark, cinematic, cyberpunk, energetic, 120bpm") -> str:
    """Generate music with MiniMax Music 2.5 (HD quality). Returns URL.
    
    MiniMax requires both prompt (tags/style) and lyrics fields.
    For instrumental, use explicit markers like '(Instrumental intro)'.
    """
    # MiniMax uses 'prompt' for style/tags and requires lyrics
    final_lyrics = lyrics if lyrics else "(Instrumental intro with building tension)\n(Instrumental section)"
    
    task_id = _submit("minimax/music-2.5", {
        "prompt": tags,
        "lyrics": final_lyrics,
        "bitrate": 256000,
        "sample_rate": 44100,
    })
    return _poll(task_id, max_wait=600)


def generate_sam3_mask(image_url: str, prompt: str = "the person") -> str:
    """Generate segmentation mask with SAM3. Returns mask image URL."""
    task_id = _submit("wavespeed-ai/sam3-image", {
        "image": image_url,
        "prompt": prompt,
        "apply_mask": False,
        "output_format": "png",
    })
    return _poll(task_id, max_wait=60)


def generate_3d_from_image(image_url: str, mask_url: str = None) -> str:
    """Generate 3D model with HunyuanV3.1 (cheap, no texture). Returns GLB URL."""
    task_id = _submit("wavespeed-ai/hunyuan-3d-v3.1/image-to-3d-rapid", {
        "image": image_url,
    })
    return _poll(task_id, max_wait=300)


def generate_3d_with_texture(image_url: str) -> str:
    """Generate 3D model with Tripo3D v2.5 (with texture/color). Returns GLB URL."""
    task_id = _submit("tripo3d/v2.5/image-to-3d", {
        "image": image_url,
    })
    return _poll(task_id, max_wait=300)
