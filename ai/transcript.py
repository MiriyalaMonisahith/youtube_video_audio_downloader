import os
import threading

try:
    import whisper
    import torch
except ImportError:
    whisper = None
    torch = None

_model = None
_lock = threading.Lock()

def get_model():
    global _model
    if whisper is None:
        raise RuntimeError("Whisper is not installed. To run AI transcription, install openai-whisper locally.")
    if _model is None:
        device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
        _model = whisper.load_model("base", device=device)
    return _model

def get_transcript(video_path):
    model = get_model()
    use_fp16 = torch.cuda.is_available() if torch else False
    with _lock:
        result = model.transcribe(video_path, fp16=use_fp16)
    return result

def get_segments(video_path):
    model = get_model()
    use_fp16 = torch.cuda.is_available() if torch else False
    with _lock:
        result = model.transcribe(video_path, fp16=use_fp16)
    return result.get("segments", [])