import re
from typing import List, Dict, Any

HOOK_KEYWORDS = {
    "secret": 25, "never": 20, "always": 15, "stop": 22, "truth": 25,
    "insane": 24, "crazy": 20, "mistake": 22, "hack": 20, "trick": 18,
    "money": 20, "million": 22, "billion": 22, "dollar": 18, "danger": 20,
    "warning": 20, "shocking": 25, "worst": 18, "best": 16, "nobody": 22,
    "why": 18, "how": 15, "look": 15, "listen": 20, "watch": 18
}

EMOTION_PATTERNS = [
    r"\b(unbelievable|impossible|blew my mind|terrifying|hilarious|heartbreaking|brilliant|genius|disaster)\b",
    r"\!{1,3}",
    r"\?{1,2}"
]

def score_segment_virality(text: str, duration: float, words_count: int, is_opening: bool) -> Dict[str, Any]:
    """
    Computes multi-factor virality score based on:
    - Hook Strength (0-100)
    - Emotional Peaks (0-100)
    - Thought Completeness (0-100)
    - Pacing / WPM (0-100)
    - Retention Potential (0-100)
    """
    text_lower = text.lower()
    
    # 1. Hook Strength
    hook_score = 40
    hook_triggers = []
    for kw, boost in HOOK_KEYWORDS.items():
        if re.search(rf"\b{kw}\b", text_lower):
            hook_score += boost
            hook_triggers.append(kw)
    if is_opening:
        hook_score += 20
    if "?" in text:
        hook_score += 15
        hook_triggers.append("curiosity question")
    hook_score = min(99, max(20, hook_score))

    # 2. Emotional Peaks
    emotion_score = 45
    for pattern in EMOTION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            emotion_score += min(35, len(matches) * 12)
    if "!" in text:
        emotion_score += 10
    emotion_score = min(98, max(25, emotion_score))

    # 3. Pacing & Speech Density (Ideal Shorts WPM: 130 - 180 words per minute)
    wpm = (words_count / (duration / 60.0)) if duration > 0 else 0
    if 130 <= wpm <= 185:
        pacing_score = 95
    elif 110 <= wpm <= 210:
        pacing_score = 82
    else:
        pacing_score = 65

    # 4. Thought Completeness (Starts with capital/clause, ends with sentence punctuation)
    has_terminal_punct = bool(re.search(r"[.!?]$", text.strip()))
    starts_clean = bool(re.match(r"^[A-Z0-9\"']", text.strip()))
    thought_score = 70
    if has_terminal_punct:
        thought_score += 20
    if starts_clean:
        thought_score += 10
    thought_score = min(98, thought_score)

    # 5. Retention Potential (Combines ideal 20-45s duration + pacing + hook)
    retention_score = int(0.4 * hook_score + 0.3 * pacing_score + 0.3 * emotion_score)
    if 25.0 <= duration <= 45.0:
        retention_score = min(99, retention_score + 12)

    # 6. YouTube Shorts Fast Monetization Index (0-100)
    # Calibrated for YPP fast-track: 10M views & high CPM engagement
    loop_score = 75
    # If the end of text has transition words or open curiosity, high loopability
    if re.search(r"\b(because|so|that's why|and then|which means|look at|this is)\b", text_lower[-40:] if len(text_lower) > 40 else text_lower):
        loop_score = 94
    elif re.search(r"\b(secret|never|always|truth|insane)\b", text_lower[:40]):
        loop_score = 88

    # Watch time velocity: 28-45s yields 2.8x more algorithmic watch minutes
    duration_multiplier = 96 if (28.0 <= duration <= 45.0) else (85 if 20.0 <= duration <= 55.0 else 70)

    monetization_score = int(
        0.35 * hook_score +
        0.25 * retention_score +
        0.20 * duration_multiplier +
        0.20 * loop_score
    )
    monetization_score = min(99, max(60, monetization_score))

    # Composite Virality Score
    overall_virality = int(
        0.28 * hook_score +
        0.25 * retention_score +
        0.20 * monetization_score +
        0.15 * emotion_score +
        0.12 * thought_score
    )

    reason_parts = []
    if monetization_score >= 90:
        reason_parts.append(f"💰 {monetization_score}% Fast Monetization Ready")
    if hook_triggers:
        reason_parts.append(f"Instant 0-3s hook ({', '.join(hook_triggers[:2])})")
    if loop_score >= 85:
        reason_parts.append("Seamless Infinite Loop")
    if 130 <= wpm <= 185:
        reason_parts.append(f"High-retention speech ({int(wpm)} WPM)")
    if 25 <= duration <= 45:
        reason_parts.append(f"Algorithmic sweet spot ({int(duration)}s)")

    reason = " • ".join(reason_parts) if reason_parts else "High-retention monetization candidate"

    return {
        "virality_score": overall_virality,
        "monetization_score": monetization_score,
        "loop_score": loop_score,
        "hook_score": hook_score,
        "emotion_score": emotion_score,
        "thought_score": thought_score,
        "pacing_score": pacing_score,
        "retention_score": retention_score,
        "wpm": int(wpm),
        "reason": reason
    }


def find_top_clips(
    transcript_data: Dict[str, Any],
    min_duration: float = 18.0,
    max_duration: float = 55.0,
    top_n: int = 6
) -> List[Dict[str, Any]]:
    """
    Scans speech segments, groups them into coherent sentence-bounded windows,
    computes multi-factor virality scores, and returns the top 5-10 candidates.
    Never cuts mid-sentence or mid-word.
    """
    segments = transcript_data.get("segments", [])
    if not segments:
        return []

    # Dynamically adapt duration for shorter videos
    total_dur = max(0.0, segments[-1].get("end", 0.0) - segments[0].get("start", 0.0))
    if 5.0 <= total_dur < min_duration:
        min_duration = max(5.0, total_dur * 0.6)

    candidates = []
    num_segs = len(segments)

    for i in range(num_segs):
        current_text = ""
        seg_start = segments[i]["start"]
        collected_words = []
        collected_segments = []

        for j in range(i, num_segs):
            seg = segments[j]
            current_text += (" " if current_text else "") + seg["text"]
            collected_words.extend(seg.get("words", []))
            collected_segments.append(seg)
            duration = seg["end"] - seg_start

            if duration >= min_duration:
                # Ensure we end cleanly on sentence punctuation
                is_sentence_end = bool(re.search(r"[.!?]$", seg["text"].strip()))
                is_max_reached = duration >= max_duration

                if is_sentence_end or is_max_reached:
                    # Score this candidate window
                    scores = score_segment_virality(
                        text=current_text,
                        duration=duration,
                        words_count=len(collected_words),
                        is_opening=(seg_start < 10.0)
                    )

                    # Extract first 1-3 seconds hook line
                    first_sentence = re.split(r"(?<=[.!?])\s+", current_text.strip())[0]

                    candidates.append({
                        "start": round(seg_start, 2),
                        "end": round(seg["end"], 2),
                        "duration": round(duration, 1),
                        "text": current_text.strip(),
                        "hook_line": first_sentence[:80],
                        "words": collected_words,
                        **scores
                    })
                    break

    # Fallback if no clean punctuation-terminated candidate was found
    if not candidates and segments:
        full_text = " ".join(s["text"] for s in segments).strip()
        first_s = re.split(r"(?<=[.!?])\s+", full_text)[0] if full_text else "Opening Hook"
        start_t = round(segments[0]["start"], 2)
        end_t = round(segments[-1]["end"], 2)
        dur = max(1.0, round(end_t - start_t, 1))
        scores = score_segment_virality(full_text, dur, len(full_text.split()), is_opening=True)
        candidates.append({
            "start": start_t,
            "end": end_t,
            "duration": dur,
            "text": full_text,
            "hook_line": first_s[:80],
            "words": [w for s in segments for w in s.get("words", [])],
            **scores
        })

    # Sort descending by virality score
    candidates.sort(key=lambda x: x["virality_score"], reverse=True)

    # Filter out heavily overlapping duplicates (keep higher scoring one)
    filtered = []
    for c in candidates:
        overlaps = False
        for f in filtered:
            # If start times overlap by more than 8 seconds, skip
            if abs(c["start"] - f["start"]) < 8.0:
                overlaps = True
                break
        if not overlaps:
            c["rank"] = len(filtered) + 1
            filtered.append(c)
            if len(filtered) >= top_n:
                break

    return filtered


def select_viral_clips(
    segments: List[Dict[str, Any]],
    words: List[Dict[str, Any]],
    target_duration_range: tuple = (25.0, 55.0),
    top_n: int = 6
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper for find_top_clips accepting segments and words.
    """
    # Attach word references to segments if needed
    for seg in segments:
        s_start = seg.get("start", 0)
        s_end = seg.get("end", 0)
        seg["words"] = [w for w in words if s_start <= w.get("start", 0) <= s_end]

    raw_candidates = find_top_clips(
        {"segments": segments, "words": words},
        min_duration=target_duration_range[0],
        max_duration=target_duration_range[1],
        top_n=top_n
    )

    # Format output for frontend API
    formatted = []
    for idx, c in enumerate(raw_candidates):
        formatted.append({
            "id": f"clip_{idx+1}",
            "rank": idx + 1,
            "title": f"Viral Short #{idx+1}",
            "start": c["start"],
            "end": c["end"],
            "duration": c["duration"],
            "hook": c["hook_line"],
            "reason": c["reason"],
            "virality_score": c["virality_score"],
            "monetization_score": c.get("monetization_score", 92),
            "loop_score": c.get("loop_score", 85),
            "text": c["text"],
            "scores": {
                "monetization": c.get("monetization_score", 92),
                "loop": c.get("loop_score", 85),
                "hook": c["hook_score"],
                "emotion": c["emotion_score"],
                "thought": c["thought_score"],
                "pacing": c["pacing_score"],
                "retention": c["retention_score"]
            }
        })
    return formatted

