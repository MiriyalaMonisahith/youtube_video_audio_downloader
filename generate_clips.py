import os
import sys
import shutil
import subprocess
import zipfile
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List

from ai.transcript import get_segments
from ai.chunk_builder import build_chunks
from ai.clip_detector import find_best_clips
from video.cutter import cut_clip_vertical
from ai.captions import generate_srt
from ai.clip_ranker import rank_clips
import yt_dlp
from ai.hookdetector import boost_hook
from ai.title_generator import generate_title
from ai.hashtag_generator import generate_hashtags
from downloader_engine import SHORTS_DIR, TEMP_DIR, OUTPUT_DIR, format_bytes

FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


def download_youtube_video(
    url: str,
    output_path: str = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> str:
    """Downloads a YouTube video to temp directory using native Python yt_dlp with live progress hook."""
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "source_video.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    base_no_ext, _ = os.path.splitext(output_path)
    outtmpl = f"{base_no_ext}.%(ext)s"

    def ydl_hook(d):
        if not progress_callback:
            return
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            pct = (downloaded / total * 100) if total > 0 else 0
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            # Map download (0-100%) to pipeline progress (5-28%)
            pipe_pct = 5 + int(pct * 0.23)
            speed_txt = f"{speed / (1024*1024):.1f} MB/s" if speed else ""
            eta_txt = f"ETA: {int(eta)}s" if eta else ""
            size_txt = f"{downloaded / (1024*1024):.1f} / {total / (1024*1024):.1f} MB"

            progress_callback({
                "step": 1,
                "total_steps": 6,
                "message": f"Downloading source: {size_txt} ({pct:.0f}%) • {speed_txt} {eta_txt}".strip(),
                "percent": pipe_pct
            })
        elif status == 'finished':
            progress_callback({
                "step": 1,
                "total_steps": 6,
                "message": "Finalizing source video download...",
                "percent": 28
            })

    # For shorts generation, 720p is optimal (fast download, identical mobile 9:16 vertical quality)
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
        'progress_hooks': [ydl_hook],
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    final_path = f"{base_no_ext}.mp4"
    if not os.path.exists(final_path) and os.path.exists(output_path):
        final_path = output_path
    return final_path


def burn_subtitles_styled(clip_path: str, srt_path: str, final_path: str, style: str = "neon_yellow"):
    """
    Burns viral styled subtitles into vertical short.
    Uses proper escaping for Windows FFmpeg path parser.
    """
    escaped_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
    
    # Custom Subtitle Styling for Viral Shorts
    # Color codes in ASS format: &H00BBGGRR
    if style == "cyber_cyan":
        style_params = "Fontname=Arial,Fontsize=18,Bold=1,PrimaryColour=&H00FFFF00,OutlineColour=&H00000000,BorderStyle=3,Outline=2.5,Shadow=0,Alignment=2,MarginV=120"
    elif style == "classic_white":
        style_params = "Fontname=Arial,Fontsize=18,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2.5,Shadow=0,Alignment=2,MarginV=120"
    else:  # neon_yellow default
        style_params = "Fontname=Arial,Fontsize=19,Bold=1,PrimaryColour=&H0000E6FF,OutlineColour=&H00000000,BorderStyle=3,Outline=2.5,Shadow=0,Alignment=2,MarginV=120"

    vf_filter = f"subtitles='{escaped_srt}':force_style='{style_params}'"

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", clip_path,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "faster",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-shortest",
        final_path
    ]
    
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        # Fallback without subtitle filter if libass encounters issues
        print("Subtitles burning fallback without filter:", proc.stderr.decode('utf-8', errors='ignore')[-200:])
        shutil.copy(clip_path, final_path)


def main_pipeline(
    source_url_or_file: str,
    num_clips: int = 3,
    caption_style: str = "neon_yellow",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Complete end-to-end AI Shorts generation pipeline.
    Accepts YouTube URL or local file path.
    Returns metadata and list of generated clips.
    """
    def notify(step_num: int, total_steps: int, message: str, percent: int):
        print(f"[{step_num}/{total_steps}] {message}")
        if progress_callback:
            progress_callback({
                "step": step_num,
                "total_steps": total_steps,
                "message": message,
                "percent": percent
            })

    total_steps = 6

    # 1. Video Source Preparation
    os.makedirs(TEMP_DIR, exist_ok=True)
    if source_url_or_file.startswith("http://") or source_url_or_file.startswith("https://"):
        notify(1, total_steps, "Connecting to stream and starting video download...", 5)
        video_path = os.path.join(TEMP_DIR, "source_video.mp4")
        download_youtube_video(source_url_or_file, video_path, progress_callback=progress_callback)
    else:
        video_path = os.path.abspath(source_url_or_file)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        notify(1, total_steps, "Using local video source...", 28)

    # Setup Job output folder
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(SHORTS_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)

    # 2. Extract Transcript with Whisper
    notify(2, total_steps, "Extracting audio track for fast transcription...", 30)
    audio_temp = os.path.join(TEMP_DIR, "whisper_audio.wav")
    try:
        subprocess.run([
            FFMPEG_BIN, "-y", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", audio_temp
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        target_audio = audio_temp if os.path.exists(audio_temp) else video_path
    except Exception:
        target_audio = video_path

    notify(2, total_steps, "Whisper AI transcribing speech (analyzing sentences)...", 35)
    segments = get_segments(target_audio)
    if not segments:
        raise ValueError("Could not extract speech segments from video.")

    # 3. Build Chunks and Detect Viral Moments
    notify(3, total_steps, "Analyzing transcript & detecting high-impact viral hooks...", 50)
    chunks = build_chunks(segments)

    best_clips = []
    for chunk in chunks[:25]:
        result = find_best_clips(chunk["text"], chunk.get("start", 0), chunk.get("end", 60))
        if isinstance(result, list):
            for clip in result:
                clip = boost_hook(clip)
                best_clips.append(clip)

    best_clips = rank_clips(best_clips)
    best_clips = best_clips[:num_clips]

    if not best_clips:
        best_clips = [{"start": 0, "end": min(30, segments[-1]["end"]), "score": 80, "reason": "opening hook"}]

    # 4. Cut 9:16 Vertical Clips and Burn Subtitles
    generated_clips = []
    title_seed_text = ""

    for i, clip in enumerate(best_clips):
        clip_num = i + 1
        clip_pct = 60 + int((i / len(best_clips)) * 22)
        notify(4, total_steps, f"Cropping vertical 9:16 & burning captions (Short #{clip_num} of {len(best_clips)})...", clip_pct)

        clip_path = os.path.join(output_dir, f"clip_{clip_num}.mp4")
        srt_path = os.path.join(output_dir, f"clip_{clip_num}.srt")
        final_path = os.path.join(output_dir, f"short_{clip_num}_final.mp4")

        cut_clip_vertical(
            video_path,
            clip["start"],
            clip["end"],
            clip_path
        )

        srt_text = generate_srt(segments, clip["start"], clip["end"])
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_text)

        burn_subtitles_styled(clip_path, srt_path, final_path, style=caption_style)

        title_seed_text += clip.get("reason", "") + " "
        
        duration_sec = round(clip["end"] - clip["start"], 1)
        generated_clips.append({
            "clip_id": clip_num,
            "filename": os.path.basename(final_path),
            "filepath": final_path,
            "duration": f"{duration_sec}s",
            "score": clip.get("score", 85),
            "start": round(clip["start"], 1),
            "end": round(clip["end"], 1),
            "reason": clip.get("reason", "viral hook")
        })

    # 5. Viral Titles and Hashtags
    notify(5, total_steps, "Generating viral SEO titles & hashtags...", 85)
    title = generate_title(title_seed_text or "Insane Moment")
    hashtags = generate_hashtags(title_seed_text or "viral shorts")

    with open(os.path.join(output_dir, "title.txt"), "w", encoding="utf-8") as f:
        f.write(title)

    with open(os.path.join(output_dir, "hashtags.txt"), "w", encoding="utf-8") as f:
        f.write(hashtags)

    # 6. Packaging into ZIP
    notify(6, total_steps, "Packaging final shorts bundle & creating ZIP...", 95)
    zip_path = os.path.join(output_dir, "shorts.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                if file != "shorts.zip" and (file.endswith("_final.mp4") or file.endswith(".txt") or file.endswith(".srt")):
                    file_full = os.path.join(root, file)
                    zipf.write(file_full, arcname=file)

    notify(6, total_steps, "Complete! Ready to download 🚀", 100)

    return {
        "success": True,
        "job_id": job_id,
        "output_dir": output_dir,
        "zip_path": zip_path,
        "title": title,
        "hashtags": hashtags,
        "clips": generated_clips
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_target = sys.argv[1]
    else:
        input_target = "temp/video.mp4"

    res = main_pipeline(input_target)
    print("\n===============================")
    print("AI Shorts Pack Ready 🚀")
    print("TITLE:", res["title"])
    print("HASHTAGS:", res["hashtags"])
    print("ZIP:", res["zip_path"])
    print("===============================\n")