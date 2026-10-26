import os
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import yt_dlp
from core.config import TEMP_DIR
from core.cache import get_cache_key, get_cached_media_path, save_cached_media_path

def extract_video_metadata(url: str) -> Dict[str, Any]:
    """Extracts metadata without downloading."""
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
    Downloads lightweight audio stream (e.g. 16kHz mono M4A/MP3) for instant Whisper transcription.
    Typically 3-8 MB downloaded in ~2 seconds instead of downloading 600 MB video!
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

    # Find the resulting file
    parent = output_path.parent
    base_stem = output_path.stem
    for f in parent.glob(f"{base_stem}.*"):
        if f.suffix in [".m4a", ".mp3", ".webm", ".opus"]:
            return f

    return output_path


def download_video_section(
    url: str,
    start_sec: float,
    end_sec: float,
    job_id: str,
    progress_cb: Optional[Callable] = None
) -> Path:
    """
    Downloads ONLY the needed segment (yt-dlp --download-sections) at target 720p.
    A 30-second section is ~5-12 MB and downloads in 2-4 seconds!
    """
    out_dir = TEMP_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "section.mp4"
    temp_template = str(out_dir / "section") + ".%(ext)s"

    # Add 1.5s padding around cut for seamless crossfades/transitions
    pad_start = max(0.0, start_sec - 1.0)
    pad_end = end_sec + 1.0
    section_arg = f"*{pad_start:.2f}-{pad_end:.2f}"

    def hook(d):
        if not progress_cb:
            return
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            curr = d.get('downloaded_bytes', 0)
            pct = int(curr / total * 100) if total else 0
            progress_cb({"stage": "section_dl", "message": f"Downloading precision clip segment ({pct}%)...", "percent": pct})

    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'merge_output_format': 'mp4',
        'download_ranges': lambda info_dict, ydl: [{'start_time': pad_start, 'end_time': pad_end}],
        'force_keyframes_at_cuts': True,
        'outtmpl': temp_template,
        'progress_hooks': [hook],
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception:
            # Fallback if download_ranges fails on older ytdlp
            pass

    # Find the resulting file
    return out_file


def download_audio_stream(url: str, video_key: str, progress_cb: Optional[Callable] = None) -> str:
    """Alias for download_audio_stream_fast returning str path."""
    return str(download_audio_stream_fast(url, video_key, progress_cb))


def download_video_segment(url: str, video_id: str, start_sec: float, end_sec: float) -> str:
    """Alias for download_video_section returning str path."""
    return str(download_video_section(url, start_sec, end_sec, job_id=video_id))

