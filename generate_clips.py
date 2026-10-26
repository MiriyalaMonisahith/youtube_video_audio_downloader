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
from downloader_engine import SHORTS_DIR, TEMP_DIR

FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


def download_youtube_video(url: str, output_path: str = None) -> str:
    """Downloads a YouTube video to temp directory using native Python yt_dlp."""
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "source_video.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    base_no_ext, _ = os.path.splitext(output_path)
    outtmpl = f"{base_no_ext}.%(ext)s"

    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
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
        notify(1, total_steps, "Downloading source YouTube video...", 10)
        video_path = os.path.join(TEMP_DIR, "source_video.mp4")
        download_youtube_video(source_url_or_file, video_path)
    else:
        video_path = os.path.abspath(source_url_or_file)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        notify(1, total_steps, "Using local video source...", 15)

    # Setup Job output folder
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(SHORTS_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)

    # 2. Extract Transcript with Whisper
    notify(2, total_steps, "Extracting audio & Whisper speech recognition...", 30)
    segments = get_segments(video_path)
    if not segments:
        raise ValueError("Could not extract speech segments from video.")

    # 3. Build Chunks and Detect Viral Moments
    notify(3, total_steps, "Analyzing transcript & detecting high-impact viral moments...", 50)
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
        # Fallback to first 30 seconds
        best_clips = [{"start": 0, "end": min(30, segments[-1]["end"]), "score": 80, "reason": "opening hook"}]

    # 4. Cut 9:16 Vertical Clips and Burn Subtitles
    notify(4, total_steps, f"Cropping vertical 9:16 & burning stylish captions ({len(best_clips)} clips)...", 70)
    
    generated_clips = []
    title_seed_text = ""

    for i, clip in enumerate(best_clips):
        clip_num = i + 1
        clip_path = os.path.join(output_dir, f"clip_{clip_num}.mp4")
        srt_path = os.path.join(output_dir, f"clip_{clip_num}.srt")
        final_path = os.path.join(output_dir, f"short_{clip_num}_final.mp4")

        # Cut vertical video
        cut_clip_vertical(
            video_path,
            clip["start"],
            clip["end"],
            clip_path
        )

        # Generate SRT
        srt_text = generate_srt(segments, clip["start"], clip["end"])
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_text)

        # Burn Subtitles
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
    notify(5, total_steps, "Generating viral titles & hashtags...", 85)
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