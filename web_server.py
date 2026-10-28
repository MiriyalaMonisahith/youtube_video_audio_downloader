import os
import sys
import uuid
import threading
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from downloader_engine import get_video_info, download_media, OUTPUT_DIR, SHORTS_DIR
from core.config import SHORTS_DIR as NEW_SHORTS_DIR
from core.hardware import detect_hardware_encoder
from pipeline.orchestrator import analyze_video_workflow, execute_render_job
from pipeline.job_manager import job_manager
from pipeline.rights_guard import assess_rights_and_safety
from pipeline.self_learner import get_ai_learner_status
from pipeline.scheduler import (
    load_scheduler_config,
    save_scheduler_config,
    load_queue,
    start_scheduler_daemon
)
from pipeline.notifier import send_whatsapp_alarm, send_daily_email, trigger_daily_alarm_suite

try:
    from generate_clips import main_pipeline
except Exception as e:
    def main_pipeline(*args, **kwargs):
        raise RuntimeError("AI Shorts pipeline requires local Whisper and FFmpeg. Please run locally with 'python web_server.py'!")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# In-memory legacy job store for basic downloads
jobs = {}


def clean_url(raw_url: str) -> str:
    """Strips whitespace, zero-width spaces, and invisible Unicode chars from user URLs."""
    if not raw_url:
        return ""
    return "".join(c for c in str(raw_url) if c not in ('\u200b', '\ufeff', '\u200e', '\u200f', '\n', '\r', '\t')).strip()


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static_file(filename):
    target = os.path.join(STATIC_DIR, filename)
    if os.path.exists(target) and os.path.isfile(target):
        return send_from_directory(STATIC_DIR, filename)
    return "Not found", 404


@app.route("/api/health")
def health():
    hw = detect_hardware_encoder()
    return jsonify({
        "status": "ok",
        "vercel": os.environ.get("VERCEL") == "1",
        "hardware_acceleration": hw
    })


@app.route("/api/hardware-status")
def hardware_status():
    hw = detect_hardware_encoder()
    return jsonify({
        "success": True,
        "hardware": hw
    })


# ==========================================
# 1 & 2. SPEED + AI CLIP SELECTION ENDPOINTS
# ==========================================

@app.route("/api/analyze", methods=["POST"])
def analyze_video():
    """
    Rapid audio-first analysis:
    Downloads only audio (2-5s), runs Whisper with word timestamps,
    scores multi-factor virality (hook, emotion, thought, pacing, retention),
    evaluates copyright rights, and produces weekly schedule + A/B titles.
    """
    data = request.get_json() or {}
    url = clean_url(data.get("url", ""))
    rights = data.get("rights", "own")

    if not url:
        return jsonify({"success": False, "error": "YouTube link is required"}), 400

    try:
        analysis_result = analyze_video_workflow(url, user_rights=rights)
        return jsonify({
            "success": True,
            "data": analysis_result
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/render-clip", methods=["POST"])
def render_clip():
    """
    Spawns high-speed background rendering of chosen clip:
    Downloads only the needed section via yt-dlp download_ranges,
    generates animated ASS karaoke captions,
    renders single-pass with hardware acceleration (NVENC/QSV/MF),
    and streams progress over SSE.
    """
    data = request.get_json() or {}
    url = clean_url(data.get("url", ""))
    start_sec = float(data.get("start_sec", 0.0))
    end_sec = float(data.get("end_sec", 45.0))
    clip_text = data.get("clip_text", "")
    video_id = data.get("video_id", "clip")
    video_title = data.get("video_title", "YouTube Short")
    style_name = data.get("style_name", "mrbeast")
    progress_bar = bool(data.get("progress_bar", True))
    watermark = data.get("watermark", None)
    copyright_free = bool(data.get("copyright_free", False))
    score = float(data.get("score") or data.get("virality_score") or 92.0)

    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    if end_sec <= start_sec:
        return jsonify({"success": False, "error": "Invalid time range: end must be greater than start"}), 400

    job_id = str(uuid.uuid4())[:8]
    job_manager.create_job(job_id)

    job_manager.submit_task(
        execute_render_job,
        job_id=job_id,
        url=url,
        start_sec=start_sec,
        end_sec=end_sec,
        clip_text=clip_text,
        video_id=video_id,
        video_title=video_title,
        style_name=style_name,
        progress_bar=progress_bar,
        watermark=watermark,
        copyright_free=copyright_free,
        score=score
    )

    return jsonify({
        "success": True,
        "job_id": job_id
    })


@app.route("/api/stream/<job_id>")
def stream_job_events(job_id):
    """Real-time Server-Sent Events (SSE) streaming progress and stopwatch timings."""
    return Response(
        job_manager.sse_event_stream(job_id),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ==========================================
# 4. RIGHTS & SAFETY GUARDRAILS
# ==========================================

@app.route("/api/rights-check", methods=["POST"])
def rights_check():
    data = request.get_json() or {}
    url = clean_url(data.get("url", ""))
    user_declaration = data.get("declaration", "own")
    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    try:
        info = get_video_info(url)
        assessment = assess_rights_and_safety(info, user_rights_declaration=user_declaration)
        return jsonify({"success": True, "assessment": assessment})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# MEDIA STREAMING & DOWNLOAD SERVING
# ==========================================

@app.route("/shorts/<path:filename>")
def serve_rendered_short(filename):
    """Direct streaming of rendered 9:16 vertical shorts."""
    folder = NEW_SHORTS_DIR if os.path.exists(os.path.join(NEW_SHORTS_DIR, filename)) else SHORTS_DIR
    full_path = os.path.join(folder, filename)
    if not os.path.exists(full_path):
        return "Short not found", 404
    return send_file(full_path, mimetype="video/mp4")


@app.route("/api/info", methods=["POST"])
def fetch_info():
    data = request.get_json() or {}
    url = clean_url(data.get("url", ""))
    if not url:
        return jsonify({"success": False, "error": "Please provide a valid URL"}), 400

    try:
        info = get_video_info(url)
        return jsonify({"success": True, "data": info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = clean_url(data.get("url", ""))
    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    media_type = data.get("type", "video")
    resolution = int(data.get("resolution", 1080))
    video_format = data.get("video_format", "mp4")
    audio_format = data.get("audio_format", "mp3")
    audio_quality = data.get("audio_quality", "320k")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "type": "download",
        "media_type": media_type,
        "status": "starting",
        "percent": 0.0,
        "message": "Initializing download...",
        "result": None,
        "error": None
    }

    def run_worker():
        try:
            def on_progress(p):
                jobs[job_id].update({
                    "status": p.get("status", "downloading"),
                    "percent": p.get("percent", 0.0),
                    "downloaded_str": p.get("downloaded_str", ""),
                    "total_str": p.get("total_str", ""),
                    "speed_str": p.get("speed_str", ""),
                    "eta_str": p.get("eta_str", "")
                })

            result = download_media(
                url=url,
                media_type=media_type,
                resolution=resolution,
                video_format=video_format,
                audio_format=audio_format,
                audio_quality=audio_quality,
                progress_callback=on_progress
            )
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["percent"] = 100.0
            jobs[job_id]["result"] = result
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

    threading.Thread(target=run_worker, daemon=True).start()
    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/job/<job_id>", methods=["GET"])
def get_job_status(job_id):
    # Check new job_manager first
    new_job = job_manager.get_job(job_id)
    if new_job:
        return jsonify({
            "success": True,
            "job": {
                "id": new_job.job_id,
                "status": new_job.status,
                "percent": new_job.progress,
                "message": new_job.message,
                "timings": new_job.timings,
                "result": new_job.result,
                "error": new_job.error
            }
        })

    job = jobs.get(job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404
    return jsonify({"success": True, "job": job})


@app.route("/api/library", methods=["GET"])
def get_library():
    downloads = []
    if os.path.exists(OUTPUT_DIR):
        for f in sorted(os.listdir(OUTPUT_DIR), reverse=True):
            full_path = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(full_path):
                ext = os.path.splitext(f)[1].lower().replace(".", "")
                is_video = ext in ["mp4", "mkv", "webm", "avi"]
                is_audio = ext in ["mp3", "m4a", "wav", "flac", "opus"]
                if is_video or is_audio:
                    downloads.append({
                        "filename": f,
                        "type": "video" if is_video else "audio",
                        "size": f"{os.path.getsize(full_path) / (1024 * 1024):.1f} MB",
                        "modified": time.ctime(os.path.getmtime(full_path)),
                        "url": f"/media/downloads/{f}",
                        "download_url": f"/download_media/downloads/{f}"
                    })

    shorts_packs = []
    # Check both SHORTS_DIR and NEW_SHORTS_DIR
    target_shorts_dirs = list(set([SHORTS_DIR, NEW_SHORTS_DIR]))
    for s_dir in target_shorts_dirs:
        if os.path.exists(s_dir):
            for item in sorted(os.listdir(s_dir), reverse=True):
                full = os.path.join(s_dir, item)
                if os.path.isfile(full) and item.endswith(".mp4"):
                    shorts_packs.append({
                        "job_id": item,
                        "title": item,
                        "clips": [{"filename": item, "url": f"/shorts/{item}", "download_url": f"/shorts/{item}"}]
                    })
                elif os.path.isdir(full):
                    clips = []
                    for f in os.listdir(full):
                        if f.endswith(".mp4"):
                            clips.append({"filename": f, "url": f"/media/shorts/{item}/{f}", "download_url": f"/download_media/shorts/{item}/{f}"})
                    if clips:
                        shorts_packs.append({"job_id": item, "title": f"Collection {item}", "clips": clips})

    return jsonify({
        "success": True,
        "downloads": downloads,
        "shorts": shorts_packs
    })


@app.route("/media/<path:subpath>")
def serve_media(subpath):
    parts = subpath.split("/", 1)
    if len(parts) < 2:
        return "Not found", 404
    base_folder, rel_path = parts[0], parts[1]
    folder = OUTPUT_DIR if base_folder == "downloads" else SHORTS_DIR
    full_path = os.path.join(folder, rel_path)
    if not os.path.exists(full_path):
        return "File not found", 404
    return send_file(full_path)


@app.route("/download_media/<path:subpath>")
def force_download(subpath):
    parts = subpath.split("/", 1)
    if len(parts) < 2:
        return "Not found", 404
    base_folder, rel_path = parts[0], parts[1]
    folder = OUTPUT_DIR if base_folder == "downloads" else SHORTS_DIR
    full_path = os.path.join(folder, rel_path)
    if not os.path.exists(full_path):
        return "File not found", 404
    return send_file(full_path, as_attachment=True)



# ==========================================
# 6. SELF-ENHANCING AI & SCHEDULER & ALARMS
# ==========================================

@app.route("/api/ai-learner/status", methods=["GET"])
def get_learner_status_endpoint():
    """Returns real-time neural learning metrics and recent evolution logs."""
    return jsonify({
        "success": True,
        "data": get_ai_learner_status()
    })


@app.route("/api/scheduler/config", methods=["GET", "POST"])
def scheduler_config_endpoint():
    """Reads or updates custom daily posting times and alarm preferences."""
    if request.method == "POST":
        data = request.get_json() or {}
        cfg = load_scheduler_config()
        if "daily_times" in data:
            cfg["daily_times"] = data["daily_times"]
        if "enabled" in data:
            cfg["enabled"] = bool(data["enabled"])
        if "target_whatsapp" in data:
            cfg["target_whatsapp"] = str(data["target_whatsapp"])
        if "target_email" in data:
            cfg["target_email"] = str(data["target_email"])
        save_scheduler_config(cfg)
        return jsonify({"success": True, "config": cfg})
    else:
        return jsonify({"success": True, "config": load_scheduler_config()})


@app.route("/api/scheduler/queue", methods=["GET"])
def scheduler_queue_endpoint():
    """Returns all queued and published auto-upload shorts."""
    return jsonify({
        "success": True,
        "queue": load_queue()
    })


@app.route("/api/notify/test-whatsapp", methods=["POST"])
def notify_test_whatsapp():
    """Triggers an immediate WhatsApp test alarm to +91 9666641949."""
    data = request.get_json() or {}
    phone = data.get("phone", "9666641949")
    msg = data.get("message")
    res = send_whatsapp_alarm(phone=phone, message=msg)
    return jsonify({"success": True, "result": res})


@app.route("/api/notify/test-email", methods=["POST"])
def notify_test_email():
    """Triggers an immediate email test alarm to monisahith11@gmail.com."""
    data = request.get_json() or {}
    email = data.get("email", "monisahith11@gmail.com")
    clip_title = data.get("clip_title", "Daily AI Shorts Hub Ready")
    res = send_daily_email(to_email=email, subject=f"⚡ Vortex Alarm: {clip_title}")
    return jsonify({"success": True, "result": res})



# ==========================================
# 7. YOUTUBE AUTOMATED UPLOADER ENGINE
# ==========================================
from pipeline.youtube_uploader import (
    load_youtube_credentials,
    save_youtube_credentials,
    get_youtube_status,
    test_youtube_connection,
    upload_short_to_youtube
)


@app.route("/api/youtube/status", methods=["GET"])
def youtube_status_endpoint():
    """Returns current YouTube channel connection and credentials status."""
    return jsonify({
        "success": True,
        "status": get_youtube_status()
    })


@app.route("/api/youtube/credentials", methods=["POST"])
def youtube_credentials_endpoint():
    """Saves user-provided YouTube OAuth 2.0 credentials."""
    data = request.get_json() or {}
    cfg = load_youtube_credentials()
    if "client_id" in data:
        cfg["client_id"] = str(data["client_id"]).strip()
    if "client_secret" in data:
        cfg["client_secret"] = str(data["client_secret"]).strip()
    if "refresh_token" in data:
        cfg["refresh_token"] = str(data["refresh_token"]).strip()
    if "privacy_status" in data:
        cfg["privacy_status"] = str(data["privacy_status"]).strip()
    if "default_category_id" in data:
        cfg["default_category_id"] = str(data["default_category_id"]).strip()

    save_youtube_credentials(cfg)
    test_res = test_youtube_connection()
    return jsonify({
        "success": True,
        "status": get_youtube_status(),
        "test_result": test_res
    })


@app.route("/api/youtube/test", methods=["POST"])
def youtube_test_endpoint():
    """Validates the saved YouTube credentials against Google's API."""
    res = test_youtube_connection()
    return jsonify(res)


@app.route("/api/youtube/manual-upload", methods=["POST"])
def youtube_manual_upload_endpoint():
    """Manually triggers immediate YouTube upload for a specific clip."""
    data = request.get_json() or {}
    filename = data.get("filename", "")
    title = data.get("title", f"Short - {filename}")
    desc = data.get("description", "")
    tags = data.get("tags", ["#Shorts", "#Viral"])
    res = upload_short_to_youtube(video_path=filename, title=title, description=desc, tags=tags)
    return jsonify({"success": True, "result": res})


# Start auto-upload daemon monitor
try:
    start_scheduler_daemon()
except Exception as _e:
    print(f"Warning: Could not start scheduler daemon: {_e}")


if __name__ == "__main__":
    port = 5000
    print(f"\nLaunching Upgraded Shorts AI Studio at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
