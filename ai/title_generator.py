import requests
import re

def generate_title(text):
    prompt = f"""
    Create a viral YouTube Shorts title.

    Rules:
    - max 60 characters
    - emotional + curiosity
    - no hashtags
    - must be clickable

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
            # Clean up quotation marks or extra notes
            res = res.strip('"\n\r ')
            if res and len(res) <= 80:
                return res
    except Exception:
        pass

    # Algorithmic fallback
    clean = re.sub(r'[^\w\s]', '', text).strip()
    words = [w.capitalize() for w in clean.split() if len(w) > 3][:6]
    if words:
        return f"This Changes Everything: {' '.join(words[:4])} 🤯"
    return "You Won't Believe What Happened Next! 😱"