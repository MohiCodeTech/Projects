"""
Generates rich demo sample audio files (WAV) for instant testing in Musica AI Vibe.
1. Classical Piano Melody (Beethoven Fur Elise theme)
2. Lo-Fi Pop Chord Progression (Am - F - C - G)
3. Melodic Pentatonic Lead Lick
"""

import os
import numpy as np
import soundfile as sf

def generate_samples(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    sr = 22050
    
    def synth_piano_note(freq, duration, velocity=0.8, sample_rate=22050):
        """Synthesize a rich harmonic piano-like tone with attack, decay and harmonics."""
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Harmonics (fundamental + overtones with natural acoustic piano roll-off)
        harmonics = [
            (1.0, 1.0),
            (2.0, 0.5),
            (3.0, 0.25),
            (4.0, 0.12),
            (5.0, 0.06),
        ]
        note = np.zeros_like(t)
        for mult, amp in harmonics:
            note += amp * np.sin(2 * np.pi * (freq * mult) * t)
            
        # Exponential acoustic decay envelope with percussive attack
        attack_len = int(0.01 * sample_rate)
        envelope = np.exp(-3.5 * t / max(duration, 0.1))
        if len(envelope) > attack_len:
            envelope[:attack_len] = np.linspace(0, 1.0, attack_len)
            
        return note * envelope * velocity

    # 1. Classical Piano Theme (Fur Elise motif in A minor, 130 BPM)
    bpm1 = 130.0
    sec_per_beat1 = 60.0 / bpm1
    eighth1 = sec_per_beat1 * 0.5
    
    # E5, D#5, E5, D#5, E5, B4, D5, C5, A4 (accompanied by A2, E3, A3 bass arpeggio)
    melody_notes = [
        (659.25, eighth1),  # E5
        (622.25, eighth1),  # D#5
        (659.25, eighth1),  # E5
        (622.25, eighth1),  # D#5
        (659.25, eighth1),  # E5
        (493.88, eighth1),  # B4
        (587.33, eighth1),  # D5
        (523.25, eighth1),  # C5
        (440.00, sec_per_beat1 * 2),  # A4
    ]
    
    total_dur1 = sum(d for _, d in melody_notes) + 0.5
    track1 = np.zeros(int(sr * total_dur1))
    
    curr_t = 0.0
    for freq, dur in melody_notes:
        note_audio = synth_piano_note(freq, dur * 0.95, velocity=0.8, sample_rate=sr)
        start_idx = int(curr_t * sr)
        end_idx = start_idx + len(note_audio)
        if end_idx <= len(track1):
            track1[start_idx:end_idx] += note_audio
        curr_t += dur
        
    # Add bass accompaniment: A2 (110Hz), E3 (164.81Hz), A3 (220Hz)
    bass_notes = [
        (0.0, 110.0, sec_per_beat1),
        (sec_per_beat1, 164.81, sec_per_beat1),
        (sec_per_beat1 * 2, 220.0, sec_per_beat1 * 2),
    ]
    for b_start, b_freq, b_dur in bass_notes:
        b_audio = synth_piano_note(b_freq, b_dur * 0.9, velocity=0.6, sample_rate=sr)
        start_idx = int(b_start * sr)
        end_idx = start_idx + len(b_audio)
        if end_idx <= len(track1):
            track1[start_idx:end_idx] += b_audio
            
    track1 = track1 / (np.max(np.abs(track1)) + 1e-6) * 0.85
    p1 = os.path.join(output_dir, "sample_classical_fur_elise.wav")
    sf.write(p1, track1, sr)
    print("Generated sample 1:", p1)

    # 2. Pop / Lo-Fi Chord Progression: C - G - Am - F (100 BPM)
    bpm2 = 100.0
    sec_per_beat2 = 60.0 / bpm2
    chord_dur2 = sec_per_beat2 * 2.0  # 2 beats per chord
    
    chords = [
        [261.63, 329.63, 392.00],        # C Maj: C4, E4, G4
        [196.00, 246.94, 293.66],        # G Maj: G3, B3, D4
        [220.00, 261.63, 329.63],        # A Min: A3, C4, E4
        [174.61, 220.00, 261.63],        # F Maj: F3, A3, C4
    ]
    
    total_dur2 = len(chords) * chord_dur2 + 0.5
    track2 = np.zeros(int(sr * total_dur2))
    
    for i, chord in enumerate(chords):
        c_start = i * chord_dur2
        for f in chord:
            c_audio = synth_piano_note(f, chord_dur2 * 0.95, velocity=0.7, sample_rate=sr)
            start_idx = int(c_start * sr)
            end_idx = start_idx + len(c_audio)
            if end_idx <= len(track2):
                track2[start_idx:end_idx] += c_audio
                
    track2 = track2 / (np.max(np.abs(track2)) + 1e-6) * 0.85
    p2 = os.path.join(output_dir, "sample_lofi_chords.wav")
    sf.write(p2, track2, sr)
    print("Generated sample 2:", p2)

    # 3. Jazz / Blues Melodic Hook (120 BPM)
    bpm3 = 120.0
    sec_per_beat3 = 60.0 / bpm3
    q3 = sec_per_beat3
    e3 = sec_per_beat3 * 0.5
    
    jazz_notes = [
        (261.63, e3),  # C4
        (311.13, e3),  # Eb4
        (349.23, e3),  # F4
        (369.99, e3),  # F#4
        (392.00, q3),  # G4
        (466.16, e3),  # Bb4
        (523.25, q3 * 1.5),  # C5
    ]
    total_dur3 = sum(d for _, d in jazz_notes) + 0.5
    track3 = np.zeros(int(sr * total_dur3))
    
    curr_t = 0.0
    for freq, dur in jazz_notes:
        j_audio = synth_piano_note(freq, dur * 0.92, velocity=0.85, sample_rate=sr)
        start_idx = int(curr_t * sr)
        end_idx = start_idx + len(j_audio)
        if end_idx <= len(track3):
            track3[start_idx:end_idx] += j_audio
        curr_t += dur
        
    track3 = track3 / (np.max(np.abs(track3)) + 1e-6) * 0.85
    p3 = os.path.join(output_dir, "sample_jazz_blues.wav")
    sf.write(p3, track3, sr)
    print("Generated sample 3:", p3)

if __name__ == "__main__":
    generate_samples(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "samples"))
