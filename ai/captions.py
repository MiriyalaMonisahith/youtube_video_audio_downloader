def generate_srt(segments, clip_start, clip_end):

    def format_time(t):
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        seconds = int(t % 60)
        millis = int((t - int(t)) * 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

    srt = ""
    index = 1
    last_end = 0.0
    prev_text = ""

    for seg in segments:
        raw_text = seg.get("text", "")
        clean_text = "".join(c for c in raw_text if c not in ('\u200b', '\ufeff', '\u200e', '\u200f', '\n', '\r')).strip()
        if not clean_text:
            continue

        s_start = seg.get("start", 0.0)
        s_end = seg.get("end", 0.0)

        # keep only segments inside clip
        if s_end < clip_start or s_start > clip_end:
            continue

        start = max(0.0, s_start - clip_start)
        end = max(0.0, min(s_end - clip_start, clip_end - clip_start))

        # Skip duplicate subtitles within short time window
        if clean_text.lower() == prev_text.lower() and abs(start - last_end) < 1.0:
            continue

        # Prevent overlapping subtitle cues on screen
        if start < last_end:
            start = last_end
        if end <= start:
            end = start + 0.35

        srt += f"{index}\n"
        srt += f"{format_time(start)} --> {format_time(end)}\n"
        srt += f"{clean_text}\n\n"

        index += 1
        last_end = end
        prev_text = clean_text

    return srt