/**
 * Musica AI Vibe - Interactive Playable Piano Roll Engine
 * Handles rendering notes, beat grid, piano keys, scrubbing, and playhead.
 */

class PianoRoll {
  constructor(canvasId, keyboardContainerId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.keyboardContainer = document.getElementById(keyboardContainerId);
    
    this.notes = [];
    this.bpm = 120.0;
    this.duration = 10.0;
    this.currentTime = 0.0;
    this.isPlaying = false;
    
    // Viewport configuration
    this.pixelsPerSecond = 140; // horizontal zoom
    this.keyHeight = 18;        // vertical row height
    
    this.minPitch = 36; // C2
    this.maxPitch = 84; // C6
    
    this.pitchRange = [];
    this.activePitches = new Set();
    
    this.onSeekCallback = null;
    this.onKeyClickCallback = null;
    
    this.initEvents();
  }

  setData(data) {
    this.notes = data.notes || [];
    this.bpm = data.bpm || 120.0;
    this.duration = data.duration || 10.0;
    this.currentTime = 0.0;
    
    // Auto-calculate pitch range based on notes
    if (this.notes.length > 0) {
      const pitches = this.notes.map(n => n.pitch);
      this.minPitch = Math.max(21, Math.min(...pitches) - 2);
      this.maxPitch = Math.min(108, Math.max(...pitches) + 2);
    } else {
      this.minPitch = 48; // C3
      this.maxPitch = 72; // C5
    }
    
    this.buildPitchRange();
    this.renderKeyboard();
    this.resizeCanvas();
    this.draw();
  }

  buildPitchRange() {
    this.pitchRange = [];
    // From high pitch at the top to low pitch at the bottom
    for (let p = this.maxPitch; p >= this.minPitch; p--) {
      this.pitchRange.push(p);
    }
  }

  isBlackKey(pitch) {
    const semitone = pitch % 12;
    return [1, 3, 6, 8, 10].includes(semitone); // C#, D#, F#, G#, A#
  }

  getNoteName(pitch) {
    const names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    const oct = Math.floor(pitch / 12) - 1;
    return `${names[pitch % 12]}${oct}`;
  }

  renderKeyboard() {
    if (!this.keyboardContainer) return;
    this.keyboardContainer.innerHTML = '';
    
    const totalHeight = this.pitchRange.length * this.keyHeight;
    this.keyboardContainer.style.height = `${totalHeight}px`;

    this.pitchRange.forEach((pitch, index) => {
      const isBlack = this.isBlackKey(pitch);
      const keyElem = document.createElement('div');
      keyElem.className = `piano-key ${isBlack ? 'black' : 'white'}`;
      keyElem.dataset.pitch = pitch;
      keyElem.style.top = `${index * this.keyHeight}px`;
      keyElem.style.height = `${this.keyHeight}px`;

      // Label C octaves and white keys
      if (!isBlack || (pitch % 12 === 0)) {
        keyElem.textContent = this.getNoteName(pitch);
      }

      keyElem.addEventListener('mousedown', () => {
        keyElem.classList.add('active');
        if (window.pianoSynth) {
          window.pianoSynth.playNote(pitch, 0.85, 0.5);
        }
        if (this.onKeyClickCallback) this.onKeyClickCallback(pitch);
      });

      keyElem.addEventListener('mouseup', () => {
        keyElem.classList.remove('active');
      });
      keyElem.addEventListener('mouseleave', () => {
        keyElem.classList.remove('active');
      });

      this.keyboardContainer.appendChild(keyElem);
    });
  }

  highlightKeys(activePitchList) {
    if (!this.keyboardContainer) return;
    const allKeys = this.keyboardContainer.querySelectorAll('.piano-key');
    allKeys.forEach(k => {
      const p = parseInt(k.dataset.pitch, 10);
      if (activePitchList.includes(p)) {
        k.classList.add('active');
      } else {
        k.classList.remove('active');
      }
    });
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const totalWidth = Math.max(window.innerWidth, (this.duration + 2.0) * this.pixelsPerSecond);
    const totalHeight = this.pitchRange.length * this.keyHeight;
    
    this.canvas.width = totalWidth;
    this.canvas.height = totalHeight;
    this.canvas.style.width = `${totalWidth}px`;
    this.canvas.style.height = `${totalHeight}px`;
  }

  setZoom(pps) {
    this.pixelsPerSecond = Math.max(60, Math.min(350, pps));
    this.resizeCanvas();
    this.draw();
  }

  initEvents() {
    if (!this.canvas) return;

    let isDragging = false;

    const handleScrub = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const targetTime = Math.max(0, Math.min(this.duration, clickX / this.pixelsPerSecond));
      this.seek(targetTime);
      if (this.onSeekCallback) {
        this.onSeekCallback(targetTime);
      }
    };

    this.canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      handleScrub(e);
    });

    window.addEventListener('mousemove', (e) => {
      if (isDragging) {
        handleScrub(e);
      }
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });
  }

  seek(time) {
    this.currentTime = Math.max(0, Math.min(this.duration, time));
    this.draw();
  }

  updateTime(time) {
    this.currentTime = time;
    this.draw();
    
    // Find currently active notes
    const activeNotes = this.notes.filter(n => {
      return this.currentTime >= n.start && this.currentTime <= (n.start + n.duration);
    });
    const activePitches = activeNotes.map(n => n.pitch);
    this.highlightKeys(activePitches);
  }

  getNoteColor(pitch, velocity = 0.8) {
    // Hue based on pitch class
    const semitone = pitch % 12;
    const hues = [
      260, // C - Purple
      280, // C# - Deep Purple
      310, // D - Magenta
      335, // D# - Pink
      350, // E - Crimson
      15,  // F - Coral
      35,  // F# - Amber
      55,  // G - Gold
      140, // G# - Emerald
      175, // A - Teal
      195, // A# - Cyan
      220  // B - Blue
    ];
    const hue = hues[semitone];
    const light = 50 + Math.round(velocity * 18);
    return {
      fill: `hsla(${hue}, 85%, ${light}%, 0.85)`,
      border: `hsl(${hue}, 95%, ${light + 15}%)`,
      glow: `hsla(${hue}, 90%, 60%, 0.4)`
    };
  }

  draw() {
    if (!this.ctx || !this.canvas) return;

    const width = this.canvas.width;
    const height = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, width, height);

    // 1. Draw horizontal row backgrounds
    this.pitchRange.forEach((pitch, i) => {
      const y = i * this.keyHeight;
      const isBlack = this.isBlackKey(pitch);
      ctx.fillStyle = isBlack ? '#0b0f1a' : '#111728';
      ctx.fillRect(0, y, width, this.keyHeight);

      // Horizontal grid lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, y + this.keyHeight);
      ctx.lineTo(width, y + this.keyHeight);
      ctx.stroke();
    });

    // 2. Draw vertical Beat & Measure lines
    const secondsPerBeat = 60.0 / Math.max(10.0, this.bpm);
    const beatsPerMeasure = 4;
    const measureDuration = secondsPerBeat * beatsPerMeasure;
    const totalMeasures = Math.ceil(this.duration / measureDuration) + 2;

    for (let m = 0; m < totalMeasures; m++) {
      const mTime = m * measureDuration;
      const mX = mTime * this.pixelsPerSecond;

      // Measure bar line (prominent)
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.35)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(mX, 0);
      ctx.lineTo(mX, height);
      ctx.stroke();

      // Measure number label
      ctx.fillStyle = 'rgba(192, 132, 252, 0.7)';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.fillText(`${m + 1}`, mX + 5, 14);

      // Sub-beat lines (subtle)
      for (let b = 1; b < beatsPerMeasure; b++) {
        const bTime = mTime + (b * secondsPerBeat);
        const bX = bTime * this.pixelsPerSecond;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(bX, 0);
        ctx.lineTo(bX, height);
        ctx.stroke();
      }
    }

    // 3. Draw Transcribed Notes
    this.notes.forEach(note => {
      const pIdx = this.pitchRange.indexOf(note.pitch);
      if (pIdx === -1) return;

      const y = pIdx * this.keyHeight + 2;
      const h = this.keyHeight - 4;
      const x = note.start * this.pixelsPerSecond;
      const w = Math.max(6, note.duration * this.pixelsPerSecond);

      const isActive = (this.currentTime >= note.start && this.currentTime <= (note.start + note.duration));
      const colors = this.getNoteColor(note.pitch, note.velocity);

      // Note shadow / glow
      if (isActive) {
        ctx.shadowColor = '#06b6d4';
        ctx.shadowBlur = 15;
      } else {
        ctx.shadowColor = colors.glow;
        ctx.shadowBlur = 6;
      }

      // Rounded note box
      ctx.fillStyle = isActive ? '#38bdf8' : colors.fill;
      ctx.strokeStyle = isActive ? '#ffffff' : colors.border;
      ctx.lineWidth = isActive ? 2 : 1;

      const radius = 3;
      ctx.beginPath();
      ctx.roundRect(x, y, w, h, radius);
      ctx.fill();
      ctx.stroke();

      // Reset shadow
      ctx.shadowBlur = 0;

      // Note text label (if wide enough)
      if (w > 20) {
        ctx.fillStyle = isActive ? '#000000' : '#ffffff';
        ctx.font = 'bold 9px sans-serif';
        ctx.fillText(note.name, x + 4, y + h - 3);
      }
    });

    // 4. Draw Glowing Playhead
    const playheadX = this.currentTime * this.pixelsPerSecond;
    ctx.shadowColor = '#22d3ee';
    ctx.shadowBlur = 12;
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2.5;

    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, height);
    ctx.stroke();

    // Top pointer triangle
    ctx.fillStyle = '#06b6d4';
    ctx.beginPath();
    ctx.moveTo(playheadX - 6, 0);
    ctx.lineTo(playheadX + 6, 0);
    ctx.lineTo(playheadX, 10);
    ctx.closePath();
    ctx.fill();

    ctx.shadowBlur = 0;
  }
}

window.PianoRoll = PianoRoll;
