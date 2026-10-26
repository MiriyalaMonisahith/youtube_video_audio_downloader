from video.cutter import cut_clip

cut_clip(
    "temp/video.mp4",
    10,
    40,
    "shorts/clip1.mp4"
)

print("Clip created!")