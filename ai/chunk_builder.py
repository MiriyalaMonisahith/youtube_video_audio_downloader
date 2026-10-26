def build_chunks(segments, chunk_size=60):

    chunks = []

    current_text = ""
    start_time = segments[0]["start"]

    for segment in segments:

        current_text += " " + segment["text"]

        if segment["end"] - start_time >= chunk_size:

            chunks.append({
                "start": start_time,
                "end": segment["end"],
                "text": current_text
            })

            current_text = ""
            start_time = segment["end"]

    return chunks