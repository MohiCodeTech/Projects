"""
Musica Vibe - Audio Music Analysis & Transcription Engine
Detects BPM/tempo, beats, musical key, and transcribes audio to notes (MIDI & MusicXML).
"""

import os
import numpy as np
import librosa
import soundfile as sf
from midi_writer import create_midi_file
from musicxml_writer import create_musicxml, midi_to_note_name

# Krumhansl-Kessler key profiles for key detection
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_key(y, sr):
    """Detects the musical key and mode (Major/Minor) using Chroma key profile correlation."""
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_avg = np.mean(chroma, axis=1)  # 12-dimensional vector
        
        # Normalize
        if np.linalg.norm(chroma_avg) > 0:
            chroma_avg = chroma_avg / np.linalg.norm(chroma_avg)
            
        maj_prof = MAJOR_PROFILE / np.linalg.norm(MAJOR_PROFILE)
        min_prof = MINOR_PROFILE / np.linalg.norm(MINOR_PROFILE)
        
        best_score = -999.0
        best_key = "C Major"
        
        for i in range(12):
            # Rotate chroma to align with root i
            rotated = np.roll(chroma_avg, -i)
            
            # Major correlation
            maj_score = float(np.dot(rotated, maj_prof))
            if maj_score > best_score:
                best_score = maj_score
                best_key = f"{PITCH_CLASSES[i]} Major"
                
            # Minor correlation
            min_score = float(np.dot(rotated, min_prof))
            if min_score > best_score:
                best_score = min_score
                best_key = f"{PITCH_CLASSES[i]} Minor"
                
        return best_key
    except Exception as e:
        print(f"Key detection warning: {e}")
        return "C Major"


def transcribe_audio(audio_path, output_dir=None, min_note_dur=0.08, max_polyphony=5, mode="polyphonic"):
    """
    Main transcription pipeline:
    - Loads audio (MP3, WAV, FLAC, OGG, etc.)
    - Analyzes tempo (BPM) and beat timestamps
    - Detects key signature
    - Transcribes notes (pitch, start, duration, velocity)
    - Generates MIDI (.mid) and MusicXML (.musicxml) files
    """
    if not output_dir:
        output_dir = os.path.dirname(os.path.abspath(audio_path))
    os.makedirs(output_dir, exist_ok=True)
    
    # Load audio at 22050 Hz mono
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    
    if duration <= 0:
        raise ValueError("Audio file is empty or has 0 duration.")
        
    # 1. Detect Tempo & Beats
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, '__len__'):
        bpm = float(tempo[0]) if len(tempo) > 0 else 120.0
    else:
        bpm = float(tempo)
    bpm = round(bpm, 1)
    if bpm < 40 or bpm > 240:
        bpm = 120.0
        
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    
    # 2. Detect Musical Key
    key_name = detect_key(y, sr)
    
    # 3. Detect Notes
    notes = []
    hop_length = 512
    
    if mode == "melody":
        # Monophonic pYIN transcription
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr,
            hop_length=hop_length
        )
        times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
        
        current_pitch = None
        start_time = 0.0
        
        for t, f, v in zip(times, f0, voiced_flag):
            if v and not np.isnan(f) and f > 0:
                midi_p = int(round(librosa.hz_to_midi(f)))
                midi_p = max(24, min(108, midi_p))
                
                if current_pitch is None:
                    current_pitch = midi_p
                    start_time = float(t)
                elif current_pitch != midi_p:
                    dur = float(t - start_time)
                    if dur >= min_note_dur:
                        notes.append({
                            "pitch": current_pitch,
                            "name": midi_to_note_name(current_pitch),
                            "start": round(start_time, 3),
                            "duration": round(dur, 3),
                            "velocity": 0.85
                        })
                    current_pitch = midi_p
                    start_time = float(t)
            else:
                if current_pitch is not None:
                    dur = float(t - start_time)
                    if dur >= min_note_dur:
                        notes.append({
                            "pitch": current_pitch,
                            "name": midi_to_note_name(current_pitch),
                            "start": round(start_time, 3),
                            "duration": round(dur, 3),
                            "velocity": 0.85
                        })
                    current_pitch = None
                    
        if current_pitch is not None:
            dur = float(times[-1] - start_time)
            if dur >= min_note_dur:
                notes.append({
                    "pitch": current_pitch,
                    "name": midi_to_note_name(current_pitch),
                    "start": round(start_time, 3),
                    "duration": round(dur, 3),
                    "velocity": 0.85
                })
    else:
        # Polyphonic CQT + Onset Peak Tracking
        # Piano range: C2 (MIDI 36) to C7 (MIDI 96) -> 61 semitones
        fmin = librosa.note_to_hz('C2')  # ~65.4 Hz
        n_bins = 64  # C2 (36) to D#7 (99)
        bins_per_octave = 12
        base_midi = 36
        
        # Constant-Q Transform
        C = np.abs(librosa.cqt(
            y, sr=sr, hop_length=hop_length, fmin=fmin,
            n_bins=n_bins, bins_per_octave=bins_per_octave
        ))
        
        # Onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env, sr=sr, hop_length=hop_length,
            backtrack=True, delta=0.15
        )
        
        # Ensure frame 0 and end frame are covered
        total_frames = C.shape[1]
        all_onsets = sorted(list(set([0] + list(onset_frames) + [total_frames - 1])))
        
        # Dynamic thresholding based on average magnitude
        global_median = np.median(C)
        global_max = np.max(C) if np.max(C) > 0 else 1.0
        threshold = max(global_median * 2.2, global_max * 0.08)
        
        for idx in range(len(all_onsets) - 1):
            f_start = all_onsets[idx]
            f_end = all_onsets[idx + 1]
            if f_end <= f_start:
                continue
                
            t_start = float(librosa.frames_to_time(f_start, sr=sr, hop_length=hop_length))
            t_end = float(librosa.frames_to_time(f_end, sr=sr, hop_length=hop_length))
            dur = t_end - t_start
            if dur < min_note_dur:
                continue
                
            # Average spectral energy across onset window
            segment = C[:, f_start:min(f_start + 4, f_end)]
            spectrum = np.mean(segment, axis=1)
            
            # Find local peaks
            peaks = []
            for b in range(1, n_bins - 1):
                if spectrum[b] > threshold and spectrum[b] > spectrum[b - 1] and spectrum[b] > spectrum[b + 1]:
                    peaks.append((b, spectrum[b]))
                    
            # Sort peaks by energy descending, limit to max_polyphony
            peaks.sort(key=lambda x: x[1], reverse=True)
            selected_peaks = peaks[:max_polyphony]
            
            # Harmonic filtering: suppress obvious octaves if fundamental is much stronger
            filtered_peaks = []
            for b, mag in selected_peaks:
                is_overtone = False
                for fb, fmag in filtered_peaks:
                    # An octave is 12 bins away
                    if (b - fb) % 12 == 0 and b > fb and mag < fmag * 0.65:
                        is_overtone = True
                        break
                if not is_overtone:
                    filtered_peaks.append((b, mag))
                    
            for b, mag in filtered_peaks:
                midi_pitch = base_midi + b
                rel_vel = float(min(1.0, max(0.4, mag / global_max)))
                notes.append({
                    "pitch": midi_pitch,
                    "name": midi_to_note_name(midi_pitch),
                    "start": round(t_start, 3),
                    "duration": round(dur, 3),
                    "velocity": round(rel_vel, 2)
                })

    # Sort notes chronologically
    notes.sort(key=lambda n: (n["start"], n["pitch"]))
    
    # Deduplicate notes starting almost at the same time with identical pitch
    cleaned_notes = []
    for n in notes:
        if cleaned_notes:
            prev = cleaned_notes[-1]
            if prev["pitch"] == n["pitch"] and abs(prev["start"] - n["start"]) < 0.05:
                # Extend duration of previous note
                prev["duration"] = max(prev["duration"], round(n["start"] + n["duration"] - prev["start"], 3))
                continue
        cleaned_notes.append(n)
    notes = cleaned_notes
    
    # 4. Generate Output Files
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    midi_filename = f"{base_name}_transcribed.mid"
    musicxml_filename = f"{base_name}_sheet.musicxml"
    
    midi_path = os.path.join(output_dir, midi_filename)
    musicxml_path = os.path.join(output_dir, musicxml_filename)
    
    create_midi_file(notes, tempo_bpm=bpm, time_signature=(4, 4), output_path=midi_path)
    create_musicxml(notes, tempo_bpm=bpm, key_name=key_name, time_signature=(4, 4), output_path=musicxml_path)
    
    return {
        "bpm": bpm,
        "tempo": bpm,
        "key": key_name,
        "duration": round(duration, 2),
        "beat_times": [round(bt, 3) for bt in beat_times],
        "notes_count": len(notes),
        "notes": notes,
        "midi_file": midi_filename,
        "musicxml_file": musicxml_filename,
        "audio_file": os.path.basename(audio_path)
    }
