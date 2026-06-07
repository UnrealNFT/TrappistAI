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
    """
    final_lyrics = lyrics if lyrics else "[Instrumental]"
    
    task_id = _submit("wavespeed-ai/heartmula/generate-music", {
        "lyrics": final_lyrics,
        "tags": tags,
        "seed": -1,
        "duration": 60  # 60 seconds (try to request longer duration)
    })
    return _poll(task_id, max_wait=600)


def generate_music_minimax(lyrics: str, tags: str = "electronic, dark, cinematic") -> str:
    """Generate music with MiniMax Music 2.5 (HD quality). Returns URL."""
    final_lyrics = lyrics if lyrics else "(Instrumental intro with building tension)\n(Instrumental section)"
    
    task_id = _submit("minimax/music-2.5", {
        "prompt": tags,
        "lyrics": final_lyrics,
        "bitrate": 256000,
        "sample_rate": 44100,
        "duration": 60  # 60 seconds
    })
    return _poll(task_id, max_wait=600)


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
