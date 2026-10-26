import json
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path
from core.config import TRANSCRIPT_CACHE_DIR, MEDIA_CACHE_DIR

def get_cache_key(url_or_id: str) -> str:
    """Generate a clean safe cache key from video URL or ID."""
    clean = url_or_id.strip()
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]

def save_transcript_cache(video_key: str, data: Dict[str, Any]) -> None:
    path = TRANSCRIPT_CACHE_DIR / f"{video_key}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to save transcript cache: {e}")

def load_transcript_cache(video_key: str) -> Optional[Dict[str, Any]]:
    path = TRANSCRIPT_CACHE_DIR / f"{video_key}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def set_cached_transcript(video_key: str, data: Dict[str, Any]) -> None:
    """Alias for save_transcript_cache."""
    save_transcript_cache(video_key, data)

def get_cached_transcript(video_key: str) -> Optional[Dict[str, Any]]:
    """Alias for load_transcript_cache."""
    return load_transcript_cache(video_key)

def get_cached_media_path(video_key: str, ext: str = "mp4") -> Optional[Path]:
    path = MEDIA_CACHE_DIR / f"{video_key}.{ext}"
    if path.exists() and path.stat().st_size > 1024:
        return path
    return None

def save_cached_media_path(video_key: str, ext: str = "mp4") -> Path:
    return MEDIA_CACHE_DIR / f"{video_key}.{ext}"
