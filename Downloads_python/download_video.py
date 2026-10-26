import sys
import os
from downloader_engine import download_media, get_video_info

def download_video(url, resolution=1080, format="mp4"):
    return download_media(url, media_type="video", resolution=resolution, video_format=format)

def download_audio(url, audio_format="mp3", quality="320k"):
    return download_media(url, media_type="audio", audio_format=audio_format, audio_quality=quality)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Please provide YouTube URL")
        print("Example:")
        print("python download_video.py https://youtube.com/watch?v=XXXX [resolution: 1080|720|480|audio]")
        exit()

    url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "1080"

    if mode.lower() == "audio":
        print(f"🎵 Downloading best quality MP3 audio from {url}...")
        res = download_audio(url)
        print(f"✅ Audio downloaded: {res['filepath']}")
    else:
        try:
            res_val = int(mode)
        except ValueError:
            res_val = 1080
        print(f"🎬 Downloading {res_val}p video from {url}...")
        res = download_video(url, resolution=res_val)
        print(f"✅ Video downloaded: {res['filepath']}")