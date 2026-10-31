"""
AI Clip Ranker for YouTube Shorts.
Evaluates candidate clips based on composite virality, retention sweet-spots,
hook potency, and speech density, with non-overlapping duplicate suppression.
"""

from typing import List, Dict, Any


def rank_clips(
    clips: List[Dict[str, Any]],
    min_separation_sec: float = 8.0,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Ranks clips descending by virality potential and deduplicates overlapping windows.
    Returns the top distinct candidates.
    """
    if not clips:
        return []

    scored_candidates = []

    for clip in clips:
        start = float(clip.get("start", 0))
        end = float(clip.get("end", start + 30))
        duration = max(1.0, end - start)
        base_score = float(clip.get("score", 50))
        reason = str(clip.get("reason", "")).lower()

        # 1. Algorithmic Duration Multiplier (Shorts sweet spot: 26s - 45s)
        dur_bonus = 0
        if 26.0 <= duration <= 45.0:
            dur_bonus += 25
        elif 20.0 <= duration <= 55.0:
            dur_bonus += 15
        elif 12.0 <= duration <= 20.0:
            dur_bonus += 8

        # 2. Hook Strength Bonus
        hook_bonus = 0
        if "hook" in reason or clip.get("hook_type"):
            hook_bonus += 20
        if "curiosity" in reason or "shock" in reason or "insane" in reason:
            hook_bonus += 15
        if "pattern interrupt" in reason:
            hook_bonus += 15

        # 3. Loopability Bonus
        loop_bonus = 10 if "loop" in reason else 0

        # Composite Rank Score
        composite_rank = base_score + dur_bonus + hook_bonus + loop_bonus
        scored_candidates.append((composite_rank, clip))

    # Sort descending
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    # 4. Non-Maximum Suppression (Deduplication)
    # Ensure clips don't overlap heavily
    filtered: List[Dict[str, Any]] = []
    for rank_score, clip in scored_candidates:
        c_start = float(clip["start"])
        c_end = float(clip["end"])

        overlaps = False
        for selected in filtered:
            s_start = float(selected["start"])
            s_end = float(selected["end"])
            # If start points are close, or overlap by more than 50%
            if abs(c_start - s_start) < min_separation_sec:
                overlaps = True
                break
            overlap_dur = max(0.0, min(c_end, s_end) - max(c_start, s_start))
            if overlap_dur > 0.5 * min(c_end - c_start, s_end - s_start):
                overlaps = True
                break

        if not overlaps:
            clip["rank"] = len(filtered) + 1
            clip["composite_score"] = round(rank_score, 1)
            # Ensure virality_score is also present for compatibility
            clip["virality_score"] = clip.get("score", int(min(99, rank_score * 0.7)))
            filtered.append(clip)
            if len(filtered) >= top_n:
                break

    return filtered
