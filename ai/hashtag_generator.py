import requests
import re

def generate_hashtags(text):
    prompt = f"""
    Generate 10 YouTube Shorts hashtags.

    Rules:
    - relevant to content
    - include viral tags like #shorts #viral
    - no explanations

    Text:
    {text}
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
            res = response.json().get("response", "").strip()
            if "#" in res:
                return res
    except Exception:
        pass

    # Heuristic fallback
    clean = re.sub(r'[^\w\s]', '', text).lower()
    words = list(set([w for w in clean.split() if len(w) > 4]))[:5]
    content_tags = " ".join([f"#{w}" for w in words])
    return f"#shorts #viral #fyp #trending #shortsfeed {content_tags}".strip()