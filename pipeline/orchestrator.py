"""
End-to-end Pipeline Orchestrator for YouTube Shorts Studio.
Coordinates:
- Stage profiling and timings benchmark
- Audio-first rapid download & transcription
- Multi-factor virality clip scoring
- Rights and copyright safety verification
- High-speed single-pass rendering with ASS karaoke subtitles
"""

import os
import time
import uuid
from typing import Dict, Any, Optional

from core.config import TEMP_DIR, SHORTS_DIR
from core.cache import get_cached_transcript, set_cached_transcript
from pipeline.downloader import download_audio_stream, download_video_segment, extract_video_metadata
from pipeline.transcriber import transcribe_audio
from pipeline.clip_selector import select_viral_clips
from pipeline.ass_styler import generate_animated_ass
from pipeline.video_processor import render_short_video
from pipeline.rights_guard import assess_rights_and_safety
from pipeline.publisher import generate_shorts_metadata, generate_weekly_posting_schedule
from pipeline.job_manager import job_manager, JobState


def analyze_video_workflow(url: str, user_rights: str = "own") -> Dict[str, Any]:
    """
    Executes fast analysis pipeline:
    1. Fast audio stream download
    2. Whisper transcription with word timestamps (cached)
    3. Multi-factor virality scoring & candidate selection
    4. Copyright & license evaluation
    5. A/B publishing plan generation
    """
    overall_start = time.perf_counter()
    timings = {}

    # 1. Video Metadata
    t0 = time.perf_counter()
    meta = extract_video_metadata(url)
    video_id = meta.get("id", "unknown_video")
    title = meta.get("title", "YouTube Video")
    duration = meta.get("duration", 0)

    # 2. Rights Check
    rights_info = assess_rights_and_safety(meta, user_rights_declaration=user_rights)

    # 3. Fast Audio Download (or cache)
    cached_tr = get_cached_transcript(video_id)
    if cached_tr:
        transcript_data = cached_tr
        timings["download_ms"] = 0
        timings["transcribe_ms"] = 0
    else:
        # Download 3-8MB audio stream
        audio_path = download_audio_stream(url, video_id)
        timings["download_ms"] = int((time.perf_counter() - t0) * 1000)

        # 4. Transcribe with Whisper (word timestamps)
        t_tr = time.perf_counter()
        transcript_data = transcribe_audio(audio_path, model_name="base")
        set_cached_transcript(video_id, transcript_data)
        timings["transcribe_ms"] = int((time.perf_counter() - t_tr) * 1000)

    # 5. Multi-factor AI Clip Selection
    t_sel = time.perf_counter()
    words = transcript_data.get("words", [])
    segments = transcript_data.get("segments", [])
    candidates = select_viral_clips(segments, words, target_duration_range=(30.0, 58.0), top_n=6)
    timings["select_ms"] = int((time.perf_counter() - t_sel) * 1000)

    # 6. Publishing Plan & Schedule
    schedule = generate_weekly_posting_schedule(candidates)
    
    total_ms = int((time.perf_counter() - overall_start) * 1000)
    timings["total_ms"] = total_ms

    return {
        "video_id": video_id,
        "title": title,
        "duration": duration,
        "thumbnail": meta.get("thumbnail"),
        "channel": meta.get("uploader"),
        "candidates": candidates,
        "rights": rights_info,
        "schedule": schedule,
        "timings": timings,
        "words_count": len(words)
    }


def execute_render_job(
    job_id: str,
    url: str,
    start_sec: float,
    end_sec: float,
    clip_text: str,
    video_id: str,
    video_title: str,
    style_name: str = "mrbeast",
    progress_bar: bool = True,
    watermark: Optional[str] = None,
    commentary_path: Optional[str] = None,
    bgm_path: Optional[str] = None
):
    """
    Background worker function that downloads only the required video segment,
    generates styled ASS subtitles, renders 9:16 vertical short in single-pass,
    and publishes progress via job_manager.
    """
    job = job_manager.get_job(job_id)
    if not job:
        return

    try:
        overall_start = time.perf_counter()
        job.update("downloading", 15, "Downloading video segment with precision range...")

        t_dl_start = time.perf_counter()
        # Fetch only the needed segment using download_ranges
        seg_video_path = download_video_segment(url, video_id, start_sec, end_sec)
        dl_ms = int((time.perf_counter() - t_dl_start) * 1000)
        job.update("generating_subtitles", 40, "Generating animated word-by-word karaoke captions...", {"download_ms": dl_ms})

        # Generate Subtitles
        cached_tr = get_cached_transcript(video_id) or {"words": []}
        ass_path = os.path.join(TEMP_DIR, f"{job_id}_subs.ass")
        generate_animated_ass(
            words=cached_tr.get("words", []),
            output_path=ass_path,
            clip_start=start_sec,
            clip_end=end_sec,
            style_name=style_name
        )

        job.update("rendering", 65, "Rendering 9:16 short with hardware acceleration...")

        t_rnd_start = time.perf_counter()
        output_filename = f"short_{job_id}.mp4"
        output_path = os.path.join(SHORTS_DIR, output_filename)
        duration = end_sec - start_sec

        render_res = render_short_video(
            source_video_path=seg_video_path,
            output_path=output_path,
            start_sec=0.0, # Since we downloaded only the segment starting at 0
            duration_sec=duration,
            subtitles_ass_path=ass_path,
            progress_bar=progress_bar,
            bgm_path=bgm_path,
            commentary_path=commentary_path,
            watermark_text=watermark
        )
        rnd_ms = int((time.perf_counter() - t_rnd_start) * 1000)

        # Generate publishing package
        pub_meta = generate_shorts_metadata(
            clip_text=clip_text,
            original_title=video_title,
            attribution_line=f"Original content: {url}",
            duration_sec=duration
        )

        total_ms = int((time.perf_counter() - overall_start) * 1000)
        job.update("finalizing", 95, "Finalizing metadata and export package...", {"render_ms": rnd_ms})

        result = {
            "video_url": f"/shorts/{output_filename}",
            "filename": output_filename,
            "duration": round(duration, 1),
            "render_time_sec": render_res.get("render_time_sec", 0),
            "file_size_mb": render_res.get("file_size_mb", 0),
            "publishing": pub_meta,
            "timings": {
                "download_ms": dl_ms,
                "render_ms": rnd_ms,
                "total_ms": total_ms
            }
        }
        job.complete(result, total_ms=total_ms)

    except Exception as e:
        import traceback
        traceback.print_exc()
        job.fail(str(e))
