/**
 * Musica AI Vibe - Web Audio Acoustic Piano Synthesizer
 * Polyphonic physical/additive acoustic piano sound synthesis.
 */

class PianoSynth {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.activeVoices = new Map();
    this.volume = 0.8;
    this.isMuted = false;
  }

  init() {
    if (!this.ctx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContextClass();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
      this.masterGain.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  setVolume(val) {
    this.volume = Math.max(0, Math.min(1, val));
    if (this.masterGain && !this.isMuted) {
      this.masterGain.gain.setTargetAtTime(this.volume, this.ctx.currentTime, 0.05);
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.masterGain) {
      const target = this.isMuted ? 0.0 : this.volume;
      this.masterGain.gain.setTargetAtTime(target, this.ctx.currentTime, 0.05);
    }
    return this.isMuted;
  }

  midiToFreq(midiPitch) {
    return 440.0 * Math.pow(2.0, (midiPitch - 69) / 12.0);
  }

  playNote(pitch, velocity = 0.8, duration = 0.5) {
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const freq = this.midiToFreq(pitch);

    // Harmonics for rich acoustic piano timbre
    const harmonics = [
      { mult: 1.0, gain: 1.0, decayMult: 1.0 },
      { mult: 2.0, gain: 0.45, decayMult: 1.2 },
      { mult: 3.0, gain: 0.22, decayMult: 1.5 },
      { mult: 4.0, gain: 0.12, decayMult: 1.8 },
      { mult: 5.0, gain: 0.06, decayMult: 2.2 },
      { mult: 6.0, gain: 0.03, decayMult: 2.5 },
    ];

    const voiceGain = this.ctx.createGain();
    const velFactor = Math.max(0.1, Math.min(1.0, velocity));
    
    // Low-pass filter simulating piano soundboard damping at higher octaves
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(Math.min(8000, freq * 8), now);

    const oscs = [];

    harmonics.forEach(h => {
      const osc = this.ctx.createOscillator();
      const hGain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq * h.mult, now);

      // Slight natural detune for piano string warmth
      if (h.mult === 1.0) {
        osc.detune.setValueAtTime((Math.random() - 0.5) * 3, now);
      }

      hGain.gain.setValueAtTime(h.gain * velFactor, now);
      // Exponential decay per harmonic
      const noteDecay = Math.max(0.2, duration * 1.5);
      hGain.gain.exponentialRampToValueAtTime(0.0001, now + (noteDecay / h.decayMult));

      osc.connect(hGain);
      hGain.connect(filter);

      osc.start(now);
      osc.stop(now + noteDecay + 0.1);
      oscs.push(osc);
    });

    // Percussive hammer attack transient
    const hammer = this.ctx.createOscillator();
    const hammerGain = this.ctx.createGain();
    hammer.type = 'triangle';
    hammer.frequency.setValueAtTime(freq * 0.5, now);
    hammerGain.gain.setValueAtTime(0.15 * velFactor, now);
    hammerGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.02);
    hammer.connect(hammerGain);
    hammerGain.connect(filter);
    hammer.start(now);
    hammer.stop(now + 0.05);
    oscs.push(hammer);

    filter.connect(voiceGain);
    voiceGain.connect(this.masterGain);

    // Keep voice reference
    const voiceKey = `${pitch}_${now}`;
    this.activeVoices.set(voiceKey, { oscs, filter, voiceGain });

    setTimeout(() => {
      this.activeVoices.delete(voiceKey);
    }, (duration + 1.5) * 1000);
  }

  stopAll() {
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setTargetAtTime(0.0, this.ctx.currentTime, 0.02);
      setTimeout(() => {
        if (!this.isMuted) {
          this.masterGain.gain.setTargetAtTime(this.volume, this.ctx.currentTime, 0.05);
        }
      }, 50);
    }
  }
}

// Global synth instance
window.pianoSynth = new PianoSynth();
