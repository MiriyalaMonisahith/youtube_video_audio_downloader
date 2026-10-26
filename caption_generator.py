def generate_srt(segments, clip_start, clip_end):

    def format_time(t):
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        seconds = int(t % 60)
        millis = int((t - int(t)) * 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

    srt = ""
    index = 1

    for seg in segments:

        # 1. KEEP ONLY SEGMENTS INSIDE CLIP
        if seg["end"] < clip_start:
            continue
        if seg["start"] > clip_end:
            continue

        # 2. SHIFT TIMING TO CLIP SPACE
        start = max(0, seg["start"] - clip_start)
        end = max(0, seg["end"] - clip_start)

        srt += f"{index}\n"
        srt += f"{format_time(start)} --> {format_time(end)}\n"
        srt += f"{seg['text'].strip()}\n\n"

        index += 1

    return srt