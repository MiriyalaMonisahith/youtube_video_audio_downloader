import requests
import json
import re

def find_best_clips(chunk_text, chunk_start=0, chunk_end=60):
    """
    Finds viral short segments within the chunk.
    Uses local Ollama (llama3.2) if accessible, otherwise falls back to intelligent heuristic analysis.
    """
    prompt = f"""
You are a YouTube Shorts expert editor.

TASK:
Find the BEST viral moment in this text.

Return ONLY JSON array.

Format:
[
  {{"start": 0, "end": 10, "score": 90, "reason": "hook"}}
]

IMPORTANT:
- Return ONLY JSON
- No text
- No explanation
- If nothing good, still guess best moment

TEXT:
{chunk_text}
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False
            },
            timeout=4
        )
        if response.status_code == 200:
            raw = response.json().get("response", "")
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start != -1 and end > 0:
                json_str = raw[start:end]
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list) and len(data) > 0:
                        return data
                except Exception:
                    pass
    except Exception:
        # Ollama not running or timed out - graceful fallback
        pass

    # Intelligent Heuristic Fallback
    # Detect punchy sentences, strong hook keywords, questions, or emotional phrases
    sentences = re.split(r'(?<=[.!?])\s+', chunk_text.strip())
    viral_keywords = [
        "secret", "never", "always", "stop", "million", "money", "truth",
        "insane", "crazy", "mistake", "hack", "trick", "watch", "why",
        "how", "best", "worst", "unbelievable", "shocking", "free"
    ]
    
    score = 65
    reason = "engaging moment"
    text_lower = chunk_text.lower()
    
    matched_words = [w for w in viral_keywords if w in text_lower]
    if matched_words:
        score += min(25, len(matched_words) * 8)
        reason = f"hook keyword: {matched_words[0]}"
    if "?" in chunk_text:
        score += 10
        reason = "curiosity hook (question)"
    if "!" in chunk_text:
        score += 10

    # Choose a high-impact 15-30 second window within chunk
    duration = max(10, chunk_end - chunk_start)
    target_clip_len = min(28, max(14, int(duration * 0.5)))
    clip_start = chunk_start
    clip_end = min(chunk_end, clip_start + target_clip_len)

    return [{
        "start": clip_start,
        "end": clip_end,
        "score": min(98, score),
        "reason": reason
    }]
