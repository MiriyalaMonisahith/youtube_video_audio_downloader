import requests

def score_clip(text):

    prompt = f"""
    Rate this transcript clip for VIRALITY (0 to 100).

    Consider:
    - emotional intensity
    - curiosity
    - shock value
    - hook strength

    Return ONLY a number.

    Text:
    {text}
    """

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False
        }
    )

    try:
        return int(response.json()["response"].strip())
    except:
        return 50