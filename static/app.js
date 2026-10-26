/**
 * VORTEX STUDIO - CLIENT JAVASCRIPT
 */

document.addEventListener('DOMContentLoaded', () => {
  // -----------------------------------------
  // State
  // -----------------------------------------
  let currentVideoInfo = null;
  let selectedMode = 'video'; // 'video' | 'audio'
  let selectedResolution = 1080;
  let selectedVideoFormat = 'mp4';
  let selectedAudioFormat = 'mp3';
  let selectedAudioQuality = '320k';
  let selectedShortsNumClips = 3;
  let selectedCaptionStyle = 'neon_yellow';

  // -----------------------------------------
  // DOM Elements
  // -----------------------------------------
  // Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  // Downloader tab elements
  const videoUrlInput = document.getElementById('video-url-input');
  const btnClearUrl = document.getElementById('btn-clear-url');
  const btnInspectUrl = document.getElementById('btn-inspect-url');
  const videoDetailsCard = document.getElementById('video-details-card');

  // Meta Elements
  const metaThumb = document.getElementById('meta-thumb');
  const metaDuration = document.getElementById('meta-duration');
  const metaTitle = document.getElementById('meta-title');
  const metaUploader = document.getElementById('meta-uploader');
  const metaViews = document.getElementById('meta-views');
  const metaDesc = document.getElementById('meta-desc');

  // Mode buttons & Panels
  const modeVideoBtn = document.getElementById('mode-video-btn');
  const modeAudioBtn = document.getElementById('mode-audio-btn');
  const videoOptionsPanel = document.getElementById('video-options-panel');
  const audioOptionsPanel = document.getElementById('audio-options-panel');
  const resolutionsContainer = document.getElementById('resolutions-container');
  const btnStartDownload = document.getElementById('btn-start-download');
  const btnDownloadLabel = document.getElementById('btn-download-label');

  // Progress & Completion Elements
  const dlProgressContainer = document.getElementById('download-progress-container');
  const dlStatusText = document.getElementById('dl-status-text');
  const dlSpeed = document.getElementById('dl-speed');
  const dlEta = document.getElementById('dl-eta');
  const dlSize = document.getElementById('dl-size');
  const dlProgressBar = document.getElementById('dl-progress-bar');
  const dlCompleteCard = document.getElementById('download-complete-card');
  const dlResultTitle = document.getElementById('dl-result-title');
  const dlPlayerContainer = document.getElementById('dl-player-container');
  const btnSaveFile = document.getElementById('btn-save-file');
  const btnDownloadAnother = document.getElementById('btn-download-another');

  // Shorts Tab elements
  const shortsUrlInput = document.getElementById('shorts-url-input');
  const btnGenerateShorts = document.getElementById('btn-generate-shorts');
  const shortsPipelineCard = document.getElementById('shorts-pipeline-card');
  const shortsPercentText = document.getElementById('shorts-percent-text');
  const shortsCurrentMsg = document.getElementById('shorts-current-msg');
  const shortsShowcaseCard = document.getElementById('shorts-showcase-card');
  const showcaseTitle = document.getElementById('showcase-title');
  const showcaseHashtags = document.getElementById('showcase-hashtags');
  const btnCopyHashtags = document.getElementById('btn-copy-hashtags');
  const btnDownloadZip = document.getElementById('btn-download-zip');
  const shortsClipsGrid = document.getElementById('shorts-clips-grid');

  // Media Vault elements
  const btnRefreshVault = document.getElementById('btn-refresh-vault');
  const vaultDownloadsList = document.getElementById('vault-downloads-list');
  const vaultShortsList = document.getElementById('vault-shorts-list');
  const vaultCountBadge = document.getElementById('vault-count');

  // Toast
  const toastEl = document.getElementById('app-toast');
  const toastText = document.getElementById('toast-text');

  // -----------------------------------------
  // Utility Functions
  // -----------------------------------------
  function showToast(message, duration = 3500) {
    toastText.textContent = message;
    toastEl.classList.remove('hidden');
    setTimeout(() => {
      toastEl.classList.add('hidden');
    }, duration);
  }

  // -----------------------------------------
  // Tab Switching
  // -----------------------------------------
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.dataset.tab;
      document.getElementById(targetId).classList.add('active');

      if (targetId === 'tab-library') {
        loadMediaVault();
      }
    });
  });

  // -----------------------------------------
  // Input Handling (Clear / Paste)
  // -----------------------------------------
  videoUrlInput.addEventListener('input', () => {
    if (videoUrlInput.value.trim().length > 0) {
      btnClearUrl.classList.add('show');
    } else {
      btnClearUrl.classList.remove('show');
    }
  });

  btnClearUrl.addEventListener('click', () => {
    videoUrlInput.value = '';
    btnClearUrl.classList.remove('show');
    videoDetailsCard.classList.add('hidden');
    videoUrlInput.focus();
  });

  // -----------------------------------------
  // Fetch Video Info (Inspect)
  // -----------------------------------------
  btnInspectUrl.addEventListener('click', async () => {
    const url = videoUrlInput.value.trim();
    if (!url) {
      showToast('⚠️ Please enter a YouTube URL');
      videoUrlInput.focus();
      return;
    }

    btnInspectUrl.classList.add('loading');
    videoDetailsCard.classList.add('hidden');
    dlCompleteCard.classList.add('hidden');
    dlProgressContainer.classList.add('hidden');

    try {
      const response = await fetch('/api/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch video details.');
      }

      currentVideoInfo = data.data;
      renderVideoDetails(currentVideoInfo);
      videoDetailsCard.classList.remove('hidden');
      videoDetailsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      showToast('✅ Video details fetched successfully!');
    } catch (err) {
      showToast(`❌ Error: ${err.message}`);
    } finally {
      btnInspectUrl.classList.remove('loading');
    }
  });

  // Also pre-populate shorts URL input if typed
  videoUrlInput.addEventListener('change', () => {
    if (!shortsUrlInput.value) {
      shortsUrlInput.value = videoUrlInput.value;
    }
  });

  // -----------------------------------------
  // Render Video Details & Resolutions
  // -----------------------------------------
  function renderVideoDetails(info) {
    metaThumb.src = info.thumbnail || '';
    metaDuration.textContent = info.duration_formatted;
    metaTitle.textContent = info.title;
    metaUploader.textContent = info.uploader;
    metaViews.textContent = `${info.views} views`;
    metaDesc.textContent = info.description || 'No description provided.';

    // Populate Resolutions
    resolutionsContainer.innerHTML = '';
    const resolutions = info.resolutions || [];

    resolutions.forEach((res, index) => {
      const card = document.createElement('div');
      card.className = `res-card ${index === 0 ? 'active' : ''}`;
      card.dataset.height = res.height;

      card.innerHTML = `
        <span class="res-badge">${res.tag}</span>
        <div class="res-label">${res.label}</div>
        <div class="res-specs">
          <span>${res.fps ? `${res.fps} FPS` : '60 FPS'}</span>
          <span>${res.size_formatted}</span>
        </div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('.res-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        selectedResolution = parseInt(res.height);
        updateDownloadActionLabel();
      });

      resolutionsContainer.appendChild(card);
    });

    if (resolutions.length > 0) {
      selectedResolution = resolutions[0].height;
    }

    updateDownloadActionLabel();
  }

  // -----------------------------------------
  // Mode Switcher (Video vs Audio)
  // -----------------------------------------
  modeVideoBtn.addEventListener('click', () => {
    selectedMode = 'video';
    modeVideoBtn.classList.add('active');
    modeAudioBtn.classList.remove('active');
    videoOptionsPanel.classList.remove('hidden');
    audioOptionsPanel.classList.add('hidden');
    updateDownloadActionLabel();
  });

  modeAudioBtn.addEventListener('click', () => {
    selectedMode = 'audio';
    modeAudioBtn.classList.add('active');
    modeVideoBtn.classList.remove('active');
    audioOptionsPanel.classList.remove('hidden');
    videoOptionsPanel.classList.add('hidden');
    updateDownloadActionLabel();
  });

  // Video Format Chips
  document.querySelectorAll('#video-formats .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#video-formats .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedVideoFormat = chip.dataset.val;
      updateDownloadActionLabel();
    });
  });

  // Audio Format Chips
  document.querySelectorAll('#audio-formats .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#audio-formats .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedAudioFormat = chip.dataset.val;

      // Bitrate options only make sense for lossy formats like MP3
      const bitrateRow = document.getElementById('audio-bitrate-row');
      if (['wav', 'flac'].includes(selectedAudioFormat)) {
        bitrateRow.style.opacity = '0.4';
        bitrateRow.style.pointerEvents = 'none';
      } else {
        bitrateRow.style.opacity = '1';
        bitrateRow.style.pointerEvents = 'auto';
      }

      updateDownloadActionLabel();
    });
  });

  // Audio Bitrate Chips
  document.querySelectorAll('#audio-bitrates .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#audio-bitrates .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedAudioQuality = chip.dataset.val;
      updateDownloadActionLabel();
    });
  });

  function updateDownloadActionLabel() {
    if (selectedMode === 'video') {
      btnDownloadLabel.textContent = `Download ${selectedResolution}p (${selectedVideoFormat.toUpperCase()}) Video`;
    } else {
      const bitStr = ['wav', 'flac'].includes(selectedAudioFormat) ? 'Lossless' : selectedAudioQuality;
      btnDownloadLabel.textContent = `Extract ${selectedAudioFormat.toUpperCase()} Audio (${bitStr})`;
    }
  }

  // -----------------------------------------
  // Execute Download & Poll Progress
  // -----------------------------------------
  btnStartDownload.addEventListener('click', async () => {
    const url = videoUrlInput.value.trim();
    if (!url) {
      showToast('⚠️ Please enter a URL first.');
      return;
    }

    btnStartDownload.disabled = true;
    dlCompleteCard.classList.add('hidden');
    dlProgressContainer.classList.remove('hidden');
    dlProgressBar.style.width = '0%';
    dlStatusText.textContent = 'Initializing...';
    dlSpeed.textContent = '- MB/s';
    dlEta.textContent = 'ETA: -';
    dlSize.textContent = '0 / 0 MB';

    try {
      const payload = {
        url,
        type: selectedMode,
        resolution: selectedResolution,
        video_format: selectedVideoFormat,
        audio_format: selectedAudioFormat,
        audio_quality: selectedAudioQuality
      };

      const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to start download.');
      }

      const jobId = data.job_id;
      pollDownloadJob(jobId);
    } catch (err) {
      showToast(`❌ Download Error: ${err.message}`);
      btnStartDownload.disabled = false;
      dlProgressContainer.classList.add('hidden');
    }
  });

  function pollDownloadJob(jobId) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/job/${jobId}`);
        const data = await res.json();

        if (!data.success || !data.job) return;

        const job = data.job;
        if (job.status === 'downloading' || job.status === 'processing') {
          const pct = Math.max(5, Math.min(99, job.percent || 10));
          dlProgressBar.style.width = `${pct}%`;
          dlStatusText.textContent = job.status === 'processing' ? 'Merging Video & Audio...' : 'Downloading streams...';
          dlSpeed.textContent = job.speed_str || '-';
          dlEta.textContent = `ETA: ${job.eta_str || '-'}`;
          dlSize.textContent = `${job.downloaded_str || '0 MB'} / ${job.total_str || '0 MB'}`;
        } else if (job.status === 'completed') {
          clearInterval(interval);
          dlProgressBar.style.width = '100%';
          dlStatusText.textContent = 'Completed!';
          btnStartDownload.disabled = false;

          setTimeout(() => {
            renderDownloadResult(job.result);
          }, 600);
        } else if (job.status === 'failed') {
          clearInterval(interval);
          btnStartDownload.disabled = false;
          showToast(`❌ Download Failed: ${job.error || 'Unknown error'}`);
          dlStatusText.textContent = 'Failed';
        }
      } catch (e) {
        console.error('Polling error', e);
      }
    }, 1000);
  }

  function renderDownloadResult(result) {
    dlProgressContainer.classList.add('hidden');
    dlCompleteCard.classList.remove('hidden');

    dlResultTitle.textContent = `${result.title} • ${result.size_str}`;
    const mediaUrl = `/media/downloads/${result.filename}`;
    const directDlUrl = `/download_media/downloads/${result.filename}`;

    btnSaveFile.href = directDlUrl;
    btnSaveFile.setAttribute('download', result.filename);

    dlPlayerContainer.innerHTML = '';
    if (result.media_type === 'audio') {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.src = mediaUrl;
      dlPlayerContainer.appendChild(audio);
    } else {
      const video = document.createElement('video');
      video.controls = true;
      video.playsInline = true;
      video.src = mediaUrl;
      dlPlayerContainer.appendChild(video);
    }

    dlCompleteCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    showToast('🎉 Download completed! File ready.');
  }

  btnDownloadAnother.addEventListener('click', () => {
    dlCompleteCard.classList.add('hidden');
    videoUrlInput.value = '';
    videoDetailsCard.classList.add('hidden');
    videoUrlInput.focus();
  });

  // -----------------------------------------
  // AI Shorts Generator Logic
  // -----------------------------------------
  // Shorts Clip count selector
  document.querySelectorAll('#shorts-num-clips .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#shorts-num-clips .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedShortsNumClips = parseInt(chip.dataset.val);
    });
  });

  // Shorts Caption Style selector
  document.querySelectorAll('#shorts-caption-style .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('#shorts-caption-style .chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedCaptionStyle = chip.dataset.val;
    });
  });

  btnGenerateShorts.addEventListener('click', async () => {
    const url = shortsUrlInput.value.trim() || videoUrlInput.value.trim();
    if (!url) {
      showToast('⚠️ Please enter a YouTube video URL for shorts.');
      shortsUrlInput.focus();
      return;
    }

    btnGenerateShorts.disabled = true;
    shortsShowcaseCard.classList.add('hidden');
    shortsPipelineCard.classList.remove('hidden');
    shortsPercentText.textContent = '5%';
    shortsCurrentMsg.textContent = 'Initializing AI Shorts pipeline...';

    // Reset step UI
    for (let i = 1; i <= 6; i++) {
      const stepEl = document.getElementById(`step-${i}`);
      stepEl.classList.remove('active', 'completed');
    }
    document.getElementById('step-1').classList.add('active');

    try {
      const res = await fetch('/api/shorts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          num_clips: selectedShortsNumClips,
          caption_style: selectedCaptionStyle
        })
      });
      const data = await res.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to start AI Shorts job.');
      }

      pollShortsJob(data.job_id);
    } catch (err) {
      showToast(`❌ Shorts Error: ${err.message}`);
      btnGenerateShorts.disabled = false;
      shortsPipelineCard.classList.add('hidden');
    }
  });

  function pollShortsJob(jobId) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/job/${jobId}`);
        const data = await res.json();

        if (!data.success || !data.job) return;

        const job = data.job;
        if (job.status === 'processing') {
          const step = job.step || 1;
          const pct = job.percent || 15;
          shortsPercentText.textContent = `${pct}%`;
          shortsCurrentMsg.textContent = job.message || 'Processing...';

          for (let i = 1; i <= 6; i++) {
            const stepEl = document.getElementById(`step-${i}`);
            if (i < step) {
              stepEl.classList.add('completed');
              stepEl.classList.remove('active');
            } else if (i === step) {
              stepEl.classList.add('active');
              stepEl.classList.remove('completed');
            } else {
              stepEl.classList.remove('active', 'completed');
            }
          }
        } else if (job.status === 'completed') {
          clearInterval(interval);
          shortsPercentText.textContent = '100%';
          shortsCurrentMsg.textContent = 'AI Shorts Pack Ready! 🚀';
          for (let i = 1; i <= 6; i++) {
            document.getElementById(`step-${i}`).classList.add('completed');
          }
          btnGenerateShorts.disabled = false;

          setTimeout(() => {
            renderShortsShowcase(job.result);
          }, 800);
        } else if (job.status === 'failed') {
          clearInterval(interval);
          btnGenerateShorts.disabled = false;
          showToast(`❌ AI Shorts Failed: ${job.error || 'Pipeline error'}`);
          shortsCurrentMsg.textContent = `Failed: ${job.error}`;
        }
      } catch (e) {
        console.error('Shorts polling error', e);
      }
    }, 1500);
  }

  function renderShortsShowcase(result) {
    shortsPipelineCard.classList.add('hidden');
    shortsShowcaseCard.classList.remove('hidden');

    showcaseTitle.textContent = result.title || 'AI Generated Shorts';
    showcaseHashtags.textContent = result.hashtags || '#shorts #viral #trending';
    btnDownloadZip.href = `/download_media/shorts/${result.job_id}/shorts.zip`;

    shortsClipsGrid.innerHTML = '';
    const clips = result.clips || [];

    clips.forEach(clip => {
      const card = document.createElement('div');
      card.className = 'short-card';

      const mediaUrl = `/media/shorts/${result.job_id}/${clip.filename}`;
      const downloadUrl = `/download_media/shorts/${result.job_id}/${clip.filename}`;

      card.innerHTML = `
        <div class="short-video-wrapper">
          <span class="short-score-pill">🔥 Score: ${clip.score}/100</span>
          <video src="${mediaUrl}" controls playsinline preload="metadata"></video>
        </div>
        <div class="short-info">
          <div>
            <div class="short-title">Clip #${clip.clip_id}: ${clip.reason}</div>
            <div class="short-meta-row">
              <span><i class="fa-solid fa-clock"></i> ${clip.duration}</span>
              <span>${clip.start}s - ${clip.end}s</span>
            </div>
          </div>
          <a href="${downloadUrl}" class="btn-short-download" download="${clip.filename}">
            <i class="fa-solid fa-download"></i> Save Short (MP4)
          </a>
        </div>
      `;

      shortsClipsGrid.appendChild(card);
    });

    shortsShowcaseCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    showToast('🔥 AI Shorts Generated Successfully!');
  }

  // Copy hashtags button
  btnCopyHashtags.addEventListener('click', () => {
    const text = showcaseHashtags.textContent;
    navigator.clipboard.writeText(text).then(() => {
      showToast('📋 Hashtags copied to clipboard!');
    });
  });

  // -----------------------------------------
  // Media Vault (Library)
  // -----------------------------------------
  async function loadMediaVault() {
    try {
      const res = await fetch('/api/library');
      const data = await res.json();
      if (!data.success) return;

      const downloads = data.downloads || [];
      const shortsPacks = data.shorts || [];

      // Update badge count
      vaultCountBadge.textContent = downloads.length + shortsPacks.length;

      // Render Downloads
      vaultDownloadsList.innerHTML = '';
      if (downloads.length === 0) {
        vaultDownloadsList.innerHTML = '<div class="empty-state">No downloaded media yet.</div>';
      } else {
        downloads.forEach(item => {
          const row = document.createElement('div');
          row.className = 'file-row';
          const icon = item.type === 'video' ? 'fa-solid fa-file-video' : 'fa-solid fa-file-audio';

          row.innerHTML = `
            <div class="file-info">
              <i class="${icon} file-icon"></i>
              <div>
                <div class="file-name" title="${item.filename}">${item.filename}</div>
                <div class="file-size">${item.size} • ${item.modified}</div>
              </div>
            </div>
            <div class="file-actions">
              <a href="${item.url}" target="_blank" class="btn-icon" title="Preview / Play">
                <i class="fa-solid fa-play"></i>
              </a>
              <a href="${item.download_url}" class="btn-icon" download title="Download">
                <i class="fa-solid fa-download"></i>
              </a>
            </div>
          `;
          vaultDownloadsList.appendChild(row);
        });
      }

      // Render Shorts Packs
      vaultShortsList.innerHTML = '';
      if (shortsPacks.length === 0) {
        vaultShortsList.innerHTML = '<div class="empty-state">No AI Shorts packages created yet.</div>';
      } else {
        shortsPacks.forEach(pack => {
          const row = document.createElement('div');
          row.className = 'file-row';

          row.innerHTML = `
            <div class="file-info">
              <i class="fa-solid fa-fire file-icon" style="color: var(--accent-pink);"></i>
              <div>
                <div class="file-name">${pack.title}</div>
                <div class="file-size">${pack.clips.length} Clips • Job: ${pack.job_id}</div>
              </div>
            </div>
            <div class="file-actions">
              ${pack.zip_url ? `
                <a href="${pack.zip_url}" class="btn-icon" download title="Download Full ZIP Bundle">
                  <i class="fa-solid fa-file-zipper"></i>
                </a>
              ` : ''}
            </div>
          `;
          vaultShortsList.appendChild(row);
        });
      }
    } catch (e) {
      console.error('Failed to load library', e);
    }
  }

  btnRefreshVault.addEventListener('click', () => {
    loadMediaVault();
    showToast('🔄 Media Vault Refreshed');
  });

  // Initial Vault count load
  loadMediaVault();
});
