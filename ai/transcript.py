try:
    import whisper
except ImportError:
    whisper = None

_model = None

def get_model():
    global _model
    if whisper is None:
        raise RuntimeError("Whisper is not installed. To run AI transcription, install openai-whisper locally.")
    if _model is None:
        _model = whisper.load_model("base")
    return _model

def get_transcript(video_path):
    model = get_model()
    result = model.transcribe(video_path)
    return result

def get_segments(video_path):
    model = get_model()
    result = model.transcribe(video_path)
    return result["segments"]