import os
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import yt_dlp
from core.config import TEMP_DIR, MEDIA_CACHE_DIR
from core.cache import get_cache_key, get_cached_media_path, save_cached_media_path

def extract_video_metadata(url: str) -> Dict[str, Any]:
    """Extracts metadata and subtitles without downloading."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Could not extract metadata from URL.")
        if 'entries' in info and info['entries']:
            info = info['entries'][0]

        video_id = info.get('id', get_cache_key(url))
        return {
            "id": video_id,
            "cache_key": get_cache_key(video_id),
            "title": info.get('title', 'Unknown Title'),
            "duration": info.get('duration', 0),
            "thumbnail": info.get('thumbnail', ''),
            "uploader": info.get('uploader') or info.get('channel') or 'Creator',
            "view_count": info.get('view_count', 0),
            "license": info.get('license', 'Standard YouTube License'),
            "description": info.get('description', '')[:500],
            "raw_info": info
        }


def download_audio_stream_fast(url: str, video_key: str, progress_cb: Optional[Callable] = None) -> Path:
    """
    Downloads lightweight audio stream for Whisper fallback.
    """
    cached = get_cached_media_path(video_key, ext="m4a")
    if cached:
        if progress_cb:
            progress_cb({"stage": "cache", "message": "Using cached audio transcript stream...", "percent": 100})
        return cached

    output_path = save_cached_media_path(video_key, ext="m4a")
    temp_template = str(output_path).replace(".m4a", "") + ".%(ext)s"

    def hook(d):
        if not progress_cb:
            return
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            curr = d.get('downloaded_bytes', 0)
            pct = int(curr / total * 100) if total else 0
            progress_cb({"stage": "audio_dl", "message": f"Fetching audio track for AI analysis ({pct}%)...", "percent": pct})

    ydl_opts = {
        'format': 'ba/bestaudio',
        'outtmpl': temp_template,
        'progress_hooks': [hook],
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    parent = output_path.parent
    base_stem = output_path.stem
    for f in parent.glob(f"{base_stem}.*"):
        if f.suffix in [".m4a", ".mp3", ".webm", ".opus"]:
            return f

    return output_path


def get_or_download_source_video(
    url: str,
    video_id: str,
    progress_cb: Optional[Callable] = None
) -> str:
    """
    Downloads or retrieves the cached 720p source video once.
    Once cached, all subsequent shorts (Clip 1, 2, 3, 4, 5) cut directly
    from this local file in ~3-5 seconds with ZERO network latency!
    """
    MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached_source = MEDIA_CACHE_DIR / f"{video_id}_source.mp4"

    # If cached file exists and is larger than 1MB, reuse instantly
    if cached_source.exists() and cached_source.stat().st_size > 1024 * 1024:
        if progress_cb:
            progress_cb({"stage": "cache", "message": "Using cached source video...", "percent": 100})
        return str(cached_source)

    temp_template = str(MEDIA_CACHE_DIR / f"{video_id}_source") + ".%(ext)s"

    def hook(d):
        if not progress_cb:
            return
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            curr = d.get('downloaded_bytes', 0)
            pct = int(curr / total * 100) if total else 0
            progress_cb({"stage": "video_dl", "message": f"Buffering source video for high-speed clip generation ({pct}%)...", "percent": pct})

    ydl_opts = {
        # Prefer pre-muxed 720p MP4 or high compatibility progressive streams
        'format': 'best[height<=720][ext=mp4]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'merge_output_format': 'mp4',
        'outtmpl': temp_template,
        'progress_hooks': [hook],
        'quiet': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 4
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    for f in MEDIA_CACHE_DIR.glob(f"{video_id}_source.*"):
        if f.suffix in [".mp4", ".mkv", ".webm"]:
            return str(f)

    return str(cached_source)


def download_video_segment(
    url: str,
    video_id: str,
    start_sec: float,
    end_sec: float,
    progress_cb: Optional[Callable] = None
) -> str:
    """
    Returns source video path for rendering. Reuses cached source video
    so subsequent clips require 0.0s download time!
    """
    return get_or_download_source_video(url, video_id, progress_cb)


def download_audio_stream(url: str, video_key: str, progress_cb: Optional[Callable] = None) -> str:
    return str(download_audio_stream_fast(url, video_key, progress_cb))
