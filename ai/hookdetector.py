"""
AI Hook Detector for YouTube Shorts.
Identifies high-impact opening moments, pattern interrupts, curiosity gaps,
and algorithmic retention drivers in speech transcripts.
"""

import re
from typing import Dict, Any

HOOK_PATTERNS = {
    "Pattern Interrupt": [
        r"\b(wait|stop|listen|look at this|don't scroll|hear me out|hold on)\b",
        r"\b(never do this|stop doing|delete this right now|throw away)\b"
    ],
    "Curiosity Gap": [
        r"\b(did you know|what if|the real reason|the truth about|the secret to)\b",
        r"\b(nobody talks about|everyone is lying about|hidden in plain sight)\b",
        r"\b(i bet you didn't know|what happens next|the craziest thing)\b"
    ],
    "Contrarian / Debunking": [
        r"\b(everyone thinks|most people believe|you've been told|that's a lie)\b",
        r"\b(actually wrong|stop believing|is completely fake|total myth)\b"
    ],
    "High Stakes & Numbers": [
        r"\b(\$|million|billion|thousand|dollar|hours|days|years|ruined|lost everything)\b",
        r"\b(danger|warning|disaster|emergency|mistake cost me)\b"
    ],
    "Question Hook": [
        r"^(why|how|what|who|where|when|can you|would you)\b.*\?",
        r"\?$"
    ]
}

POWER_WORDS = {
    "secret": 12, "insane": 10, "crazy": 8, "shocking": 12, "unbelievable": 12,
    "mistake": 10, "hack": 8, "truth": 10, "never": 8, "warning": 10,
    "exposed": 12, "worst": 8, "best": 6, "banned": 12, "illegal": 10,
    "impossible": 10, "genius": 8, "disaster": 10, "ruined": 10
}


def analyze_hook(text: str, start_time: float = 0.0) -> Dict[str, Any]:
    """
    Analyzes the opening text of a clip for hook potency, category, and retention strength.
    """
    clean_text = text.strip()
    text_lower = clean_text.lower()
    first_sentence = re.split(r"(?<=[.!?])\s+", clean_text)[0] if clean_text else ""
    first_lower = first_sentence.lower()

    detected_categories = []
    hook_boost = 0

    # 1. Evaluate Hook Categories in opening sentence
    for cat_name, patterns in HOOK_PATTERNS.items():
        matched = False
        for p in patterns:
            if re.search(p, first_lower) or re.search(p, text_lower[:120]):
                matched = True
                break
        if matched:
            detected_categories.append(cat_name)
            hook_boost += 14

    # 2. Check Power Words
    power_matches = []
    for word, boost in POWER_WORDS.items():
        if re.search(rf"\b{word}\b", text_lower[:150]):
            hook_boost += boost
            power_matches.append(word)

    # 3. Position advantage (Videos start with highest audience attention)
    if start_time < 4.0:
        hook_boost += 18
    elif start_time < 12.0:
        hook_boost += 10
    elif start_time < 25.0:
        hook_boost += 5

    # 4. Question in opening 50 characters
    if "?" in first_sentence[:60]:
        hook_boost += 12
        if "Question Hook" not in detected_categories:
            detected_categories.append("Question Hook")

    primary_category = detected_categories[0] if detected_categories else "Engaging Statement"
    hook_strength = min(100, max(20, 45 + hook_boost))

    return {
        "hook_score": hook_strength,
        "hook_type": primary_category,
        "categories": detected_categories,
        "power_words": power_matches[:3],
        "first_line": first_sentence[:80]
    }


def boost_hook(clip: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhances clip dictionary with deep hook analysis and calibrated score boosts.
    Maintains full backwards compatibility with legacy pipeline.
    """
    clip["score"] = clip.get("score", 0)
    clip_text = clip.get("text", "")
    reason = clip.get("reason", "").lower()
    start_t = float(clip.get("start", 0))

    analysis = analyze_hook(clip_text or reason, start_time=start_t)

    # Calculate boost amount based on verified NLP indicators
    boost_val = 0
    if analysis["hook_score"] >= 80:
        boost_val += 25
    elif analysis["hook_score"] >= 65:
        boost_val += 15
    else:
        boost_val += 8

    # Keyword boosts from reasons
    if "hook" in reason:
        boost_val += 12
    if "shock" in reason or "crazy" in reason or "insane" in reason:
        boost_val += 10
    if "curiosity" in reason:
        boost_val += 10

    # Apply boost
    clip["score"] = min(99, clip["score"] + boost_val)
    clip["hook_type"] = analysis["hook_type"]
    clip["hook_score"] = analysis["hook_score"]

    # Enrich reason string
    if analysis["categories"]:
        type_str = analysis["categories"][0]
        if type_str.lower() not in reason:
            clip["reason"] = f"{type_str}: {clip.get('reason', 'High engagement')}"

    return clip
