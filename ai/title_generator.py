"""
AI Viral Title Generator for YouTube Shorts.
Produces high-CTR, curiosity-driven titles adhering to mobile display boundaries (under 60 chars).
Uses hybrid LLM copy generation + psychological title formula heuristics.
"""

import re
from typing import List
from ai.llm_client import generate_ai_text

VIRAL_TITLE_TEMPLATES = [
    # 1. Curiosity Gap
    "{hook}... and nobody noticed 🤯",
    "Wait until the end of this... 😱",
    "The secret nobody talks about: {topic}",
    # 2. Contrarian / Warning
    "Stop doing this right now! 🛑",
    "Never make this 1 mistake ❌",
    "Why 99% of people get this wrong 🤦‍♂️",
    # 3. High Stakes & Hacks
    "This 1 trick changes everything 🔥",
    "How this ACTUALLY works in 60s ⏱️",
    "The truth about {topic} exposed ⚡"
]


def _clean_title(raw: str) -> str:
    """Cleans up LLM title output: removes markdown, outer quotes, trailing periods."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^[\"'\s]+|[\"'\s]+$", "", cleaned)
    cleaned = re.sub(r"#\w+", "", cleaned)  # remove hashtags from title
    cleaned = cleaned.replace("**", "").replace("__", "").strip()
    if cleaned.endswith("."):
        cleaned = cleaned[:-1].strip()
    return cleaned[:70]


def generate_title_variants(text: str, count: int = 3) -> List[str]:
    """
    Generates high-CTR title variants tuned for YouTube Shorts discovery.
    """
    clean_text = text.strip()
    if not clean_text:
        return [
            "Wait until the end... 😱",
            "This changes everything 🔥",
            "Never make this mistake! 🛑"
        ]

    # 1. Attempt LLM Generation
    prompt = f"""
Create 3 high-CTR, viral YouTube Shorts titles for this clip.
Rules:
- Max 60 characters each
- Curiosity gap, high stakes, or pattern interrupt
- Include 1 emoji per title
- NO hashtags
- Numbered list: 1., 2., 3.

Transcript:
"{clean_text[:350]}"
"""
    system_prompt = "You are a master YouTube Shorts title strategist. Return only 3 numbered viral titles."

    ai_output = generate_ai_text(prompt, system=system_prompt, temperature=0.7, timeout=4)
    if ai_output:
        lines = [line.strip() for line in ai_output.split("\n") if line.strip()]
        extracted = []
        for line in lines:
            # Strip number prefix e.g. "1. ", "1) "
            clean_line = re.sub(r"^\d+[\.\)]\s*", "", line)
            clean_line = _clean_title(clean_line)
            if 10 <= len(clean_line) <= 75:
                extracted.append(clean_line)
        if len(extracted) >= count:
            return extracted[:count]
        elif extracted:
            return extracted

    # 2. Intelligent NLP Heuristic Fallback
    words = [w.strip(".,!?\"'()").capitalize() for w in clean_text.split() if len(w) > 3]
    topic = " ".join(words[:3]) if words else "This Moment"
    first_few = " ".join(words[:4]) if words else "Watch Closely"

    # Identify if clip contains a question
    has_question = "?" in clean_text
    variants = []

    if has_question:
        q_match = re.search(r"([^.!?]+\?)", clean_text)
        if q_match:
            q_text = q_match.group(1).strip()
            if len(q_text) <= 55:
                variants.append(f"{q_text} 🤯")

    variants.append(f"The Truth About {topic} 🔥")
    variants.append(f"Wait for what happens next... 😱")
    variants.append(f"Stop doing this right now! 🛑")
    variants.append(f"This 1 trick changes {topic} ⚡")

    return variants[:count]


def generate_title(text: str) -> str:
    """
    Generates single viral title.
    Maintains 100% backwards compatibility with legacy callers.
    """
    variants = generate_title_variants(text, count=1)
    return variants[0] if variants else "You Won't Believe What Happened Next! 😱"
