import os
import re
import json
import time
from typing import Dict, Any, Optional, Callable
import yt_dlp

IS_VERCEL = os.environ.get("VERCEL") == "1"
BASE_DIR = "/tmp" if IS_VERCEL else os.path.abspath(".")

OUTPUT_DIR = os.path.join(BASE_DIR, "downloads")
SHORTS_DIR = os.path.join(BASE_DIR, "shorts")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

for d in [OUTPUT_DIR, SHORTS_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)


def format_bytes(num_bytes: Optional[float]) -> str:
    if not num_bytes:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def get_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts rich video metadata and available resolution/audio streams.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Could not fetch video information.")

        # If it's a playlist, take the first entry or summarize
        if 'entries' in info and info['entries']:
            entry = info['entries'][0]
        else:
            entry = info

        title = entry.get('title', 'Unknown Title')
        duration = entry.get('duration', 0)
        thumbnail = entry.get('thumbnail', '')
        uploader = entry.get('uploader') or entry.get('channel') or 'Unknown Creator'
        view_count = entry.get('view_count', 0)
        description = entry.get('description', '')
        video_id = entry.get('id', '')

        # Analyze available video resolutions
        raw_formats = entry.get('formats', [])
        resolutions_map = {}
        has_audio_stream = False

        for f in raw_formats:
            height = f.get('height')
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            filesize = f.get('filesize') or f.get('filesize_approx')

            if acodec and acodec != 'none':
                has_audio_stream = True

            if height and vcodec and vcodec != 'none':
                # Group by standard heights
                h_val = int(height)
                fps = f.get('fps') or 30
                ext = f.get('ext', 'mp4')

                # We prefer common resolutions
                if h_val not in resolutions_map or (filesize and filesize > (resolutions_map[h_val].get('filesize') or 0)):
                    quality_label = f"{h_val}p"
                    if h_val >= 2160:
                        tag = "4K Ultra HD"
                    elif h_val >= 1440:
                        tag = "2K Quad HD"
                    elif h_val >= 1080:
                        tag = "Full HD"
                    elif h_val >= 720:
                        tag = "HD"
                    elif h_val >= 480:
                        tag = "Standard (SD)"
                    else:
                        tag = "Low (Mobile)"

                    resolutions_map[h_val] = {
                        "height": h_val,
                        "label": quality_label,
                        "tag": tag,
                        "fps": int(fps),
                        "ext": ext,
                        "format_id": f.get('format_id'),
                        "filesize": filesize,
                        "size_formatted": format_bytes(filesize)
                    }

        # Sort resolutions descending
        sorted_resolutions = sorted(resolutions_map.values(), key=lambda x: x['height'], reverse=True)

        # Standard fallback resolutions if none detected
        if not sorted_resolutions:
            sorted_resolutions = [
                {"height": 1080, "label": "1080p", "tag": "Full HD", "fps": 60, "format_id": "bestvideo+bestaudio/best", "size_formatted": "Estimated"},
                {"height": 720, "label": "720p", "tag": "HD", "fps": 30, "format_id": "bestvideo[height<=720]+bestaudio/best", "size_formatted": "Estimated"},
                {"height": 480, "label": "480p", "tag": "SD", "fps": 30, "format_id": "bestvideo[height<=480]+bestaudio/best", "size_formatted": "Estimated"},
                {"height": 360, "label": "360p", "tag": "Mobile", "fps": 30, "format_id": "bestvideo[height<=360]+bestaudio/best", "size_formatted": "Estimated"},
            ]

        audio_options = [
            {"format": "mp3", "quality": "320k", "label": "MP3 - 320 kbps (High Quality Studio)"},
            {"format": "mp3", "quality": "256k", "label": "MP3 - 256 kbps (Premium Audio)"},
            {"format": "mp3", "quality": "192k", "label": "MP3 - 192 kbps (Standard Audio)"},
            {"format": "mp3", "quality": "128k", "label": "MP3 - 128 kbps (Lightweight)"},
            {"format": "m4a", "quality": "best", "label": "M4A (Apple AAC Original Stream)"},
            {"format": "wav", "quality": "lossless", "label": "WAV (Uncompressed Lossless)"},
            {"format": "flac", "quality": "lossless", "label": "FLAC (Hi-Res Audio Lossless)"},
            {"format": "opus", "quality": "best", "label": "OPUS (Modern Efficient Codec)"},
        ]

        return {
            "id": video_id,
            "url": url,
            "title": title,
            "duration": duration,
            "duration_formatted": format_duration(duration),
            "thumbnail": thumbnail,
            "uploader": uploader,
            "views": f"{view_count:,}" if view_count else "N/A",
            "description": description[:300] + ("..." if len(description) > 300 else ""),
            "resolutions": sorted_resolutions,
            "audio_options": audio_options,
            "has_audio": has_audio_stream
        }


def download_media(
    url: str,
    media_type: str = "video",
    resolution: int = 1080,
    video_format: str = "mp4",
    audio_format: str = "mp3",
    audio_quality: str = "320k",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Downloads video or audio with user-selected quality specifications.
    Emits live progress to progress_callback.
    """
    timestamp = int(time.time())
    
    def ydl_hook(d):
        if not progress_callback:
            return
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded / total * 100) if total > 0 else 0
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            progress_callback({
                "status": "downloading",
                "percent": round(percent, 1),
                "downloaded_str": format_bytes(downloaded),
                "total_str": format_bytes(total),
                "speed_str": f"{format_bytes(speed)}/s" if speed else "Calculating...",
                "eta_str": f"{eta}s" if eta else "Calculating..."
            })
        elif status == 'finished':
            progress_callback({
                "status": "processing",
                "percent": 99.0,
                "downloaded_str": "Done",
                "total_str": "Finalizing",
                "speed_str": "Merging streams",
                "eta_str": "A few seconds"
            })

    output_filename_template = f"%(title)s_{timestamp}.%(ext)s"
    output_filepath = os.path.join(OUTPUT_DIR, output_filename_template)

    if media_type == "audio":
        # Audio Extraction
        postprocessors = []
        if audio_format in ['mp3', 'm4a', 'flac', 'wav', 'opus']:
            pp = {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
            }
            if audio_quality not in ['best', 'lossless']:
                pp['preferredquality'] = audio_quality.replace('k', '')
            postprocessors.append(pp)

        # Embed thumbnail and metadata into audio
        postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_filepath,
            'progress_hooks': [ydl_hook],
            'postprocessors': postprocessors,
            'writethumbnail': False,
            'quiet': True,
            'no_warnings': True,
        }
    else:
        # Video Download with Quality Selection
        # Select best video stream matching or closest to selected resolution + best audio
        format_str = f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]/best"
        ydl_opts = {
            'format': format_str,
            'outtmpl': output_filepath,
            'merge_output_format': video_format,
            'progress_hooks': [ydl_hook],
            'postprocessors': [
                {'key': 'FFmpegMetadata', 'add_metadata': True}
            ],
            'quiet': True,
            'no_warnings': True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(result)
        
        # If converted to requested extension, adjust filename
        base, _ = os.path.splitext(filename)
        expected_ext = audio_format if media_type == "audio" else video_format
        final_file = f"{base}.{expected_ext}"
        
        if not os.path.exists(final_file):
            if os.path.exists(filename):
                final_file = filename
            else:
                # Find matching file in output dir
                for f in os.listdir(OUTPUT_DIR):
                    if str(timestamp) in f:
                        final_file = os.path.join(OUTPUT_DIR, f)
                        break

    if progress_callback:
        progress_callback({
            "status": "completed",
            "percent": 100.0,
            "downloaded_str": "Complete",
            "total_str": "100%",
            "speed_str": "-",
            "eta_str": "0s"
        })

    file_size = os.path.getsize(final_file) if os.path.exists(final_file) else 0

    return {
        "success": True,
        "title": result.get('title', 'Downloaded Media'),
        "filename": os.path.basename(final_file),
        "filepath": final_file,
        "size_str": format_bytes(file_size),
        "media_type": media_type,
        "thumbnail": result.get('thumbnail', '')
    }
