import numpy as np
import soundfile as sf
import os
from transcriber import transcribe_audio

def main():
    sr = 22050
    t = np.linspace(0, 3.0, int(sr * 3.0), endpoint=False)
    y = np.zeros_like(t)

    # Note 1: C4 (261.63Hz)
    m1 = (t >= 0.0) & (t < 1.0)
    y[m1] += 0.5 * np.sin(2 * np.pi * 261.63 * t[m1])

    # Note 2: E4 (329.63Hz)
    m2 = (t >= 1.0) & (t < 2.0)
    y[m2] += 0.5 * np.sin(2 * np.pi * 329.63 * t[m2])

    # Note 3: G4 (392.00Hz)
    m3 = (t >= 2.0) & (t < 3.0)
    y[m3] += 0.5 * np.sin(2 * np.pi * 392.00 * t[m3])

    test_wav = os.path.abspath("test_synthetic.wav")
    sf.write(test_wav, y, sr)
    
    print(f"Testing audio transcription on {test_wav}...")
    res = transcribe_audio(test_wav)
    print("SUCCESSFUL TRANSCRIPTION!")
    print(f"BPM: {res['bpm']}")
    print(f"Key: {res['key']}")
    print(f"Duration: {res['duration']}s")
    print(f"Notes Count: {res['notes_count']}")
    for n in res['notes'][:6]:
        print("  Note:", n)
    print("MIDI File:", res['midi_file'], "exists:", os.path.exists(os.path.join(os.path.dirname(test_wav), res['midi_file'])))
    print("MusicXML File:", res['musicxml_file'], "exists:", os.path.exists(os.path.join(os.path.dirname(test_wav), res['musicxml_file'])))

if __name__ == "__main__":
    main()
