"""
AI Face Tracking & Smart Reframe for 9:16 Vertical Shorts.
Detects the active speaker using OpenCV Computer Vision Haar Cascades
and dynamically pans the 9:16 vertical crop with smooth cinematic motion damping.
Preserves original audio track via single-pass FFmpeg multiplexing.
"""

import os
import shutil
import subprocess
import cv2
from typing import Optional

FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


def get_face_detector() -> Optional[cv2.CascadeClassifier]:
    """Loads OpenCV Haar Cascade frontal face detector."""
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    if os.path.exists(cascade_path):
        cascade = cv2.CascadeClassifier(cascade_path)
        if not cascade.empty():
            return cascade
    return None


def auto_zoom(
    input_path: str,
    output_path: str,
    smooth_alpha: float = 0.15,
    detect_interval: int = 2
) -> str:
    """
    Intelligently crops 16:9 horizontal video to 9:16 vertical, dynamically
    tracking the speaker's face with smooth pan-and-scan camera motion.
    Preserves original video audio.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")

    face_cascade = get_face_detector()
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Target 9:16 vertical crop width inside original frame
    crop_w = int(height * 9 / 16)
    if crop_w > width:
        crop_w = width

    # Temporary silent video file for OpenCV writer
    temp_silent = output_path + ".temp_silent.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_silent, fourcc, fps, (1080, 1920))

    # Tracking state: Start at horizontal center
    curr_cx = float(width // 2)
    target_cx = float(width // 2)
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            h, w = frame.shape[:2]

            # Run face detection periodically for high performance
            if face_cascade and (frame_idx % detect_interval == 0):
                # Downscale for faster detection
                scale = 360.0 / h
                small_h = 360
                small_w = int(w * scale)
                small_frame = cv2.resize(frame, (small_w, small_h))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.15,
                    minNeighbors=4,
                    minSize=(30, 30)
                )

                if len(faces) > 0:
                    # Pick largest face (primary speaker)
                    best_face = max(faces, key=lambda f: f[2] * f[3])
                    fx, fy, fw, fh = best_face
                    # Scale back to full resolution
                    face_center_x = (fx + fw / 2.0) / scale
                    target_cx = face_center_x
                else:
                    # Slowly drift towards center when no face is found
                    target_cx = w / 2.0

            # Apply Exponential Moving Average (EMA) smoothing for cinematic pan
            curr_cx = curr_cx * (1.0 - smooth_alpha) + target_cx * smooth_alpha

            # Calculate crop bounds and prevent out-of-frame clipping
            half_crop = crop_w // 2
            x1 = int(curr_cx - half_crop)
            x2 = x1 + crop_w

            if x1 < 0:
                x1 = 0
                x2 = crop_w
            elif x2 > w:
                x2 = w
                x1 = max(0, w - crop_w)

            cropped = frame[:, x1:x2]
            resized = cv2.resize(cropped, (1080, 1920), interpolation=cv2.INTER_LINEAR)
            out.write(resized)

    finally:
        cap.release()
        out.release()

    # Multiplex original audio back into the final video
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    mux_cmd = [
        FFMPEG_BIN, "-y",
        "-i", temp_silent,
        "-i", input_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-shortest",
        output_path
    ]

    res = subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0 or not os.path.exists(output_path):
        # Fallback to silent video if audio multiplexing fails
        shutil.move(temp_silent, output_path)
    else:
        if os.path.exists(temp_silent):
            os.remove(temp_silent)

    return output_path
