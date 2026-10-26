def boost_hook(clip):

    # Ensure score exists
    clip["score"] = clip.get("score", 0)

    # 🔥 BOOST early clips (strong hook behavior)
    if clip["start"] < 5:
        clip["score"] += 30

    elif clip["start"] < 10:
        clip["score"] += 15

    # 🔥 keyword-based boost
    reason = clip.get("reason", "").lower()

    if "hook" in reason:
        clip["score"] += 20

    if "shock" in reason or "crazy" in reason:
        clip["score"] += 15

    if "excitement" in reason:
        clip["score"] += 10

    return clip