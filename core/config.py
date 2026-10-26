import os
import shutil
import sys
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_BASE = Path("/tmp") if (os.environ.get("VERCEL") == "1" or not os.access(str(BASE_DIR), os.W_OK)) else BASE_DIR

CACHE_DIR = STORAGE_BASE / "cache"
TRANSCRIPT_CACHE_DIR = CACHE_DIR / "transcripts"
MEDIA_CACHE_DIR = CACHE_DIR / "media"
DOWNLOADS_DIR = STORAGE_BASE / "downloads"
SHORTS_DIR = STORAGE_BASE / "shorts"
TEMP_DIR = STORAGE_BASE / "temp"

for p in [CACHE_DIR, TRANSCRIPT_CACHE_DIR, MEDIA_CACHE_DIR, DOWNLOADS_DIR, SHORTS_DIR, TEMP_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# Performance & Target Settings
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30
MAX_SHORT_DURATION = 60
MIN_SHORT_DURATION = 15

# Detect ffmpeg path
FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE_BIN = shutil.which("ffprobe") or "ffprobe"

FFMPEG_PATH = FFMPEG_BIN
FFPROBE_PATH = FFPROBE_BIN

