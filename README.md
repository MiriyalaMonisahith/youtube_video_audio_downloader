# ⚡ Vortex Studio Pro: High-Speed AI Shorts Creator & Media Downloader

Vortex Studio Pro upgrades YouTube link processing into a production-quality, hardware-accelerated pipeline capable of generating 60-second viral 9:16 vertical shorts in under 60 seconds with word-by-word animated karaoke captions, multi-factor AI scoring, and copyright safety guardrails.

---

## 🚀 7-Pillar Production Architecture

### 1. Speed & Pipeline Profiling (Target: 60s short in <60s)
- **Audio-First Ingestion**: Extracts a 3–8 MB audio stream in ~2 seconds to run Whisper and virality scoring immediately, rather than waiting 10+ minutes to download full videos.
- **Section Trimming**: Uses `yt-dlp` precision `download_ranges` to fetch only the chosen 30–50s video window on demand.
- **Hardware Acceleration (Single-Pass FFmpeg)**: Auto-detects Intel QuickSync (`h264_qsv`), NVIDIA NVENC (`h264_nvenc`), AMD AMF (`h264_amf`), or Windows MediaFoundation (`h264_mf`). Executes reframe + progress bar + animated ASS subtitles in a single pass.
- **Persistent Caching**: Disk-backed cache for transcripts and word-level timestamps (`core/cache.py`).
- **Real-Time Streaming**: Server-Sent Events (SSE) stream progress and millisecond stopwatch metrics (`pipeline/job_manager.py`).

### 2. Multi-Factor AI Clip Selection
- **Multi-Factor Scoring**: Evaluates Hook Strength, Emotional Peaks, Thought Completeness, Pacing (ideal 130–185 WPM), and Retention Potential.
- **Top Candidates with Reasons**: Returns ranked candidates with virality scores (0–100) and actionable reasons.
- **Sentence-Boundary Snapping**: Cuts strictly on sentence terminals (`.!?`), eliminating abrupt mid-word cuts.
- **Interactive Studio Curation**: Preview, drag-to-trim start/end sliders, and duration adjustments.

### 3. Transformative Production & Monetization
- **9:16 Vertical Smart Reframe**: Transforms 16:9 to 1080x1920 with centered framing.
- **Word-by-Word Animated Captions**: Multiple presets (MrBeast Yellow, Hormozi Cyan, Neon Red, Minimal Clean) positioned at the bottom safe zone (`Alignment=2`, `MarginV=190`).
- **Dynamic Progress Bar**: Top-aligned animated progress bar (`drawbox`).
- **Multi-Track Audio Mixing**: Original audio, background music with volume ducking, and commentary overlay.

### 4. Rights & Safety Guardrails
- **Pre-Processing Declaration**: Enforces user rights declaration (Ownership, Commercial License, Creative Commons, or Fair Use).
- **License Detection**: Probes YouTube metadata for Creative Commons (CC-BY) vs Standard YouTube License.
- **Content-ID Claim Risk**: Proactively warns against major record labels (VEVO, Warner, Sony, Universal) and music video content.
- **Auto-Attribution Generator**: Automatically generates compliant source attribution text.

### 5. Publishing & Growth Hub
- **A/B Title Variants**: 3 curiosity-gap and high-CTR title variations.
- **SEO Descriptions & Tags**: Generates #Shorts, #Viral, and topic tags.
- **Weekly Schedule Planner**: Recommends optimal posting windows (12:00 PM lunch peak, 5:30 PM commute peak, 8:30 PM evening peak).

### 6. UI/UX Polish
- **One-Screen Workflow**: Dark-mode glassmorphism interface with smooth micro-animations.
- **Interactive 9:16 Video Player**: Instant playback of rendered shorts with download buttons.
- **Live Stage Timers**: Visual stopwatch showing timings per pipeline stage.

### 7. Engineering Quality
- **Typed Modular Architecture**: Clean separation into `core/`, `pipeline/`, and `tests/`.
- **Automated Integration Tests**: `tests/test_pipeline.py` testing all modules.

---

## 🛠️ Getting Started

### 1. Prerequisites
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) in your system PATH.

### 2. Quick Setup
```bash
# Clone repository
git clone https://github.com/MiriyalaMonisahith/youtube_video_audio_downloader.git
cd youtube_video_audio_downloader

# Virtual Environment
python -m venv venv
.\venv\Scripts\activate     # Windows
source venv/bin/activate    # Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Studio
```bash
python web_server.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🧪 Testing & Verification

Run the integration test suite:
```bash
python -m unittest tests/test_pipeline.py
```

Test the live API health and hardware acceleration probe:
```bash
curl http://localhost:5000/api/health
```
