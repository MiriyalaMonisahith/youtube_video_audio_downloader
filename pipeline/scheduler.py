"""
Daily Auto-Upload & Publishing Scheduler module for YouTube Shorts.
Schedules generated shorts at customizable daily times and manages
the automated publishing pipeline with WhatsApp & Email alarm triggers.
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from core.config import CACHE_DIR, SHORTS_DIR
from pipeline.notifier import trigger_daily_alarm_suite

SCHEDULE_FILE = os.path.join(CACHE_DIR, "scheduled_uploads.json")
CONFIG_FILE = os.path.join(CACHE_DIR, "scheduler_config.json")

DEFAULT_DAILY_TIMES = {
    "Monday": "12:00",
    "Tuesday": "17:30",
    "Wednesday": "12:00",
    "Thursday": "18:00",
    "Friday": "16:30",
    "Saturday": "11:00",
    "Sunday": "19:00"
}


def load_scheduler_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "enabled": True,
        "daily_times": DEFAULT_DAILY_TIMES,
        "auto_notify_whatsapp": True,
        "auto_notify_email": True,
        "target_whatsapp": "9666641949",
        "target_email": "monisahith11@gmail.com"
    }


def save_scheduler_config(cfg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_queue() -> List[Dict[str, Any]]:
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_queue(q: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2)


def get_next_available_slot(days_ahead: int = 0) -> str:
    """Calculates next scheduled custom posting time based on user configuration."""
    cfg = load_scheduler_config()
    daily_times = cfg.get("daily_times", DEFAULT_DAILY_TIMES)
    
    target_date = datetime.now() + timedelta(days=days_ahead)
    day_name = target_date.strftime("%A")
    time_str = daily_times.get(day_name, "12:00")
    
    date_part = target_date.strftime("%Y-%m-%d")
    return f"{date_part} {time_str}:00"


def schedule_clip_for_upload(
    clip_filename: str,
    title: str,
    description: str,
    tags: List[str],
    scheduled_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enqueues a rendered clip for daily auto-upload at user's custom daily time,
    and automatically fires the WhatsApp + Email alarm.
    """
    queue = load_queue()
    if not scheduled_time:
        scheduled_time = get_next_available_slot(len(queue))

    entry = {
        "id": f"upload_{int(time.time())}_{len(queue)}",
        "filename": clip_filename,
        "title": title,
        "description": description,
        "tags": tags,
        "scheduled_time": scheduled_time,
        "status": "QUEUED",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    queue.append(entry)
    save_queue(queue)

    # Automatically fire WhatsApp + Email daily alarm
    cfg = load_scheduler_config()
    if cfg.get("auto_notify_whatsapp") or cfg.get("auto_notify_email"):
        trigger_daily_alarm_suite(title)

    return entry


def check_and_run_due_uploads() -> List[Dict[str, Any]]:
    """Checks for clips whose scheduled time has arrived and executes the YouTube upload."""
    from pipeline.youtube_uploader import upload_short_to_youtube
    queue = load_queue()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    updated = False
    completed = []

    for item in queue:
        if item.get("status") == "QUEUED" and item.get("scheduled_time") <= now_str:
            # Execute automated YouTube upload (Live or Staging mode)
            upload_res = upload_short_to_youtube(
                video_path=item.get("filename", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                tags=item.get("tags", []),
                scheduled_time=item.get("scheduled_time")
            )

            item["youtube_url"] = upload_res.get("url", "")
            item["youtube_id"] = upload_res.get("video_id", "")
            item["status"] = "PUBLISHED" if upload_res.get("live") else "PUBLISHED_STAGED"
            item["published_at"] = now_str
            item["upload_meta"] = upload_res
            completed.append(item)
            updated = True

            # Trigger wake-up alarm with direct YouTube link
            try:
                short_link = upload_res.get("url", "http://localhost:5000")
                trigger_daily_alarm_suite(f"{item.get('title')} ({short_link})")
            except Exception as _ne:
                print(f"Warning notifying daily alarm on upload tick: {_ne}")

    if updated:
        save_queue(queue)

    return completed


# Background daemon monitor for auto-uploads
_scheduler_thread = None
_running = False

def start_scheduler_daemon():
    global _scheduler_thread, _running
    if _running:
        return
    _running = True

    def loop():
        while _running:
            try:
                check_and_run_due_uploads()
            except Exception as e:
                print(f"Scheduler worker tick error: {e}")
            time.sleep(30)

    _scheduler_thread = threading.Thread(target=loop, daemon=True)
    _scheduler_thread.start()
