import sys
# Python 3.14+ compatibility workaround for google.protobuf C-extension
if sys.version_info >= (3, 14):
    sys.modules.setdefault('google._upb._message', None)

import streamlit as st
import os
import glob
from downloader_engine import get_video_info, download_media, OUTPUT_DIR, SHORTS_DIR
from generate_clips import main_pipeline

# Configure Streamlit Page
st.set_page_config(
    page_title="Vortex Studio | Pro Video Downloader & AI Shorts",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
    }

    .stApp {
        background-color: #07090e;
        color: #f8fafc;
    }

    /* Glass Cards */
    .stCard {
        background: rgba(18, 24, 38, 0.7);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 20px;
    }

    /* Neon Pill Badges */
    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        background: linear-gradient(135deg, #ec4899, #6366f1);
        color: white;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }

    /* Primary Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #ec4899) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        padding: 12px 28px !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(236, 72, 153, 0.45) !important;
    }

    /* Download Buttons */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981, #059669) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <span class="badge-pill">NEXT-GEN MEDIA SUITE</span>
    <h1 style="font-size: 3rem; margin-bottom: 5px; background: linear-gradient(135deg, #a5b4fc, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        ⚡ VORTEX STUDIO
    </h1>
    <p style="color: #94a3b8; font-size: 1.1rem;">
        High-Quality Video Downloader (4K to 360p) • Lossless Audio Extractor • AI Viral Shorts Generator
    </p>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_download, tab_shorts, tab_vault = st.tabs([
    "🎬 Video & Audio Downloader",
    "🔥 AI Shorts Generator",
    "📁 Media Vault & Library"
])

# ---------------------------------------------------------
# TAB 1: VIDEO & AUDIO DOWNLOADER (WITH QUALITY & BITRATE)
# ---------------------------------------------------------
with tab_download:
    st.markdown("### 📥 Download YouTube Video or Audio")
    st.write("Fetch any video, select exact quality resolutions (4K, 1080p, 720p, etc.) or extract audio at 320 kbps.")

    url_input = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...", key="dl_url_input")

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        fetch_btn = st.button("🔍 Inspect Video", key="btn_inspect")

    if url_input and (fetch_btn or st.session_state.get("cached_url") == url_input):
        with st.spinner("Fetching stream info and available resolutions..."):
            try:
                info = get_video_info(url_input)
                st.session_state["cached_url"] = url_input
                st.session_state["current_info"] = info
            except Exception as e:
                st.error(f"Error fetching video details: {e}")
                info = None

        if info:
            st.divider()
            # Video Metadata Card
            col_thumb, col_meta = st.columns([1, 2])
            with col_thumb:
                st.image(info["thumbnail"], use_container_width=True)
                st.caption(f"⏱️ Duration: **{info['duration_formatted']}**")

            with col_meta:
                st.subheader(info["title"])
                st.write(f"👤 **Channel:** {info['uploader']} | 👁️ **Views:** {info['views']}")
                if info["description"]:
                    st.write(info["description"])

            st.divider()
            # Format and Quality Options
            st.markdown("#### ⚙️ Download Options")
            dl_mode = st.radio("Choose Media Type:", ["🎥 Video (with Quality Control)", "🎵 Audio Only (MP3 / Lossless)"], horizontal=True)

            if "Video" in dl_mode:
                col_res, col_fmt = st.columns([2, 1])
                with col_res:
                    res_choices = {f"{r['label']} - {r['tag']} ({r['size_formatted']})": r["height"] for r in info["resolutions"]}
                    selected_res_label = st.selectbox("Select Video Resolution:", list(res_choices.keys()))
                    selected_height = res_choices[selected_res_label]

                with col_fmt:
                    selected_video_fmt = st.selectbox("Video Container:", ["mp4", "mkv", "webm"])

                if st.button("🚀 Start Video Download", key="btn_download_video"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def update_progress(p):
                        pct = int(p.get("percent", 0))
                        progress_bar.progress(min(100, max(0, pct)))
                        status_text.text(f"Status: {p.get('status')} | {p.get('speed_str', '')} | ETA: {p.get('eta_str', '')}")

                    with st.spinner("Downloading and muxing video streams..."):
                        try:
                            result = download_media(
                                url=url_input,
                                media_type="video",
                                resolution=selected_height,
                                video_format=selected_video_fmt,
                                progress_callback=update_progress
                            )
                            st.success(f"✅ Video Downloaded Successfully! ({result['size_str']})")
                            st.video(result["filepath"])

                            with open(result["filepath"], "rb") as f:
                                st.download_button(
                                    label="💾 Save Video File",
                                    data=f.read(),
                                    file_name=result["filename"],
                                    mime=f"video/{selected_video_fmt}"
                                )
                        except Exception as e:
                            st.error(f"Download failed: {e}")

            else:
                # Audio extraction
                col_afmt, col_abit = st.columns([1, 1])
                with col_afmt:
                    selected_afmt = st.selectbox("Audio Format:", ["mp3", "m4a", "wav", "flac", "opus"])
                with col_abit:
                    selected_abit = st.selectbox("Audio Bitrate / Quality:", ["320k", "256k", "192k", "128k", "best"])

                if st.button("🎵 Extract Audio Track", key="btn_download_audio"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def update_audio_progress(p):
                        pct = int(p.get("percent", 0))
                        progress_bar.progress(min(100, max(0, pct)))
                        status_text.text(f"Extracting: {pct}% | {p.get('speed_str', '')}")

                    with st.spinner("Extracting and encoding audio stream..."):
                        try:
                            result = download_media(
                                url=url_input,
                                media_type="audio",
                                audio_format=selected_afmt,
                                audio_quality=selected_abit,
                                progress_callback=update_audio_progress
                            )
                            st.success(f"✅ Audio Extracted Successfully! ({result['size_str']})")
                            st.audio(result["filepath"])

                            with open(result["filepath"], "rb") as f:
                                st.download_button(
                                    label=f"💾 Save {selected_afmt.upper()} File",
                                    data=f.read(),
                                    file_name=result["filename"],
                                    mime=f"audio/{selected_afmt}"
                                )
                        except Exception as e:
                            st.error(f"Audio extraction failed: {e}")


# ---------------------------------------------------------
# TAB 2: AI SHORTS GENERATOR
# ---------------------------------------------------------
with tab_shorts:
    st.markdown("### 🔥 AI Viral Shorts Generator")
    st.write("Automatically extracts speech with Whisper, discovers viral moments, cuts 9:16 vertical shorts, and burns animated subtitles!")

    shorts_url = st.text_input("Enter YouTube Video URL for Shorts:", placeholder="https://www.youtube.com/watch?v=...", key="shorts_url_in")

    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        num_shorts = st.slider("Number of Shorts to generate:", min_value=1, max_value=5, value=3)
    with col_s2:
        caption_style = st.selectbox("Caption Style:", ["neon_yellow (MrBeast Style)", "cyber_cyan (Hormozi Style)", "classic_white"], index=0)
        style_code = "neon_yellow" if "neon_yellow" in caption_style else ("cyber_cyan" if "cyber_cyan" in caption_style else "classic_white")

    if st.button("🔥 Generate AI Shorts Pack", key="btn_run_shorts"):
        if not shorts_url:
            st.error("Please enter a YouTube URL.")
        else:
            prog_bar = st.progress(0)
            status_box = st.empty()

            def on_shorts_progress(p):
                step = p.get("step", 1)
                total = p.get("total_steps", 6)
                pct = p.get("percent", 10)
                prog_bar.progress(pct)
                status_box.markdown(f"**Step [{step}/{total}]**: {p.get('message', 'Processing...')}")

            with st.spinner("AI Shorts Pipeline running..."):
                try:
                    res = main_pipeline(
                        source_url_or_file=shorts_url,
                        num_clips=num_shorts,
                        caption_style=style_code,
                        progress_callback=on_shorts_progress
                    )
                    st.success("🎉 AI Shorts Pack Created Successfully!")
                    st.markdown(f"#### 🏷️ Viral Title: **{res['title']}**")
                    st.code(res["hashtags"], language="markdown")

                    # Download complete zip
                    if os.path.exists(res["zip_path"]):
                        with open(res["zip_path"], "rb") as zf:
                            st.download_button(
                                "📦 Download All Shorts (.ZIP)",
                                data=zf.read(),
                                file_name="shorts_pack.zip",
                                mime="application/zip"
                            )

                    # Preview Clips
                    st.markdown("### 📱 Generated Vertical Shorts (9:16)")
                    clip_cols = st.columns(len(res["clips"]))
                    for idx, clip in enumerate(res["clips"]):
                        with clip_cols[idx]:
                            st.caption(f"🔥 Score: {clip['score']}/100 • {clip['duration']}")
                            st.video(clip["filepath"])
                            with open(clip["filepath"], "rb") as vf:
                                st.download_button(
                                    f"⬇️ Download Short #{clip['clip_id']}",
                                    data=vf.read(),
                                    file_name=clip["filename"],
                                    mime="video/mp4",
                                    key=f"dl_clip_{idx}"
                                )
                except Exception as e:
                    st.error(f"Shorts generation error: {e}")


# ---------------------------------------------------------
# TAB 3: MEDIA VAULT & LIBRARY
# ---------------------------------------------------------
with tab_vault:
    st.markdown("### 📁 Media Vault")
    st.write("Browse all previously downloaded videos, audios, and AI Shorts.")

    col_v1, col_v2 = st.columns([1, 1])

    with col_v1:
        st.markdown("#### 🎬 Full Downloads")
        downloaded_files = glob.glob(f"{OUTPUT_DIR}/*.*")
        if not downloaded_files:
            st.info("No downloads yet.")
        else:
            for fpath in sorted(downloaded_files, reverse=True)[:10]:
                fname = os.path.basename(fpath)
                fsize = f"{os.path.getsize(fpath) / (1024*1024):.1f} MB"
                st.write(f"📄 **{fname}** ({fsize})")
                if fname.endswith((".mp4", ".mkv", ".webm")):
                    st.video(fpath)
                elif fname.endswith((".mp3", ".m4a", ".wav")):
                    st.audio(fpath)
                st.divider()

    with col_v2:
        st.markdown("#### 🔥 AI Shorts Packages")
        if os.path.exists(SHORTS_DIR):
            job_dirs = sorted([d for d in os.listdir(SHORTS_DIR) if os.path.isdir(os.path.join(SHORTS_DIR, d))], reverse=True)
            if not job_dirs:
                st.info("No shorts packages yet.")
            else:
                for jdir in job_dirs[:5]:
                    jpath = os.path.join(SHORTS_DIR, jdir)
                    zip_f = os.path.join(jpath, "shorts.zip")
                    st.write(f"📁 **Collection {jdir}**")
                    if os.path.exists(zip_f):
                        with open(zip_f, "rb") as zf:
                            st.download_button(f"📦 Download Package {jdir}", data=zf.read(), file_name=f"shorts_{jdir}.zip", key=f"v_zip_{jdir}")
                    st.divider()