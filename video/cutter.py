import subprocess

def cut_clip_vertical(input_video, start, end, output_file):

    subprocess.run([
    "ffmpeg",
    "-y",

    "-ss", str(start),
    "-i", input_video,
    "-t", str(end - start),

    "-vf",
    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,unsharp=5:5:1.0",

    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "17",

    "-c:a", "aac",
    "-b:a", "192k",
    "-ar", "44100",
    "-ac", "2",

    "-map", "0:v:0",
    "-map", "0:a:0?",

    "-shortest",

    output_file
])
    