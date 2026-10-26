# ⚡ Vortex Studio: YouTube Video/Audio Downloader & AI Shorts Generator

A full-featured YouTube Video Downloader with multi-resolution quality selection (4K to 360p), Audio Extractor (320kbps MP3 & Lossless), and an AI-powered YouTube Shorts generator with Whisper transcription and animated viral subtitles.

---

## ✨ Features

- **🎬 Video Downloader with Quality Control**:
  - Automatically fetches video metadata (thumbnail, duration, channel, view count).
  - Multi-resolution stream choices: **4K Ultra HD (2160p)**, **2K Quad HD (1440p)**, **Full HD (1080p 60fps)**, **720p HD**, **480p**, and **360p**.
  - Container formats: **MP4**, **MKV**, **WebM**.
  - Real-time download progress with speed (MB/s), ETA, and percentage.
  - In-browser preview player and direct download button.

- **🎵 Audio Extractor**:
  - High-bitrate options: **MP3 (320 kbps, 256 kbps, 192 kbps, 128 kbps)**.
  - Audiophile & Lossless streams: **M4A (Apple AAC)**, **WAV (Studio Master)**, **FLAC**, **OPUS**.

- **🔥 AI Shorts Generator**:
  - **Whisper Speech Recognition**: Extracts full speech segments with exact timestamps.
  - **AI Viral Hook Detection**: Ollama (llama3.2) integration with automatic fallback to heuristic analysis.
  - **9:16 Vertical Cropping**: Automatic aspect ratio conversion for YouTube Shorts, Instagram Reels, and TikTok.
  - **Animated Styled Captions**: Burns customizable subtitles (**Neon Yellow**, **Cyber Cyan**, or **Crisp White**).
  - **Copywriting**: Automatically writes viral titles, hashtags, and packages everything into a ZIP bundle.

- **💎 Dual Interface Options**:
  - **Web Studio (HTML5/CSS3 Glassmorphism UI)** on `http://localhost:5000`.
  - **Streamlit Dashboard UI** on `http://localhost:8501`.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and added to your system PATH.

### 2. Installation
```bash
git clone https://github.com/MiriyalaMonisahith/youtube_video_audio_downloader.git
cd youtube_video_audio_downloader

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Running the App

#### Option A: Web Studio (Recommended)
```bash
python web_server.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

#### Option B: Streamlit Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

#### Option C: Interactive CLI Launcher
```bash
python run.py
```

---

## 📄 License
MIT License
