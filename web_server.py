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
from generate_clips import main_pipeline

app = Flask(__name__, static_folder="static", static_url_path="")

# In-memory job state store
jobs = {}

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/info", methods=["POST"])
def fetch_info():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
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
    url = data.get("url", "").strip()
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


@app.route("/api/shorts", methods=["POST"])
def start_shorts():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "URL or video path is required"}), 400

    num_clips = int(data.get("num_clips", 3))
    caption_style = data.get("caption_style", "neon_yellow")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "type": "shorts",
        "status": "starting",
        "percent": 5.0,
        "message": "Initializing AI Shorts pipeline...",
        "result": None,
        "error": None
    }

    def run_shorts_worker():
        try:
            def on_progress(p):
                jobs[job_id].update({
                    "status": "processing",
                    "step": p.get("step", 1),
                    "total_steps": p.get("total_steps", 6),
                    "message": p.get("message", ""),
                    "percent": p.get("percent", 0)
                })

            result = main_pipeline(
                source_url_or_file=url,
                num_clips=num_clips,
                caption_style=caption_style,
                progress_callback=on_progress
            )
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["percent"] = 100.0
            jobs[job_id]["message"] = "Shorts Pack Generated Successfully!"
            jobs[job_id]["result"] = result
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

    threading.Thread(target=run_shorts_worker, daemon=True).start()
    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/job/<job_id>", methods=["GET"])
def get_job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404
    return jsonify({"success": True, "job": job})


@app.route("/api/library", methods=["GET"])
def get_library():
    downloads = []
    # Scan downloads folder
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

    # Scan shorts folder for packs
    shorts_packs = []
    if os.path.exists(SHORTS_DIR):
        for folder in sorted(os.listdir(SHORTS_DIR), reverse=True):
            folder_path = os.path.join(SHORTS_DIR, folder)
            if os.path.isdir(folder_path):
                clips = []
                title = ""
                hashtags = ""
                
                title_file = os.path.join(folder_path, "title.txt")
                if os.path.exists(title_file):
                    with open(title_file, "r", encoding="utf-8") as tf:
                        title = tf.read().strip()

                tag_file = os.path.join(folder_path, "hashtags.txt")
                if os.path.exists(tag_file):
                    with open(tag_file, "r", encoding="utf-8") as hf:
                        hashtags = hf.read().strip()

                zip_file = os.path.join(folder_path, "shorts.zip")
                has_zip = os.path.exists(zip_file)

                for f in os.listdir(folder_path):
                    if f.endswith("_final.mp4"):
                        clips.append({
                            "filename": f,
                            "url": f"/media/shorts/{folder}/{f}",
                            "download_url": f"/download_media/shorts/{folder}/{f}"
                        })

                if clips or has_zip:
                    shorts_packs.append({
                        "job_id": folder,
                        "title": title or f"Shorts Collection {folder}",
                        "hashtags": hashtags,
                        "clips": clips,
                        "zip_url": f"/download_media/shorts/{folder}/shorts.zip" if has_zip else None
                    })

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


if __name__ == "__main__":
    port = 5000
    print(f"\n🚀 Launching Premium Downloader & AI Shorts Web App at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
