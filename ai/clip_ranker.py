def rank_clips(clips):

    scored = []

    for clip in clips:

        score = 0

        duration = clip["end"] - clip["start"]
        if 5 <= duration <= 25:
            score += 30

        score += clip.get("score", 0)

        if "hook" in clip.get("reason", "").lower():
            score += 25

        scored.append((score, clip))

    scored.sort(reverse=True, key=lambda x: x[0])

    return [c[1] for c in scored]