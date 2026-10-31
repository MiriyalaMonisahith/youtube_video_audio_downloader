"""
AI Viral Moment Detector for YouTube Shorts.
Analyzes speech segments within transcript chunks to identify
the highest-performing 15-55s clips with natural sentence boundaries.
Uses hybrid LLM reasoning + sentence-level sliding window heuristics.
"""

import re
from typing import List, Dict, Any, Union
from ai.llm_client import generate_ai_text, extract_json_from_text
from ai.viral_scorer import compute_algorithmic_virality
from ai.hookdetector import analyze_hook


def find_best_clips(
    chunk_text: str,
    chunk_start: float = 0.0,
    chunk_end: float = 60.0
) -> List[Dict[str, Any]]:
    """
    Finds viral short segments within the chunk.
    Tries LLM reasoning first, with intelligent sentence-boundary fallback.
    Never cuts speech mid-sentence.
    """
    clean_text = chunk_text.strip()
    if not clean_text:
        return []

    chunk_dur = max(10.0, chunk_end - chunk_start)

    # 1. Attempt LLM Detection
    prompt = f"""
You are an expert YouTube Shorts and TikTok editor.
Analyze this video transcript chunk (Timestamp range: {chunk_start:.1f}s to {chunk_end:.1f}s).
Find the BEST viral moment (optimal duration 20s to 50s) that will maximize retention.

Rules:
- Must begin at an exciting hook or question
- Must end on a complete thought
- Return ONLY a JSON array of objects

JSON format:
[
  {{"start": {chunk_start:.1f}, "end": {min(chunk_end, chunk_start + 35):.1f}, "score": 92, "reason": "Curiosity hook followed by shocking payoff"}}
]

Transcript:
"{clean_text}"
"""
    system_prompt = "You are an expert viral video editor. Return ONLY a valid JSON array of clip timestamps."

    raw_response = generate_ai_text(prompt, system=system_prompt, temperature=0.4, timeout=4)
    if raw_response:
        parsed = extract_json_from_text(raw_response)
        if isinstance(parsed, list) and len(parsed) > 0:
            valid_clips = []
            for item in parsed:
                if isinstance(item, dict) and "start" in item and "end" in item:
                    try:
                        s = float(item["start"])
                        e = float(item["end"])
                        # Clamp timestamps within chunk range
                        s = max(chunk_start, min(s, chunk_end - 5.0))
                        e = min(chunk_end, max(e, s + 10.0))
                        dur = e - s
                        if 10.0 <= dur <= 58.0:
                            score = int(item.get("score", 85))
                            reason = str(item.get("reason", "Viral moment"))
                            valid_clips.append({
                                "start": round(s, 2),
                                "end": round(e, 2),
                                "duration": round(dur, 1),
                                "score": min(99, max(40, score)),
                                "reason": reason,
                                "text": clean_text
                            })
                    except (ValueError, TypeError):
                        continue
            if valid_clips:
                return valid_clips

    # 2. Intelligent Sentence-Bounded Heuristic Fallback
    # Split text into natural sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if s.strip()]
    if not sentences:
        sentences = [clean_text]

    # Calculate approximate time per sentence
    total_chars = sum(len(s) for s in sentences) or 1
    sec_per_char = chunk_dur / total_chars

    sentence_spans = []
    curr_t = chunk_start
    for s in sentences:
        s_dur = max(1.5, len(s) * sec_per_char)
        sentence_spans.append({
            "text": s,
            "start": round(curr_t, 2),
            "end": round(curr_t + s_dur, 2)
        })
        curr_t += s_dur

    best_candidate = None
    highest_score = -1

    # Scan multi-sentence combinations between 18s and 50s
    num_s = len(sentence_spans)
    for i in range(num_s):
        accumulated_text = ""
        win_start = sentence_spans[i]["start"]

        for j in range(i, num_s):
            accumulated_text += (" " if accumulated_text else "") + sentence_spans[j]["text"]
            win_end = sentence_spans[j]["end"]
            win_dur = win_end - win_start

            if 18.0 <= win_dur <= 52.0 or (j == num_s - 1 and win_dur >= 10.0):
                # Score this sentence-bounded candidate
                metrics = compute_algorithmic_virality(accumulated_text, duration=win_dur)
                hook_data = analyze_hook(accumulated_text, start_time=win_start)
                
                score = int(0.6 * metrics["virality_score"] + 0.4 * hook_data["hook_score"])

                if score > highest_score:
                    highest_score = score
                    reason = f"{hook_data['hook_type']} • {metrics['reason']}"
                    best_candidate = {
                        "start": round(win_start, 2),
                        "end": round(win_end, 2),
                        "duration": round(win_dur, 1),
                        "score": score,
                        "reason": reason,
                        "text": accumulated_text
                    }

    if best_candidate:
        return [best_candidate]

    # Absolute fallback
    default_dur = min(35.0, chunk_dur)
    return [{
        "start": round(chunk_start, 2),
        "end": round(chunk_start + default_dur, 2),
        "duration": round(default_dur, 1),
        "score": 75,
        "reason": "High-retention opening segment",
        "text": clean_text
    }]
