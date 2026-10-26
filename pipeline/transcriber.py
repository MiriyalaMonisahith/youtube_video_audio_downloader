import os
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path
from core.cache import load_transcript_cache, save_transcript_cache

try:
    import whisper
    import torch
except ImportError:
    whisper = None
    torch = None

_model = None
_lock = threading.Lock()

def get_whisper_model():
    global _model
    if whisper is None:
        raise RuntimeError("Whisper is not installed. Please install openai-whisper.")
    if _model is None:
        device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
        _model = whisper.load_model("base", device=device)
    return _model


def transcribe_audio_with_words(
    audio_path: Path,
    video_key: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Transcribes audio with word-level timestamps and disk caching.
    Returns segments containing word-level start/end timings.
    """
    if not force_refresh:
        cached = load_transcript_cache(video_key)
        if cached:
            return cached

    model = get_whisper_model()
    use_fp16 = torch.cuda.is_available() if torch else False

    with _lock:
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            fp16=use_fp16,
            temperature=0.0
        )

    # Normalize segment and word structures
    clean_segments = []
    for s in result.get("segments", []):
        words = []
        for w in s.get("words", []):
            words.append({
                "word": w.get("word", "").strip(),
                "start": round(w.get("start", 0.0), 3),
                "end": round(w.get("end", 0.0), 3),
                "probability": round(w.get("probability", 1.0), 2)
            })

        clean_segments.append({
            "id": s.get("id"),
            "start": round(s.get("start", 0.0), 3),
            "end": round(s.get("end", 0.0), 3),
            "text": s.get("text", "").strip(),
            "words": words
        })

    # Flatten words for direct timing alignment
    all_words = [w for s in clean_segments for w in s.get("words", [])]

    payload = {
        "text": result.get("text", "").strip(),
        "language": result.get("language", "en"),
        "segments": clean_segments,
        "words": all_words
    }

    save_transcript_cache(video_key, payload)
    return payload


def transcribe_audio(audio_path: str, model_name: str = "base") -> Dict[str, Any]:
    """
    Convenience wrapper for transcribe_audio_with_words.
    """
    from core.cache import get_cache_key
    video_key = get_cache_key(str(audio_path))
    return transcribe_audio_with_words(Path(audio_path), video_key)

