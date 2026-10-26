import yt_dlp
import whisper

YOUTUBE_URL = input("Enter YouTube URL: ")

print("Downloading video...")

ydl_opts = {
    "outtmpl": "temp/video.%(ext)s",
    "format": "best"
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([YOUTUBE_URL])

print("Loading Whisper...")

model = whisper.load_model("base")

print("Generating transcript...")

result = model.transcribe("temp/video.mp4")

print("\nTRANSCRIPT:\n")
print(result["text"])