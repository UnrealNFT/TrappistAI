"""
MP3 → MP4 conversion using a bundled static ffmpeg (imageio-ffmpeg).
No system ffmpeg / apt required — works in any Python environment.

Public API:
- convert_to_mp4(audio_path, image_path=None, out_path=None) -> mp4 path
"""

import os
import subprocess
import tempfile

import imageio_ffmpeg


def _ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def convert_to_mp4(audio_path: str, image_path: str = None, out_path: str = None) -> str:
    """Combine an MP3 with a still image (or a black background) into an MP4.
    Returns the path to the generated MP4."""
    if out_path is None:
        fd, out_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)

    ff = _ffmpeg_exe()
    if image_path:
        cmd = [
            ff, "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            # even dimensions + cap width at 1280 (libx264 requires even sizes)
            "-vf", "scale='min(1280,iw)':-2",
            "-shortest",
            out_path,
        ]
    else:
        cmd = [
            ff, "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=2",
            "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            out_path,
        ]

    proc = subprocess.run(cmd, capture_output=True, timeout=300)
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="ignore")[-500:]
        raise RuntimeError(f"ffmpeg failed: {err}")
    return out_path
