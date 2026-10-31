"""
AI Transcription Engine with Whisper & Cloud Subtitles.
Provides fast speech-to-text with word-level timestamps,
hallucination-suppression, and device-aware model selection.
"""

import os
import threading
from typing import Dict, Any, List, Optional
from core.cache import load_transcript_cache, save_transcript_cache, get_cache_key

try:
    import whisper
    import torch
except ImportError:
    whisper = None
    torch = None

_models: Dict[str, Any] = {}
_lock = threading.Lock()


def get_model(model_name: Optional[str] = None):
    """
    Loads and caches Whisper model.
    Defaults to 'tiny.en' on CPU for high-speed processing, or 'base' on CUDA GPU.
    """
    global _models
    if whisper is None:
        raise RuntimeError("Whisper is not installed. Please install openai-whisper.")

    device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
    if not model_name:
        model_name = "base" if device == "cuda" else "tiny.en"

    cache_key = f"{model_name}_{device}"
    with _lock:
        if cache_key not in _models:
            _models[cache_key] = whisper.load_model(model_name, device=device)
        return _models[cache_key]


def get_transcript(
    audio_or_video_path: str,
    model_name: Optional[str] = None,
    word_timestamps: bool = True
) -> Dict[str, Any]:
    """
    Transcribes audio with robust anti-hallucination settings and word timestamps.
    """
    if not os.path.exists(audio_or_video_path):
        raise FileNotFoundError(f"Audio/video file not found: {audio_or_video_path}")

    # Check cache first
    cache_id = get_cache_key(audio_or_video_path)
    cached = load_transcript_cache(cache_id)
    if cached:
        return cached

    model = get_model(model_name)
    use_fp16 = bool(torch and torch.cuda.is_available())

    transcribe_options = {
        "fp16": use_fp16,
        "condition_on_previous_text": False,  # Prevents repetitive hallucination loops
        "compression_ratio_threshold": 2.4,
        "no_speech_threshold": 0.6,
        "temperature": (0.0, 0.2, 0.4),
        "word_timestamps": word_timestamps
    }

    with _lock:
        result = model.transcribe(audio_or_video_path, **transcribe_options)

    # Clean and structure word timestamps
    all_words = []
    clean_segments = []

    for seg in result.get("segments", []):
        seg_text = seg.get("text", "").strip()
        s_start = round(seg.get("start", 0.0), 2)
        s_end = round(seg.get("end", 0.0), 2)

        seg_words = []
        for w in seg.get("words", []):
            word_str = w.get("word", "").strip()
            if word_str:
                w_obj = {
                    "word": word_str,
                    "start": round(w.get("start", s_start), 2),
                    "end": round(w.get("end", s_end), 2)
                }
                seg_words.append(w_obj)
                all_words.append(w_obj)

        clean_segments.append({
            "start": s_start,
            "end": s_end,
            "text": seg_text,
            "words": seg_words
        })

    structured_data = {
        "text": result.get("text", "").strip(),
        "segments": clean_segments,
        "words": all_words,
        "language": result.get("language", "en")
    }

    save_transcript_cache(cache_id, structured_data)
    return structured_data


def get_segments(audio_or_video_path: str, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns segment list with word timestamps.
    Maintains 100% backwards compatibility with legacy callers.
    """
    transcript = get_transcript(audio_or_video_path, model_name=model_name)
    return transcript.get("segments", [])
