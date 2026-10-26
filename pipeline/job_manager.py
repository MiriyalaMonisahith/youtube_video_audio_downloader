"""
Job Queue and SSE Streaming Manager for YouTube Shorts Generation.
Manages asynchronous pipeline execution with worker thread pool, stage timing profiling,
and real-time Server-Sent Events (SSE) progress streaming.
"""

from typing import Dict, Any, Generator, Optional
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor

class JobState:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = "queued" # queued, analyzing, selecting, rendering, completed, failed
        self.progress = 0
        self.message = "Job initialized"
        self.timings = {
            "download_ms": 0,
            "transcribe_ms": 0,
            "select_ms": 0,
            "render_ms": 0,
            "total_ms": 0
        }
        self.result = {}
        self.error = None
        self.event_queue = queue.Queue()
        self.created_at = time.time()

    def update(self, status: str, progress: int, message: str, stage_timing: Optional[Dict[str, int]] = None):
        self.status = status
        self.progress = progress
        self.message = message
        if stage_timing:
            self.timings.update(stage_timing)
        payload = {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "timings": self.timings
        }
        self.event_queue.put(payload)

    def complete(self, result: Dict[str, Any], total_ms: int):
        self.status = "completed"
        self.progress = 100
        self.message = "Short creation completed successfully!"
        self.result = result
        self.timings["total_ms"] = total_ms
        payload = {
            "job_id": self.job_id,
            "status": "completed",
            "progress": 100,
            "message": self.message,
            "timings": self.timings,
            "result": self.result
        }
        self.event_queue.put(payload)

    def fail(self, error_message: str):
        self.status = "failed"
        self.error = error_message
        self.message = f"Error: {error_message}"
        payload = {
            "job_id": self.job_id,
            "status": "failed",
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "timings": self.timings
        }
        self.event_queue.put(payload)


class JobQueueManager:
    def __init__(self, max_workers: int = 4):
        self.jobs: Dict[str, JobState] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()

    def create_job(self, job_id: str) -> JobState:
        with self.lock:
            state = JobState(job_id)
            self.jobs[job_id] = state
            return state

    def get_job(self, job_id: str) -> Optional[JobState]:
        with self.lock:
            return self.jobs.get(job_id)

    def submit_task(self, fn, *args, **kwargs):
        return self.executor.submit(fn, *args, **kwargs)

    def sse_event_stream(self, job_id: str) -> Generator[str, None, None]:
        """Generator yielding Server-Sent Events formatted strings for the job."""
        job = self.get_job(job_id)
        if not job:
            yield "event: error\ndata: {\"error\": \"Job not found\"}\n\n"
            return

        # Send initial status
        import json
        initial_payload = {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "timings": job.timings
        }
        yield f"data: {json.dumps(initial_payload)}\n\n"

        while True:
            try:
                # Wait up to 25s for next event or send keepalive comment
                event = job.event_queue.get(timeout=25.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") in ["completed", "failed"]:
                    break
            except queue.Empty:
                # Send SSE keep-alive comment
                yield ": keep-alive\n\n"


# Global singleton manager
job_manager = JobQueueManager(max_workers=4)
