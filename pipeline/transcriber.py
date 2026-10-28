import os
import json
import urllib.request
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path
from core.cache import load_transcript_cache, save_transcript_cache, get_cache_key

try:
    import whisper
    import torch
except ImportError:
    whisper = None
    torch = None

_model = None
_lock = threading.Lock()


def get_whisper_model(model_name: str = "tiny.en"):
    """
    Loads Whisper model. Defaults to 'tiny.en' on CPU for ultra-fast transcription,
    or 'base' when GPU is available.
    """
    global _model
    if whisper is None:
        raise RuntimeError("Whisper is not installed. Please install openai-whisper.")
    if _model is None:
        device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
        chosen = "base" if device == "cuda" else "tiny.en"
        _model = whisper.load_model(chosen, device=device)
    return _model


def extract_youtube_cloud_transcript(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extracts pre-computed cloud subtitles and word timestamps directly from YouTube.
    Executes in under 0.5 seconds without downloading audio or running heavy CPU models!
    """
    video_id = info.get("id") or get_cache_key(info.get("webpage_url", "video"))
    cached = load_transcript_cache(video_id)
    if cached:
        return cached

    subs = info.get("subtitles", {}) or {}
    auto_subs = info.get("automatic_captions", {}) or {}

    # Language priority: English variants first, then first available
    target_langs = ["en", "en-US", "en-orig", "en-GB"]
    selected_track = None

    for lang in target_langs:
        if lang in subs:
            selected_track = subs[lang]
            break
        if lang in auto_subs:
            selected_track = auto_subs[lang]
            break

    if not selected_track:
        # Fallback to any language
        for track_dict in [subs, auto_subs]:
            if track_dict:
                selected_track = next(iter(track_dict.values()))
                break

    if not selected_track:
        return None

    # Find json3 format URL
    json3_url = None
    for fmt in selected_track:
        if fmt.get("ext") == "json3":
            json3_url = fmt.get("url")
            break

    if not json3_url:
        return None

    try:
        req = urllib.request.Request(
            json3_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        clean_segments = []
        all_words = []
        full_text_parts = []
        prev_clean_text = ""
        prev_t_start = -999.0

        for ev in data.get("events", []):
            t_start = ev.get("tStartMs", 0) / 1000.0
            d_dur = ev.get("dDurationMs", 0) / 1000.0
            t_end = t_start + d_dur

            segs = ev.get("segs", [])
            if not segs:
                continue

            raw_text = "".join(s.get("utf8", "") for s in segs)
            # Remove zero-width spaces, byte-order marks, and bidirectional markers
            clean_text = "".join(c for c in raw_text if c not in ('\u200b', '\ufeff', '\u200e', '\u200f', '\n', '\r'))
            clean_text = " ".join(clean_text.split()).strip()
            if not clean_text:
                continue

            # Deduplicate concurrent or identical duplicate events from YouTube tracks
            if clean_text == prev_clean_text and abs(t_start - prev_t_start) < 1.2:
                continue
            if t_start < prev_t_start - 0.05:
                continue

            prev_clean_text = clean_text
            prev_t_start = t_start
            full_text_parts.append(clean_text)

            # Extract words with timestamps (using exact word offsets from YouTube if present)
            seg_words = []
            has_word_offsets = any("tOffsetMs" in s for s in segs)

            if has_word_offsets:
                for idx, s in enumerate(segs):
                    w_raw = s.get("utf8", "")
                    w_clean = "".join(c for c in w_raw if c not in ('\u200b', '\ufeff', '\u200e', '\u200f', '\n', '\r')).strip()
                    if not w_clean:
                        continue
                    w_offset = s.get("tOffsetMs", 0) / 1000.0
                    w_start = t_start + w_offset
                    if idx + 1 < len(segs) and "tOffsetMs" in segs[idx + 1]:
                        w_end = t_start + (segs[idx + 1]["tOffsetMs"] / 1000.0)
                    else:
                        w_end = min(t_end, w_start + 0.35)
                    if w_end <= w_start:
                        w_end = w_start + 0.25
                    w_obj = {
                        "word": w_clean,
                        "start": round(w_start, 3),
                        "end": round(w_end, 3),
                        "probability": 0.99
                    }
                    seg_words.append(w_obj)
                    all_words.append(w_obj)
            else:
                words_list = clean_text.split()
                if words_list:
                    effective_dur = max(d_dur, 0.2 * len(words_list))
                    step = effective_dur / len(words_list)
                    w_start = t_start
                    for w in words_list:
                        w_clean = "".join(c for c in w if c not in ('\u200b', '\ufeff', '\u200e', '\u200f')).strip()
                        if not w_clean:
                            continue
                        w_obj = {
                            "word": w_clean,
                            "start": round(w_start, 3),
                            "end": round(w_start + step, 3),
                            "probability": 0.99
                        }
                        seg_words.append(w_obj)
                        all_words.append(w_obj)
                        w_start += step

            clean_segments.append({
                "start": round(t_start, 3),
                "end": round(t_end, 3),
                "text": clean_text,
                "words": seg_words
            })

        if not clean_segments:
            return None

        result_payload = {
            "text": " ".join(full_text_parts),
            "language": "en",
            "segments": clean_segments,
            "words": all_words,
            "source": "youtube_cloud_captions"
        }

        save_transcript_cache(video_id, result_payload)
        return result_payload

    except Exception as e:
        print(f"Warning: Cloud captions extraction failed ({e}), falling back to Whisper")
        return None


def transcribe_audio_with_words(
    audio_path: Path,
    video_key: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Transcribes audio with word-level timestamps using Whisper and disk caching.
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

    clean_segments = []
    prev_seg_text = ""
    prev_seg_start = -999.0

    for s in result.get("segments", []):
        seg_raw = s.get("text", "")
        seg_clean = "".join(c for c in seg_raw if c not in ('\u200b', '\ufeff', '\u200e', '\u200f', '\n', '\r')).strip()
        if not seg_clean:
            continue

        s_start = round(s.get("start", 0.0), 3)
        s_end = round(s.get("end", 0.0), 3)

        # Skip duplicate hallucinations from Whisper
        if seg_clean.lower() == prev_seg_text.lower() and abs(s_start - prev_seg_start) < 1.0:
            continue

        words = []
        for w in s.get("words", []):
            raw_w = w.get("word", "")
            clean_w = "".join(c for c in raw_w if c not in ('\u200b', '\ufeff', '\u200e', '\u200f')).strip()
            if not clean_w:
                continue
            words.append({
                "word": clean_w,
                "start": round(w.get("start", 0.0), 3),
                "end": round(w.get("end", 0.0), 3),
                "probability": round(w.get("probability", 1.0), 2)
            })

        clean_segments.append({
            "id": s.get("id"),
            "start": s_start,
            "end": s_end,
            "text": seg_clean,
            "words": words
        })
        prev_seg_text = seg_clean
        prev_seg_start = s_start

    all_words = [w for s in clean_segments for w in s.get("words", [])]

    payload = {
        "text": result.get("text", "").strip(),
        "language": result.get("language", "en"),
        "segments": clean_segments,
        "words": all_words,
        "source": "whisper_local"
    }

    save_transcript_cache(video_key, payload)
    return payload


def transcribe_audio(audio_path: str, model_name: str = "tiny.en") -> Dict[str, Any]:
    """
    Convenience wrapper for transcribe_audio_with_words.
    """
    video_key = get_cache_key(str(audio_path))
    return transcribe_audio_with_words(Path(audio_path), video_key)
