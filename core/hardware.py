import subprocess
import functools
from core.config import FFMPEG_BIN

@functools.lru_cache(maxsize=1)
def get_best_hardware_encoder() -> dict:
    """
    Probes system FFmpeg installation for hardware acceleration encoders.
    Returns encoder name and optimal flags.
    """
    candidates = [
        ("h264_nvenc", ["-preset", "p4", "-tune", "hq"], "NVIDIA NVENC"),
        ("h264_qsv", ["-preset", "faster", "-global_quality", "20"], "Intel QuickSync"),
        ("h264_amf", ["-quality", "speed"], "AMD AMF"),
        ("h264_mf", ["-rate_control", "cbr"], "Windows MediaFoundation"),
        ("libx264", ["-preset", "veryfast", "-crf", "20"], "Software CPU")
    ]

    for encoder, flags, name in candidates:
        try:
            cmd = [
                FFMPEG_BIN, "-y",
                "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.05",
                "-c:v", encoder,
                "-f", "null", "-"
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                is_hardware = encoder != "libx264"
                return {
                    "encoder": encoder,
                    "name": name,
                    "flags": flags,
                    "is_hardware": is_hardware,
                    "type": "hardware" if is_hardware else "software",
                    "description": f"{name} ({encoder})"
                }
        except Exception:
            continue

    return {
        "encoder": "libx264",
        "name": "Software CPU",
        "flags": ["-preset", "veryfast", "-crf", "20"],
        "is_hardware": False,
        "type": "software",
        "description": "libx264 (CPU Fallback)"
    }


def detect_hardware_encoder() -> dict:
    """Convenience alias for get_best_hardware_encoder."""
    return get_best_hardware_encoder()


def get_optimal_encoder_args() -> list:
    """Returns the FFmpeg CLI arguments for the fastest available video encoder."""
    info = get_best_hardware_encoder()
    return ["-c:v", info["encoder"], *info["flags"], "-pix_fmt", "yuv420p"]
