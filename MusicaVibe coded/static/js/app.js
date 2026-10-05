/**
 * Musica AI Vibe - Master Application Controller
 * Manages uploads, playback synchronization, OSMD sheet music, and UI interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const progressCard = document.getElementById('progress-card');
  const progressStatus = document.getElementById('progress-status');
  const progressSub = document.getElementById('progress-sub');
  const resultsSection = document.getElementById('results-section');

  // Tabs
  const tabPianoroll = document.getElementById('tab-pianoroll');
  const tabSheet = document.getElementById('tab-sheet');
  const viewPianoroll = document.getElementById('view-pianoroll');
  const viewSheet = document.getElementById('view-sheet');

  // Dashboard Metrics
  const metricBpm = document.getElementById('metric-bpm');
  const metricKey = document.getElementById('metric-key');
  const metricDuration = document.getElementById('metric-duration');
  const metricNotes = document.getElementById('metric-notes');
  const beatLed = document.getElementById('beat-led');
  const trackNameDisplay = document.getElementById('track-name');

  // Buttons & Downloads
  const btnDownloadMidi = document.getElementById('btn-download-midi');
  const btnDownloadMusicxml = document.getElementById('btn-download-musicxml');
  const btnPrintSheet = document.getElementById('btn-print-sheet');

  // Transport Controls
  const btnPlay = document.getElementById('btn-play');
  const btnStop = document.getElementById('btn-stop');
  const btnLoop = document.getElementById('btn-loop');
  const timeCurrent = document.getElementById('time-current');
  const timeTotal = document.getElementById('time-total');
  const speedSelect = document.getElementById('speed-select');
  const zoomInBtn = document.getElementById('btn-zoom-in');
  const zoomOutBtn = document.getElementById('btn-zoom-out');
  const volumeSlider = document.getElementById('volume-slider');
  const btnMute = document.getElementById('btn-mute');

  // Audio Source Buttons
  const srcSynth = document.getElementById('src-synth');
  const srcAudio = document.getElementById('src-audio');
  const srcBoth = document.getElementById('src-both');

  // Mode Selection
  let transcriptionMode = 'polyphonic';
  const modePoly = document.getElementById('mode-poly');
  const modeMelody = document.getElementById('mode-melody');

  // Audio Playback state
  let audioData = null;
  let isPlaying = false;
  let isLooping = false;
  let playbackSpeed = 1.0;
  let playbackSource = 'synth'; // 'synth', 'audio', 'both'
  let currentTime = 0.0;
  let duration = 0.0;
  let animationFrameId = null;
  let lastFrameTimestamp = null;
  let notesPlayedSet = new Set();

  // Audio Element for original track
  const originalAudio = new Audio();
  originalAudio.preload = 'auto';

  // Initialize Piano Roll Engine
  const pianoRoll = new PianoRoll('pianoroll-canvas', 'keyboard-container');

  // OSMD Sheet Music instance
  let osmd = null;

  // ----------------------------------------------------
  // Transcribe Mode Selection
  // ----------------------------------------------------
  if (modePoly && modeMelody) {
    modePoly.addEventListener('click', () => {
      transcriptionMode = 'polyphonic';
      modePoly.classList.add('active');
      modeMelody.classList.remove('active');
    });
    modeMelody.addEventListener('click', () => {
      transcriptionMode = 'melody';
      modeMelody.classList.add('active');
      modePoly.classList.remove('active');
    });
  }

  // ----------------------------------------------------
  // Drag & Drop & Upload Handling
  // ----------------------------------------------------
  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });

    ['dragleave', 'dragend'].forEach(type => {
      dropzone.addEventListener(type, () => dropzone.classList.remove('dragover'));
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleUpload(e.target.files[0]);
      }
    });
  }

  // Quick Sample Buttons
  document.querySelectorAll('.sample-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      const sampleFile = btn.dataset.sample;
      handleSampleAnalysis(sampleFile);
    });
  });

  function showLoading(status, sub) {
    if (progressCard) {
      progressCard.style.display = 'block';
      progressStatus.textContent = status;
      progressSub.textContent = sub;
      progressCard.scrollIntoView({ behavior: 'smooth' });
    }
  }

  function hideLoading() {
    if (progressCard) {
      progressCard.style.display = 'none';
    }
  }

  function handleUpload(file) {
    stopPlayback();
    showLoading('Analyzing Audio Spectrogram...', 'Detecting tempo, beats per minute, and harmonic key profile');

    const formData = new FormData();
    formData.append('audio', file);
    formData.append('mode', transcriptionMode);

    setTimeout(() => {
      progressStatus.textContent = 'Transcribing Notes & Generating Scores...';
      progressSub.textContent = 'Extracting pitch contours, synthesizing MIDI and MusicXML sheet music';
    }, 1200);

    fetch('/api/analyze', {
      method: 'POST',
      body: formData
    })
      .then(res => {
        if (!res.ok) return res.json().then(d => { throw new Error(d.error || 'Upload error'); });
        return res.json();
      })
      .then(data => {
        hideLoading();
        loadAnalysisResults(data, file.name);
      })
      .catch(err => {
        hideLoading();
        alert('Error analyzing audio: ' + err.message);
      });
  }

  function handleSampleAnalysis(sampleName) {
    stopPlayback();
    showLoading('Analyzing Demo Track...', 'Detecting tempo, beats per minute, and harmonic key profile');

    setTimeout(() => {
      progressStatus.textContent = 'Transcribing Notes & Building Sheet Music...';
      progressSub.textContent = 'Constructing piano roll and grand staff score';
    }, 800);

    fetch('/api/analyze-sample', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sample: sampleName, mode: transcriptionMode })
    })
      .then(res => {
        if (!res.ok) return res.json().then(d => { throw new Error(d.error || 'Sample error'); });
        return res.json();
      })
      .then(data => {
        hideLoading();
        const prettyNames = {
          'sample_classical_fur_elise.wav': 'Für Elise Motif (Classical Piano)',
          'sample_lofi_chords.wav': 'Lo-Fi Pop Chords (Am - F - C - G)',
          'sample_jazz_blues.wav': 'Jazz Blues Pentatonic Hook'
        };
        loadAnalysisResults(data, prettyNames[sampleName] || sampleName);
      })
      .catch(err => {
        hideLoading();
        alert('Error analyzing sample: ' + err.message);
      });
  }

  // ----------------------------------------------------
  // Load & Display Analysis Results
  // ----------------------------------------------------
  function loadAnalysisResults(data, trackDisplayName) {
    audioData = data;
    duration = data.duration || 10.0;
    currentTime = 0.0;

    // Display Track Info
    if (trackNameDisplay) trackNameDisplay.textContent = trackDisplayName;

    // Update Dashboard Metrics
    if (metricBpm) metricBpm.textContent = `${data.bpm.toFixed(1)}`;
    if (metricKey) metricKey.textContent = data.key || 'C Major';
    if (metricDuration) metricDuration.textContent = `${duration.toFixed(1)}s`;
    if (metricNotes) metricNotes.textContent = `${data.notes_count} Notes`;
    if (timeTotal) timeTotal.textContent = formatTime(duration);
    if (timeCurrent) timeCurrent.textContent = formatTime(0);

    // Setup Download Links
    if (btnDownloadMidi) btnDownloadMidi.href = data.midi_url;
    if (btnDownloadMusicxml) btnDownloadMusicxml.href = data.musicxml_url;

    // Setup Original Audio element
    originalAudio.src = data.audio_url;
    originalAudio.load();

    // Feed Data to Piano Roll
    pianoRoll.setData(data);

    // Render Sheet Music
    renderSheetMusic(data.musicxml_content);

    // Show Results Section
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });

    // Start Beat LED flash sequence
    startBeatLedSync(data.bpm, data.beat_times);
  }

  // ----------------------------------------------------
  // Beat LED Sync
  // ----------------------------------------------------
  let beatFlashInterval = null;
  function startBeatLedSync(bpm, beatTimes) {
    if (beatFlashInterval) clearInterval(beatFlashInterval);
    if (!beatLed) return;

    const intervalMs = (60.0 / Math.max(20.0, bpm)) * 1000;
    beatFlashInterval = setInterval(() => {
      if (isPlaying) {
        beatLed.classList.add('pulse');
        setTimeout(() => beatLed.classList.remove('pulse'), 90);
      }
    }, intervalMs);
  }

  // ----------------------------------------------------
  // Sheet Music (OpenSheetMusicDisplay)
  // ----------------------------------------------------
  function renderSheetMusic(musicxmlContent) {
    const target = document.getElementById('osmd-score-target');
    if (!target) return;
    target.innerHTML = '';

    try {
      if (window.opensheetmusicdisplay && window.opensheetmusicdisplay.OpenSheetMusicDisplay) {
        osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay(target, {
          autoResize: true,
          drawTitle: true,
          drawComposer: true,
          drawPartNames: false,
          drawMeasureNumbers: true,
          backend: 'svg'
        });
        osmd.load(musicxmlContent).then(() => {
          osmd.render();
        }).catch(err => {
          console.warn('OSMD render warning, rendering fallback score:', err);
          renderFallbackSheetMusic(audioData.notes, audioData.bpm);
        });
      } else {
        renderFallbackSheetMusic(audioData.notes, audioData.bpm);
      }
    } catch (e) {
      console.warn('OSMD exception:', e);
      renderFallbackSheetMusic(audioData.notes, audioData.bpm);
    }
  }

  // Fallback SVG Score Renderer (always renders score cleanly even offline)
  function renderFallbackSheetMusic(notes, bpm) {
    const target = document.getElementById('osmd-score-target');
    if (!target || !notes) return;

    let svg = `<svg class="svg-score-canvas" viewBox="0 0 1000 400" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.3"/>
        </filter>
      </defs>
      <rect width="1000" height="400" fill="#ffffff" />
      <text x="500" y="32" text-anchor="middle" font-family="serif" font-size="20" font-weight="bold" fill="#111827">Transcribed Piano Score</text>
      <text x="500" y="52" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#64748b">Detected Tempo: ${bpm.toFixed(1)} BPM • 4/4 Time</text>`;

    // Draw 5 staff lines for Treble (y: 90, 105, 120, 135, 150)
    for (let i = 0; i < 5; i++) {
      const y = 90 + i * 15;
      svg += `<line x1="50" y1="${y}" x2="950" y2="${y}" stroke="#334155" stroke-width="1.5" />`;
    }
    // Treble Clef Text & Time Signature
    svg += `<text x="60" y="145" font-family="serif" font-size="52" fill="#0f172a">𝄞</text>`;
    svg += `<text x="100" y="115" font-family="serif" font-size="24" font-weight="bold" fill="#0f172a">4</text>`;
    svg += `<text x="100" y="145" font-family="serif" font-size="24" font-weight="bold" fill="#0f172a">4</text>`;

    // Draw 5 staff lines for Bass (y: 220, 235, 250, 265, 280)
    for (let i = 0; i < 5; i++) {
      const y = 220 + i * 15;
      svg += `<line x1="50" y1="${y}" x2="950" y2="${y}" stroke="#334155" stroke-width="1.5" />`;
    }
    // Bass Clef Text & Time Signature
    svg += `<text x="60" y="265" font-family="serif" font-size="44" fill="#0f172a">𝄢</text>`;
    svg += `<text x="100" y="245" font-family="serif" font-size="24" font-weight="bold" fill="#0f172a">4</text>`;
    svg += `<text x="100" y="275" font-family="serif" font-size="24" font-weight="bold" fill="#0f172a">4</text>`;

    // Brace and Bar lines at ends
    svg += `<line x1="50" y1="90" x2="50" y2="280" stroke="#0f172a" stroke-width="3" />`;
    svg += `<line x1="950" y1="90" x2="950" y2="280" stroke="#0f172a" stroke-width="3" />`;

    // Measure dividers (3 bars across the line)
    [325, 535, 745].forEach(x => {
      svg += `<line x1="${x}" y1="90" x2="${x}" y2="150" stroke="#94a3b8" stroke-width="1.5" />`;
      svg += `<line x1="${x}" y1="220" x2="${x}" y2="280" stroke="#94a3b8" stroke-width="1.5" />`;
    });

    // Render sample note heads from transcription
    const maxRender = Math.min(24, notes.length);
    const stepX = 800 / Math.max(1, maxRender);

    for (let idx = 0; idx < maxRender; idx++) {
      const n = notes[idx];
      const nx = 140 + idx * stepX;
      const isTreble = n.pitch >= 60;

      let ny = 120;
      if (isTreble) {
        // C4 = 165 (one ledger line below treble), B5 = 75
        ny = 165 - (n.pitch - 60) * 4.5;
      } else {
        // C4 = 205 (one ledger line above bass), C3 = 250
        ny = 250 - (n.pitch - 48) * 4.5;
      }

      // Note head
      svg += `<ellipse cx="${nx}" cy="${ny}" rx="6" ry="4.5" fill="#0f172a" transform="rotate(-20 ${nx} ${ny})" />`;
      // Stem
      svg += `<line x1="${nx + 5}" y1="${ny}" x2="${nx + 5}" y2="${ny - 28}" stroke="#0f172a" stroke-width="1.5" />`;
      // Pitch name label underneath
      svg += `<text x="${nx}" y="${ny + 16}" text-anchor="middle" font-family="sans-serif" font-size="9" font-weight="600" fill="#475569">${n.name}</text>`;
    }

    svg += `</svg>`;
    target.innerHTML = svg;
  }

  // Print Sheet Music
  if (btnPrintSheet) {
    btnPrintSheet.addEventListener('click', () => {
      const printWin = window.open('', '_blank');
      const scoreHtml = document.getElementById('osmd-score-target').innerHTML;
      printWin.document.write(`
        <html>
          <head>
            <title>Musica AI Vibe - Sheet Music</title>
            <style>
              body { font-family: serif; margin: 2rem; background: #fff; text-align: center; }
              svg { max-width: 100%; height: auto; }
            </style>
          </head>
          <body>
            <h1>${trackNameDisplay ? trackNameDisplay.textContent : 'Sheet Music'}</h1>
            <p>BPM: ${audioData ? audioData.bpm.toFixed(1) : '120.0'} • Transcribed by Musica AI Vibe</p>
            <div>${scoreHtml}</div>
            <script>setTimeout(() => { window.print(); window.close(); }, 500);<\/script>
          </body>
        </html>
      `);
      printWin.document.close();
    });
  }

  // ----------------------------------------------------
  // View Tabs Switching
  // ----------------------------------------------------
  if (tabPianoroll && tabSheet) {
    tabPianoroll.addEventListener('click', () => {
      tabPianoroll.classList.add('active');
      tabSheet.classList.remove('active');
      viewPianoroll.style.display = 'block';
      viewSheet.style.display = 'none';
      pianoRoll.draw();
    });

    tabSheet.addEventListener('click', () => {
      tabSheet.classList.add('active');
      tabPianoroll.classList.remove('active');
      viewSheet.style.display = 'block';
      viewPianoroll.style.display = 'none';
      if (osmd) {
        osmd.render();
      }
    });
  }

  // ----------------------------------------------------
  // Playback & Synchronization Engine
  // ----------------------------------------------------
  function startPlayback() {
    if (!audioData) return;
    if (window.pianoSynth) window.pianoSynth.init();

    isPlaying = true;
    btnPlay.innerHTML = '⏸';
    btnPlay.title = 'Pause (Space)';

    lastFrameTimestamp = performance.now();

    if (playbackSource === 'audio' || playbackSource === 'both') {
      originalAudio.currentTime = currentTime;
      originalAudio.playbackRate = playbackSpeed;
      originalAudio.play().catch(e => console.log('Audio autoplay prevented:', e));
    }

    requestAnimationFrame(playbackLoop);
  }

  function pausePlayback() {
    isPlaying = false;
    btnPlay.innerHTML = '▶';
    btnPlay.title = 'Play (Space)';
    originalAudio.pause();
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (window.pianoSynth) window.pianoSynth.stopAll();
    pianoRoll.highlightKeys([]);
  }

  function stopPlayback() {
    pausePlayback();
    currentTime = 0.0;
    notesPlayedSet.clear();
    originalAudio.currentTime = 0.0;
    pianoRoll.seek(0.0);
    if (timeCurrent) timeCurrent.textContent = formatTime(0);
  }

  function playbackLoop(timestamp) {
    if (!isPlaying) return;

    const deltaSec = (timestamp - lastFrameTimestamp) / 1000.0 * playbackSpeed;
    lastFrameTimestamp = timestamp;

    const prevTime = currentTime;
    currentTime += deltaSec;

    // Check if reached end of track
    if (currentTime >= duration) {
      if (isLooping) {
        currentTime = 0.0;
        notesPlayedSet.clear();
        if (playbackSource === 'audio' || playbackSource === 'both') {
          originalAudio.currentTime = 0.0;
          originalAudio.play().catch(() => { });
        }
      } else {
        stopPlayback();
        return;
      }
    }

    // Trigger Synth Notes during interval [prevTime, currentTime]
    if (playbackSource === 'synth' || playbackSource === 'both') {
      if (audioData && audioData.notes) {
        audioData.notes.forEach((note, idx) => {
          if (!notesPlayedSet.has(idx)) {
            if (note.start >= prevTime && note.start <= currentTime) {
              notesPlayedSet.add(idx);
              window.pianoSynth.playNote(note.pitch, note.velocity || 0.8, note.duration || 0.4);
            }
          }
        });
      }
    }

    // Update Piano Roll View and keys
    pianoRoll.updateTime(currentTime);

    // Auto-scroll piano roll container to keep playhead centered
    const canvasContainer = document.querySelector('.pianoroll-canvas-container');
    if (canvasContainer) {
      const playheadPx = currentTime * pianoRoll.pixelsPerSecond;
      const targetScroll = playheadPx - (canvasContainer.clientWidth / 2);
      if (Math.abs(canvasContainer.scrollLeft - targetScroll) > 20) {
        canvasContainer.scrollLeft = Math.max(0, targetScroll);
      }
    }

    // Update time readout
    if (timeCurrent) timeCurrent.textContent = formatTime(currentTime);

    animationFrameId = requestAnimationFrame(playbackLoop);
  }

  // Transport Button Listeners
  if (btnPlay) {
    btnPlay.addEventListener('click', () => {
      if (isPlaying) pausePlayback();
      else startPlayback();
    });
  }

  if (btnStop) {
    btnStop.addEventListener('click', () => {
      stopPlayback();
    });
  }

  if (btnLoop) {
    btnLoop.addEventListener('click', () => {
      isLooping = !isLooping;
      btnLoop.classList.toggle('active', isLooping);
      btnLoop.style.color = isLooping ? '#10b981' : '#fff';
    });
  }

  // Keyboard Spacebar play/pause shortcut
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
      e.preventDefault();
      if (isPlaying) pausePlayback();
      else startPlayback();
    }
  });

  // Piano Roll Scrub callback
  pianoRoll.onSeekCallback = (seekTime) => {
    currentTime = seekTime;
    originalAudio.currentTime = seekTime;

    // Reset note played cache for notes after seekTime
    notesPlayedSet.clear();
    if (audioData && audioData.notes) {
      audioData.notes.forEach((note, idx) => {
        if (note.start < currentTime) {
          notesPlayedSet.add(idx);
        }
      });
    }
    if (timeCurrent) timeCurrent.textContent = formatTime(currentTime);
  };

  // Speed Selector
  if (speedSelect) {
    speedSelect.addEventListener('change', (e) => {
      playbackSpeed = parseFloat(e.target.value) || 1.0;
      originalAudio.playbackRate = playbackSpeed;
    });
  }

  // Audio Source Switcher
  function setPlaybackSource(src) {
    playbackSource = src;
    [srcSynth, srcAudio, srcBoth].forEach(btn => btn && btn.classList.remove('active'));

    if (src === 'synth' && srcSynth) srcSynth.classList.add('active');
    if (src === 'audio' && srcAudio) srcAudio.classList.add('active');
    if (src === 'both' && srcBoth) srcBoth.classList.add('active');

    if (isPlaying) {
      if (src === 'synth') {
        originalAudio.pause();
      } else {
        originalAudio.currentTime = currentTime;
        originalAudio.play().catch(() => { });
      }
    }
  }

  if (srcSynth) srcSynth.addEventListener('click', () => setPlaybackSource('synth'));
  if (srcAudio) srcAudio.addEventListener('click', () => setPlaybackSource('audio'));
  if (srcBoth) srcBoth.addEventListener('click', () => setPlaybackSource('both'));

  // Zoom buttons
  if (zoomInBtn) {
    zoomInBtn.addEventListener('click', () => {
      pianoRoll.setZoom(pianoRoll.pixelsPerSecond + 30);
    });
  }
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener('click', () => {
      pianoRoll.setZoom(pianoRoll.pixelsPerSecond - 30);
    });
  }

  // Volume slider & mute
  if (volumeSlider) {
    volumeSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (window.pianoSynth) window.pianoSynth.setVolume(val);
      originalAudio.volume = val;
    });
  }

  if (btnMute) {
    btnMute.addEventListener('click', () => {
      const isMuted = window.pianoSynth.toggleMute();
      originalAudio.muted = isMuted;
      btnMute.textContent = isMuted ? '🔇' : '🔊';
    });
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}.${ms}`;
  }
});
