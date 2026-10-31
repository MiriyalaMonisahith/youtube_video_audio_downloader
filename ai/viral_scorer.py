"""
AI Virality Scorer for YouTube Shorts.
Evaluates speech clips on a 0-100 scale using hybrid LLM inference
backed by multi-factor psychological, emotional, and acoustic pacing heuristics.
"""

import re
from typing import Dict, Any, Optional
from ai.llm_client import generate_ai_text

VIRAL_HOOK_PATTERNS = [
    r"\b(secret|never|always|stop|truth|insane|crazy|mistake|hack|trick|money|million|billion|dollar)\b",
    r"\b(warning|danger|shocking|worst|best|nobody|why|how|look|listen|watch|wait)\b",
    r"\b(unbelievable|impossible|blew my mind|terrifying|hilarious|heartbreaking|brilliant|genius|disaster)\b",
    r"\b(what if|did you know|everyone thinks|don't ever|the real reason|i tested)\b"
]

HIGH_RETENTION_WORDS = {
    "secret": 8, "never": 7, "always": 5, "stop": 7, "truth": 8,
    "insane": 7, "crazy": 6, "mistake": 7, "hack": 6, "trick": 5,
    "money": 6, "million": 7, "billion": 7, "warning": 7, "shocking": 8,
    "nobody": 7, "why": 5, "listen": 6, "wait": 7, "unbelievable": 8,
    "exposed": 8, "proof": 7, "guaranteed": 6, "free": 5, "danger": 7
}


def compute_algorithmic_virality(
    text: str,
    duration: float = 30.0,
    words_count: int = 0
) -> Dict[str, Any]:
    """
    Computes rigorous multi-factor virality metrics:
    - Hook Strength (0-100)
    - Emotional Arousal (0-100)
    - Thought Flow & Completeness (0-100)
    - Speech Pacing / WPM (0-100)
    - Retention & Loop Potential (0-100)
    """
    text_clean = text.strip()
    text_lower = text_clean.lower()
    words = text_clean.split()
    w_count = words_count if words_count > 0 else len(words)

    # 1. Hook Score (First 3-5 seconds importance)
    hook_score = 42
    matched_hooks = []
    for kw, boost in HIGH_RETENTION_WORDS.items():
        if re.search(rf"\b{kw}\b", text_lower):
            hook_score += boost
            matched_hooks.append(kw)

    if "?" in text_clean:
        hook_score += 12
        matched_hooks.append("curiosity question")
    if "!" in text_clean:
        hook_score += 8

    # Opening pattern interrupts
    opening_words = " ".join(words[:4]).lower() if len(words) >= 4 else text_lower
    if re.search(r"\b(wait|stop|never|don't|did you|why does|how to|look at|this is)\b", opening_words):
        hook_score += 15
        matched_hooks.append("pattern interrupt")

    hook_score = min(98, max(30, hook_score))

    # 2. Emotional Arousal & Sentiment Intensity
    emotion_score = 45
    for pattern in VIRAL_HOOK_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            emotion_score += min(35, len(matches) * 9)

    if text_clean.isupper() or any(w.isupper() and len(w) > 2 for w in words):
        emotion_score += 6
    emotion_score = min(98, max(35, emotion_score))

    # 3. Speech Cadence & Pacing (Optimal Shorts: 130 - 185 WPM)
    wpm = (w_count / (duration / 60.0)) if duration > 0 else 145.0
    if 130 <= wpm <= 185:
        pacing_score = 96
    elif 110 <= wpm <= 210:
        pacing_score = 84
    elif 90 <= wpm <= 230:
        pacing_score = 70
    else:
        pacing_score = 55

    # 4. Thought Completeness & Clean Boundaries
    has_terminal_punct = bool(re.search(r"[.!?]$", text_clean))
    starts_clean = bool(re.match(r"^[A-Z0-9\"']", text_clean))
    thought_score = 65
    if has_terminal_punct:
        thought_score += 20
    if starts_clean:
        thought_score += 10
    thought_score = min(98, max(40, thought_score))

    # 5. Loop Potential & Retention Sweet Spot
    loop_score = 70
    if re.search(r"\b(because|so|that's why|and then|which means|look at|this is)\b", text_lower[-40:]):
        loop_score = 92
    elif re.search(r"\b(secret|never|always|truth|insane)\b", text_lower[:40]):
        loop_score = 86

    # Retention bonus for 25-45s duration
    retention_score = int(0.35 * hook_score + 0.35 * pacing_score + 0.30 * emotion_score)
    if 24.0 <= duration <= 45.0:
        retention_score = min(98, retention_score + 10)

    # Composite Virality Score
    overall_virality = int(
        0.30 * hook_score +
        0.25 * retention_score +
        0.20 * emotion_score +
        0.15 * pacing_score +
        0.10 * thought_score
    )
    overall_virality = min(99, max(45, overall_virality))

    reason_parts = []
    if hook_score >= 80:
        triggers_txt = ", ".join(matched_hooks[:2]) if matched_hooks else "strong hook"
        reason_parts.append(f"Instant hook ({triggers_txt})")
    if loop_score >= 85:
        reason_parts.append("Seamless loop potential")
    if 130 <= wpm <= 185:
        reason_parts.append(f"High-retention pace ({int(wpm)} WPM)")
    if 25 <= duration <= 45:
        reason_parts.append(f"Ideal duration ({int(duration)}s)")

    reason = " • ".join(reason_parts) if reason_parts else "High-retention candidate"

    return {
        "virality_score": overall_virality,
        "hook_score": hook_score,
        "emotion_score": emotion_score,
        "pacing_score": pacing_score,
        "thought_score": thought_score,
        "retention_score": retention_score,
        "loop_score": loop_score,
        "wpm": int(wpm),
        "reason": reason
    }


def score_clip(text: str) -> int:
    """
    Evaluates clip virality (0 to 100).
    Uses LLM if available, blended with algorithmic metrics for maximum accuracy.
    """
    if not text or not text.strip():
        return 40

    # 1. Compute multi-factor algorithmic baseline
    heuristic_res = compute_algorithmic_virality(text)
    heuristic_score = heuristic_res["virality_score"]

    # 2. Try LLM generation for nuanced semantic understanding
    prompt = f"""
Rate this YouTube Shorts transcript clip for VIRALITY on a scale of 0 to 100.
Consider:
- Immediate 0-3s Hook strength
- Emotional intensity & curiosity
- High-stakes or novelty
- Drop-off risk

Clip text:
"{text.strip()[:400]}"

Respond ONLY with an integer between 0 and 100. No explanation.
"""
    system_prompt = "You are a YouTube Shorts virality algorithm expert. Output only a single integer 0-100."

    ai_output = generate_ai_text(prompt, system=system_prompt, temperature=0.3, timeout=3)
    if ai_output:
        # Extract integer from output
        match = re.search(r"\b(100|[1-9]?[0-9])\b", ai_output)
        if match:
            llm_score = int(match.group(1))
            # Blend 50% LLM + 50% Algorithmic for calibrated stability
            blended = int(0.5 * llm_score + 0.5 * heuristic_score)
            return min(99, max(35, blended))

    return heuristic_score


def score_clip_detailed(
    text: str,
    duration: float = 30.0,
    words_count: int = 0
) -> Dict[str, Any]:
    """Returns detailed virality metrics including sub-scores and reasoning."""
    metrics = compute_algorithmic_virality(text, duration=duration, words_count=words_count)
    # Blend with LLM if available
    llm_s = score_clip(text)
    metrics["virality_score"] = int(0.6 * metrics["virality_score"] + 0.4 * llm_s)
    return metrics
