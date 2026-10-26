import sys
import os
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("=" * 60)
    print("⚡ VORTEX STUDIO - VIDEO DOWNLOADER & AI SHORTS")
    print("=" * 60)
    print("1. Launch Modern Web Studio (Recommended - Ultra-Fast Web UI)")
    print("2. Launch Streamlit UI (app.py)")
    print("=" * 60)

    choice = input("Enter your choice (1 or 2) [default: 1]: ").strip()
    if choice == "2":
        print("\nStarting Streamlit App on http://localhost:8501 ...\n")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    else:
        print("\nStarting Vortex Web Studio on http://localhost:5000 ...\n")
        subprocess.run([sys.executable, "web_server.py"])

if __name__ == "__main__":
    main()
