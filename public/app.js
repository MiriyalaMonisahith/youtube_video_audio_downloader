/**
 * VORTEX STUDIO PRO - CLIENT APPLICATION LOGIC
 * Full 7-Pillar Implementation:
 * 1. Speed profiling & hardware status
 * 2. Multi-factor AI clip scoring & curation
 * 3. Studio customizer (ASS styles, drag-to-trim, progress bar, watermark)
 * 4. Rights & safety verification
 * 5. Publishing hub (A/B titles, hashtags, calendar)
 * 6. Real-time SSE progress streaming & 9:16 player
 */

document.addEventListener('DOMContentLoaded', () => {
  // -----------------------------------------
  // Global State
  // -----------------------------------------
  let currentAnalysis = null;
  let selectedCandidate = null;
  let selectedStyle = 'mrbeast';
  let activeEventSource = null;

  // Traditional Downloader State
  let currentVideoInfo = null;
  let selectedMode = 'video';
  let selectedResolution = 1080;
  let selectedVideoFormat = 'mp4';
  let selectedAudioFormat = 'mp3';
  let selectedAudioQuality = '320k';

  // -----------------------------------------
  // DOM Elements
  // -----------------------------------------
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  const toastEl = document.getElementById('app-toast');
  const toastText = document.getElementById('toast-text');

  // Hardware status pills
  const hwName = document.getElementById('hw-name');

  // Shorts Studio Elements
  const shortsUrlInput = document.getElementById('shorts-url-input');
  const btnClearShortsUrl = document.getElementById('btn-clear-shorts-url');
  const btnAnalyzeVideo = document.getElementById('btn-analyze-video');
  const analyzeSpinner = document.getElementById('analyze-spinner');

  // Timings
  const timingsBanner = document.getElementById('timings-banner');
  const tDl = document.getElementById('t-dl');
  const tTr = document.getElementById('t-tr');
  const tSel = document.getElementById('t-sel');
  const tRnd = document.getElementById('t-rnd');
  const tTotal = document.getElementById('t-total');

  // Analysis Meta
  const analysisMetaCard = document.getElementById('analysis-meta-card');
  const analysisThumb = document.getElementById('analysis-thumb');
  const analysisTitle = document.getElementById('analysis-title');
  const analysisChannel = document.getElementById('analysis-channel');
  const analysisDuration = document.getElementById('analysis-duration');
  const rightsBadge = document.getElementById('rights-badge');
  const rightsMsg = document.getElementById('rights-msg');

  // Candidates & Customizer
  const clipsCuratorCard = document.getElementById('clips-curator-card');
  const candidatesGrid = document.getElementById('candidates-grid');
  const selectedClipLabel = document.getElementById('selected-clip-label');
  const sliderStart = document.getElementById('slider-start');
  const sliderEnd = document.getElementById('slider-end');
  const lblStartTime = document.getElementById('lbl-start-time');
  const lblEndTime = document.getElementById('lbl-end-time');
  const lblDuration = document.getElementById('lbl-duration');
  const styleCards = document.querySelectorAll('.style-card');
  const chkProgressBar = document.getElementById('chk-progress-bar');
  const inputWatermark = document.getElementById('input-watermark');
  const btnRenderShort = document.getElementById('btn-render-short');

  // Rendering Progress & Showcase
  const renderProgressCard = document.getElementById('render-progress-card');
  const renderStatusMsg = document.getElementById('render-status-msg');
  const renderPct = document.getElementById('render-pct');
  const renderProgressFill = document.getElementById('render-progress-fill');

  const renderedShowcaseCard = document.getElementById('rendered-showcase-card');
  const renderStatTime = document.getElementById('render-stat-time');
  const renderStatSize = document.getElementById('render-stat-size');
  const shortVideoPlayer = document.getElementById('short-video-player');
  const btnDownloadShort = document.getElementById('btn-download-short');

  // Publishing Hub
  const abTitlesList = document.getElementById('ab-titles-list');
  const pubDescription = document.getElementById('pub-description');
  const btnCopyDesc = document.getElementById('btn-copy-desc');

  // Downloader Tab Elements
  const videoUrlInput = document.getElementById('video-url-input');
  const btnClearUrl = document.getElementById('btn-clear-url');
  const btnInspectUrl = document.getElementById('btn-inspect-url');
  const inspectSpinner = document.getElementById('inspect-spinner');
  const videoDetailsCard = document.getElementById('video-details-card');
  const metaThumb = document.getElementById('meta-thumb');
  const metaDuration = document.getElementById('meta-duration');
  const metaTitle = document.getElementById('meta-title');
  const metaUploader = document.getElementById('meta-uploader');
  const metaViews = document.getElementById('meta-views');
  const metaDesc = document.getElementById('meta-desc');
  const modeVideoBtn = document.getElementById('mode-video-btn');
  const modeAudioBtn = document.getElementById('mode-audio-btn');
  const videoOptionsPanel = document.getElementById('video-options-panel');
  const audioOptionsPanel = document.getElementById('audio-options-panel');
  const resolutionsContainer = document.getElementById('resolutions-container');
  const btnStartDownload = document.getElementById('btn-start-download');
  const dlProgressContainer = document.getElementById('download-progress-container');
  const dlStatusText = document.getElementById('dl-status-text');
  const dlSpeed = document.getElementById('dl-speed');
  const dlSize = document.getElementById('dl-size');
  const dlProgressBar = document.getElementById('dl-progress-bar');

  // Media Vault Elements
  const btnRefreshVault = document.getElementById('btn-refresh-vault');
  const vaultDownloadsList = document.getElementById('vault-downloads-list');
  const vaultShortsList = document.getElementById('vault-shorts-list');
  const vaultCountBadge = document.getElementById('vault-count');

  // -----------------------------------------
  // Helper Utilities
  // -----------------------------------------
  function showToast(message, duration = 3500) {
    if (!toastEl) return;
    toastText.textContent = message;
    toastEl.classList.remove('hidden');
    setTimeout(() => toastEl.classList.add('hidden'), duration);
  }

  function formatSec(seconds) {
    const s = Math.floor(seconds);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}:${rem.toString().padStart(2, '0')}`;
  }

  // -----------------------------------------
  // Hardware Acceleration Status Check
  // -----------------------------------------
  async function checkHardwareStatus() {
    try {
      const res = await fetch('/api/hardware-status');
      const data = await res.json();
      if (data.success && data.hardware) {
        const hw = data.hardware;
        hwName.textContent = `${hw.name} (${hw.encoder})`;
      }
    } catch (e) {
      hwName.textContent = "CPU Accelerated";
    }
  }
  checkHardwareStatus();

  // -----------------------------------------
  // Tab Switching
  // -----------------------------------------
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetTab = document.getElementById(btn.getAttribute('data-tab'));
      if (targetTab) targetTab.classList.add('active');

      if (btn.getAttribute('data-tab') === 'tab-library') {
        loadMediaVault();
      }
    });
  });

  if (btnClearShortsUrl) {
    btnClearShortsUrl.addEventListener('click', () => {
      shortsUrlInput.value = '';
      shortsUrlInput.focus();
    });
  }

  // -----------------------------------------
  // PILLAR 1 & 2: Fast AI Scan & Clip Scoring
  // -----------------------------------------
  btnAnalyzeVideo.addEventListener('click', async () => {
    const url = shortsUrlInput.value.trim();
    if (!url) {
      showToast('Please paste a YouTube video URL');
      shortsUrlInput.focus();
      return;
    }

    // Get selected rights declaration
    const rightsRadio = document.querySelector('input[name="rights-declaration"]:checked');
    const rightsValue = rightsRadio ? rightsRadio.value : 'own';

    // UI Loading state
    btnAnalyzeVideo.disabled = true;
    analyzeSpinner.style.display = 'block';
    analysisMetaCard.classList.add('hidden');
    clipsCuratorCard.classList.add('hidden');
    renderedShowcaseCard.classList.add('hidden');
    timingsBanner.classList.remove('hidden');
    tDl.textContent = 'Ingesting...';
    tTr.textContent = 'Waiting...';
    tSel.textContent = 'Waiting...';
    tRnd.textContent = '-';
    tTotal.textContent = '-';

    showToast('Starting audio-first scan & virality analysis...');

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, rights: rightsValue })
      });

      const json = await res.json();
      if (!json.success) {
        throw new Error(json.error || 'Failed to analyze video');
      }

      currentAnalysis = json.data;
      displayAnalysisResults(currentAnalysis);
      showToast('AI virality analysis complete!');
    } catch (err) {
      showToast(`Error: ${err.message}`);
    } finally {
      btnAnalyzeVideo.disabled = false;
      analyzeSpinner.style.display = 'none';
    }
  });

  function displayAnalysisResults(data) {
    // 1. Timings profiling
    const t = data.timings || {};
    tDl.textContent = `${t.download_ms || 0}ms`;
    tTr.textContent = `${t.transcribe_ms || 0}ms`;
    tSel.textContent = `${t.select_ms || 0}ms`;
    tRnd.textContent = '-';
    tTotal.textContent = `${((t.total_ms || 0) / 1000).toFixed(1)}s`;

    // 2. Video Metadata & Rights Warning
    analysisMetaCard.classList.remove('hidden');
    analysisThumb.src = data.thumbnail || '';
    analysisTitle.textContent = data.title || 'YouTube Video';
    analysisChannel.textContent = data.channel || 'Creator';
    analysisDuration.textContent = formatSec(data.duration || 0);

    const rights = data.rights || {};
    rightsBadge.innerHTML = `<i class="fa-solid fa-shield"></i> ${rights.license_detected || 'Standard'}`;
    if (rights.risk_level === 'HIGH') {
      rightsMsg.innerHTML = `<strong>⚠️ High Content-ID Risk:</strong> ${rights.risk_reasons.join(' ')}`;
      rightsMsg.parentElement.style.borderColor = '#ef4444';
      rightsMsg.parentElement.style.color = '#f87171';
    } else if (rights.risk_level === 'MEDIUM') {
      rightsMsg.innerHTML = `<strong>ℹ️ Advisory:</strong> ${rights.risk_reasons.join(' ')}`;
      rightsMsg.parentElement.style.borderColor = '#f59e0b';
      rightsMsg.parentElement.style.color = '#fbbf24';
    } else {
      rightsMsg.innerHTML = `<strong>✅ Clear:</strong> ${rights.license_detected} detected. Attribution template prepared.`;
      rightsMsg.parentElement.style.borderColor = '#10b981';
      rightsMsg.parentElement.style.color = '#34d399';
    }

    // 3. Populate Candidate Cards
    candidatesGrid.innerHTML = '';
    const candidates = data.candidates || [];

    if (candidates.length === 0) {
      candidatesGrid.innerHTML = `<div class="empty-state">No clips found matching virality criteria.</div>`;
      clipsCuratorCard.classList.remove('hidden');
      return;
    }

    candidates.forEach((cand, idx) => {
      const card = document.createElement('div');
      card.className = `candidate-card ${idx === 0 ? 'active' : ''}`;
      card.dataset.index = idx;

      card.innerHTML = `
        <div class="candidate-top-row">
          <div class="virality-badge"><i class="fa-solid fa-fire"></i> ${cand.virality_score}/100 VIRAL</div>
          <span class="clip-duration-tag">${cand.duration}s</span>
        </div>
        <div class="candidate-hook">"${cand.hook}"</div>
        <div class="candidate-reason"><i class="fa-solid fa-bolt"></i> ${cand.reason}</div>
        <div class="scores-breakdown">
          <div class="score-row">
            <span>Hook Strength</span>
            <span>${cand.scores.hook}/100</span>
          </div>
          <div class="score-bar-bg"><div class="score-bar-fill" style="width: ${cand.scores.hook}%;"></div></div>

          <div class="score-row" style="margin-top: 4px;">
            <span>Emotional Peak</span>
            <span>${cand.scores.emotion}/100</span>
          </div>
          <div class="score-bar-bg"><div class="score-bar-fill" style="width: ${cand.scores.emotion}%;"></div></div>

          <div class="score-row" style="margin-top: 4px;">
            <span>Retention Potential</span>
            <span>${cand.scores.retention}/100</span>
          </div>
          <div class="score-bar-bg"><div class="score-bar-fill" style="width: ${cand.scores.retention}%;"></div></div>
        </div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('.candidate-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        selectCandidate(cand, idx);
      });

      candidatesGrid.appendChild(card);
    });

    clipsCuratorCard.classList.remove('hidden');
    // Select first candidate by default
    selectCandidate(candidates[0], 0);
  }

  function selectCandidate(cand, idx) {
    selectedCandidate = cand;
    selectedClipLabel.textContent = `Clip #${idx + 1} (${cand.virality_score}/100 Viral)`;

    // Configure Trim Sliders
    const maxDur = currentAnalysis.duration || 600;
    sliderStart.max = maxDur;
    sliderEnd.max = maxDur;

    sliderStart.value = cand.start;
    sliderEnd.value = cand.end;

    updateTrimLabels();
  }

  // -----------------------------------------
  // Trim Range Sliders
  // -----------------------------------------
  function updateTrimLabels() {
    let startVal = parseFloat(sliderStart.value);
    let endVal = parseFloat(sliderEnd.value);

    if (endVal <= startVal + 5) {
      endVal = startVal + 5;
      sliderEnd.value = endVal;
    }

    lblStartTime.textContent = formatSec(startVal);
    lblEndTime.textContent = formatSec(endVal);
    lblDuration.textContent = `${(endVal - startVal).toFixed(1)}s`;
  }

  sliderStart.addEventListener('input', () => {
    let startVal = parseFloat(sliderStart.value);
    let endVal = parseFloat(sliderEnd.value);
    if (startVal >= endVal - 5) {
      sliderStart.value = endVal - 5;
    }
    updateTrimLabels();
  });

  sliderEnd.addEventListener('input', () => {
    let startVal = parseFloat(sliderStart.value);
    let endVal = parseFloat(sliderEnd.value);
    if (endVal <= startVal + 5) {
      sliderEnd.value = startVal + 5;
    }
    updateTrimLabels();
  });

  // Style preset buttons
  styleCards.forEach(card => {
    card.addEventListener('click', () => {
      styleCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      selectedStyle = card.getAttribute('data-style');
    });
  });

  // -----------------------------------------
  // PILLAR 1, 3 & 6: High-Speed Render & SSE
  // -----------------------------------------
  btnRenderShort.addEventListener('click', async () => {
    if (!currentAnalysis || !selectedCandidate) {
      showToast('Please analyze a video and pick a clip first');
      return;
    }

    const url = shortsUrlInput.value.trim();
    const startSec = parseFloat(sliderStart.value);
    const endSec = parseFloat(sliderEnd.value);
    const watermarkText = inputWatermark.value.trim() || null;
    const progressBar = chkProgressBar.checked;

    btnRenderShort.disabled = true;
    renderProgressCard.classList.remove('hidden');
    renderedShowcaseCard.classList.add('hidden');
    renderProgressFill.style.width = '5%';
    renderPct.textContent = '5%';
    renderStatusMsg.textContent = 'Submitting render job to GPU worker...';

    showToast('GPU single-pass render started...');

    try {
      const res = await fetch('/api/render-clip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          start_sec: startSec,
          end_sec: endSec,
          clip_text: selectedCandidate.text,
          video_id: currentAnalysis.video_id,
          video_title: currentAnalysis.title,
          style_name: selectedStyle,
          progress_bar: progressBar,
          watermark: watermarkText
        })
      });

      const json = await res.json();
      if (!json.success) {
        throw new Error(json.error || 'Failed to start render');
      }

      const jobId = json.job_id;
      listenToRenderProgress(jobId);
    } catch (err) {
      showToast(`Error: ${err.message}`);
      btnRenderShort.disabled = false;
      renderProgressCard.classList.add('hidden');
    }
  });

  // Batch Turbo Renderer (Pillar 5 Batch Mode)
  const btnRenderAllShorts = document.getElementById('btn-render-all-shorts');
  if (btnRenderAllShorts) {
    btnRenderAllShorts.addEventListener('click', async () => {
      if (!currentAnalysis || !currentAnalysis.candidates || currentAnalysis.candidates.length === 0) {
        showToast('Please analyze a video first');
        return;
      }
      const candidates = currentAnalysis.candidates.slice(0, 5);
      showToast(`Turbo Batch Rendering: creating all ${candidates.length} shorts...`);
      btnRenderAllShorts.disabled = true;
      btnRenderShort.disabled = true;
      renderProgressCard.classList.remove('hidden');

      for (let i = 0; i < candidates.length; i++) {
        const cand = candidates[i];
        renderStatusMsg.textContent = `Batch Turbo: Rendering Short ${i + 1} of ${candidates.length} (GPU)...`;
        renderPct.textContent = `${Math.round((i / candidates.length) * 100)}%`;
        renderProgressFill.style.width = `${Math.round((i / candidates.length) * 100)}%`;

        try {
          const res = await fetch('/api/render-clip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              url: shortsUrlInput.value.trim(),
              start_sec: cand.start,
              end_sec: cand.end,
              clip_text: cand.text,
              video_id: currentAnalysis.video_id,
              video_title: `${currentAnalysis.title} (Part ${i + 1})`,
              style_name: selectedStyle,
              progress_bar: chkProgressBar.checked,
              watermark: inputWatermark.value.trim() || null
            })
          });
          const json = await res.json();
          if (json.success) {
            await new Promise((resolve) => {
              const sse = new EventSource(`/api/stream/${json.job_id}`);
              sse.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.status === 'completed' || data.status === 'failed') {
                  sse.close();
                  if (data.status === 'completed' && i === candidates.length - 1) {
                    displayRenderedShort(data.result);
                  }
                  resolve();
                }
              };
              sse.onerror = () => { sse.close(); resolve(); };
            });
          }
        } catch (e) {
          console.error(e);
        }
      }

      btnRenderAllShorts.disabled = false;
      btnRenderShort.disabled = false;
      renderProgressCard.classList.add('hidden');
      showToast('All shorts created successfully! Check Media Vault to download them all.');
      loadMediaVault();
    });
  }

  function listenToRenderProgress(jobId) {
    if (activeEventSource) {
      activeEventSource.close();
    }

    activeEventSource = new EventSource(`/api/stream/${jobId}`);

    activeEventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const pct = data.progress || 0;
        renderProgressFill.style.width = `${pct}%`;
        renderPct.textContent = `${pct}%`;
        renderStatusMsg.textContent = data.message || 'Processing...';

        if (data.status === 'completed') {
          activeEventSource.close();
          btnRenderShort.disabled = false;
          renderProgressCard.classList.add('hidden');
          displayRenderedShort(data.result);
          showToast('Short rendered successfully in record time!');
        } else if (data.status === 'failed') {
          activeEventSource.close();
          btnRenderShort.disabled = false;
          renderProgressCard.classList.add('hidden');
          showToast(`Render failed: ${data.error || data.message}`);
        }
      } catch (err) {
        console.error('SSE Parse error', err);
      }
    };

    activeEventSource.onerror = (err) => {
      console.warn('SSE connection closed or re-connecting...');
    };
  }

  function displayRenderedShort(result) {
    renderedShowcaseCard.classList.remove('hidden');
    renderStatTime.textContent = `${result.render_time_sec || '-'}s`;
    renderStatSize.textContent = `${result.file_size_mb || '-'} MB`;

    // Video Player
    shortVideoPlayer.src = result.video_url;
    btnDownloadShort.href = result.video_url;

    // Update Stage Profiling banner
    if (result.timings) {
      tRnd.textContent = `${result.timings.render_ms || 0}ms`;
      tTotal.textContent = `${((result.timings.total_ms || 0) / 1000).toFixed(1)}s`;
    }

    // Publishing Hub (Pillar 5)
    const pub = result.publishing || {};
    abTitlesList.innerHTML = '';
    (pub.titles_ab || []).forEach(title => {
      const item = document.createElement('div');
      item.className = 'ab-title-item';
      item.innerHTML = `<span>${title}</span> <i class="fa-regular fa-copy"></i>`;
      item.addEventListener('click', () => {
        navigator.clipboard.writeText(title);
        showToast('Title copied to clipboard!');
      });
      abTitlesList.appendChild(item);
    });

    pubDescription.value = pub.description || '';

    // Scroll smoothly to preview
    renderedShowcaseCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  if (btnCopyDesc) {
    btnCopyDesc.addEventListener('click', () => {
      navigator.clipboard.writeText(pubDescription.value);
      showToast('Description & tags copied!');
    });
  }

  // -----------------------------------------
  // TRADITIONAL DOWNLOADER TAB
  // -----------------------------------------
  if (btnClearUrl) {
    btnClearUrl.addEventListener('click', () => {
      videoUrlInput.value = '';
      videoUrlInput.focus();
    });
  }

  if (btnInspectUrl) {
    btnInspectUrl.addEventListener('click', async () => {
      const url = videoUrlInput.value.trim();
      if (!url) {
        showToast('Please enter a YouTube link');
        return;
      }

      btnInspectUrl.disabled = true;
      inspectSpinner.style.display = 'block';

      try {
        const res = await fetch('/api/info', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        const json = await res.json();
        if (!json.success) throw new Error(json.error || 'Failed to inspect link');

        currentVideoInfo = json.data;
        renderVideoDetails(currentVideoInfo);
      } catch (e) {
        showToast(`Error: ${e.message}`);
      } finally {
        btnInspectUrl.disabled = false;
        inspectSpinner.style.display = 'none';
      }
    });
  }

  function renderVideoDetails(info) {
    videoDetailsCard.classList.remove('hidden');
    metaThumb.src = info.thumbnail || '';
    metaDuration.textContent = formatSec(info.duration || 0);
    metaTitle.textContent = info.title || 'Video Title';
    metaUploader.textContent = info.uploader || 'Uploader';
    metaViews.textContent = `${(info.view_count || 0).toLocaleString()} views`;
    metaDesc.textContent = info.description || '';

    // Resolutions
    resolutionsContainer.innerHTML = '';
    const formats = info.formats || [];
    formats.forEach((fmt, i) => {
      const chip = document.createElement('button');
      chip.className = `chip ${i === 0 ? 'active' : ''}`;
      chip.textContent = `${fmt.height}p`;
      chip.addEventListener('click', () => {
        document.querySelectorAll('#resolutions-container .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        selectedResolution = fmt.height;
      });
      resolutionsContainer.appendChild(chip);
    });

    videoDetailsCard.scrollIntoView({ behavior: 'smooth' });
  }

  if (modeVideoBtn && modeAudioBtn) {
    modeVideoBtn.addEventListener('click', () => {
      modeVideoBtn.classList.add('active');
      modeAudioBtn.classList.remove('active');
      videoOptionsPanel.classList.remove('hidden');
      audioOptionsPanel.classList.add('hidden');
      selectedMode = 'video';
    });

    modeAudioBtn.addEventListener('click', () => {
      modeAudioBtn.classList.add('active');
      modeVideoBtn.classList.remove('active');
      audioOptionsPanel.classList.remove('hidden');
      videoOptionsPanel.classList.add('hidden');
      selectedMode = 'audio';
    });
  }

  if (btnStartDownload) {
    btnStartDownload.addEventListener('click', async () => {
      const url = videoUrlInput.value.trim();
      if (!url) return;

      btnStartDownload.disabled = true;
      dlProgressContainer.classList.remove('hidden');
      dlProgressBar.style.width = '10%';
      dlStatusText.textContent = 'Initializing download...';

      try {
        const res = await fetch('/api/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url,
            type: selectedMode,
            resolution: selectedResolution,
            video_format: selectedVideoFormat,
            audio_format: selectedAudioFormat,
            audio_quality: selectedAudioQuality
          })
        });
        const json = await res.json();
        if (!json.success) throw new Error(json.error || 'Failed to start download');

        pollDownloadJob(json.job_id);
      } catch (e) {
        showToast(`Error: ${e.message}`);
        btnStartDownload.disabled = false;
      }
    });
  }

  function pollDownloadJob(jobId) {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/job/${jobId}`);
        const json = await res.json();
        if (!json.success) return;

        const job = json.job;
        dlProgressBar.style.width = `${job.percent}%`;
        dlStatusText.textContent = job.message || 'Downloading...';
        if (job.speed_str) dlSpeed.textContent = job.speed_str;
        if (job.total_str) dlSize.textContent = `${job.downloaded_str || '0'} / ${job.total_str}`;

        if (job.status === 'completed') {
          clearInterval(timer);
          btnStartDownload.disabled = false;
          dlStatusText.textContent = 'Completed!';
          showToast('Download finished successfully!');
        } else if (job.status === 'failed') {
          clearInterval(timer);
          btnStartDownload.disabled = false;
          showToast(`Download failed: ${job.error}`);
        }
      } catch (e) {
        // network retry
      }
    }, 1000);
  }

  // -----------------------------------------
  // MEDIA VAULT
  // -----------------------------------------
  async function loadMediaVault() {
    try {
      const res = await fetch('/api/library');
      const data = await res.json();
      if (!data.success) return;

      vaultCountBadge.textContent = (data.shorts.length + data.downloads.length).toString();

      // Render Shorts list
      vaultShortsList.innerHTML = '';
      if (data.shorts.length === 0) {
        vaultShortsList.innerHTML = `<div class="empty-state">No shorts generated yet. Run a Fast AI Scan in the Shorts Studio tab!</div>`;
      } else {
        data.shorts.forEach(s => {
          const item = document.createElement('div');
          item.className = 'vault-item';
          item.innerHTML = `
            <div>
              <strong>${s.title}</strong>
              <div style="font-size: 0.8rem; color: var(--text-muted);">${s.clips.length} clip(s)</div>
            </div>
            <a href="${s.clips[0].download_url}" class="btn-primary btn-small" download>
              <i class="fa-solid fa-download"></i> Download
            </a>
          `;
          vaultShortsList.appendChild(item);
        });
      }

      // Render Downloads list
      vaultDownloadsList.innerHTML = '';
      if (data.downloads.length === 0) {
        vaultDownloadsList.innerHTML = `<div class="empty-state">No downloads yet.</div>`;
      } else {
        data.downloads.forEach(d => {
          const item = document.createElement('div');
          item.className = 'vault-item';
          item.innerHTML = `
            <div>
              <strong>${d.filename}</strong>
              <div style="font-size: 0.8rem; color: var(--text-muted);">${d.size} • ${d.type}</div>
            </div>
            <a href="${d.download_url}" class="btn-primary btn-small" download>
              <i class="fa-solid fa-download"></i> Download
            </a>
          `;
          vaultDownloadsList.appendChild(item);
        });
      }
    } catch (e) {
      console.error('Vault load error', e);
    }
  }

  if (btnRefreshVault) {
    btnRefreshVault.addEventListener('click', loadMediaVault);
  }
});
