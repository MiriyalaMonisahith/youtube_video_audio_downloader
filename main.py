from Downloads_python.download_video import download_video
from ai.transcript import get_transcript

url = input("Enter YouTube URL: ")

download_video(url)

result = get_transcript("temp/video.mp4")

print(result["text"])