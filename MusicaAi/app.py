# # from flask import Flask, render_template, request, jsonify
# # import librosa
# # import numpy as np
# # import os
# # import uuid
# # from scipy.stats import mode

# # app = Flask(__name__)

# # UPLOAD_FOLDER = "uploads"
# # os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# # @app.route("/")
# # def home():
# #     return render_template("index.html")


# # @app.route("/transcribe")
# # def transcribe_page():
# #     return render_template("transcribe.html")


# # @app.route("/api/transcribe", methods=["POST"])
# # def transcribe():

# #     if "audio" not in request.files:
# #         return jsonify({"error": "No audio file uploaded"}), 400

# #     audio_file = request.files["audio"]

# #     if audio_file.filename == "":
# #         return jsonify({"error": "No file selected"}), 400

# #     filename = str(uuid.uuid4()) + ".wav"
# #     filepath = os.path.join(UPLOAD_FOLDER, filename)
# #     audio_file.save(filepath)

# #     try:
# #         # Load audio
# #         y, sr = librosa.load(filepath, sr=None, mono=True)

# #         # Detect pitch with pYIN
# #         f0, voiced_flag, voiced_prob = librosa.pyin(
# #             y,
# #             fmin=librosa.note_to_hz("C2"),
# #             fmax=librosa.note_to_hz("C6")
# #         )

# #         midi_series = []
# #         for frequency, voiced in zip(f0, voiced_flag):
# #             if voiced and not np.isnan(frequency):
# #                 midi_series.append(int(round(librosa.hz_to_midi(frequency))))
# #             else:
# #                 midi_series.append(None)

# #         # 1. Smooth jitter: chunk frame samples (~150ms window) and pick dominant pitch
# #         chunk_size = 15  # Adjust based on pitch stability
# #         smoothed_midi = []

# #         for i in range(0, len(midi_series), chunk_size):
# #             chunk = [m for m in midi_series[i:i + chunk_size] if m is not None]
# #             if chunk:
# #                 # Mode gives most frequent pitch in window
# #                 most_common_pitch = mode(chunk, keepdims=False).mode
# #                 smoothed_midi.append(most_common_pitch)

# #         # Convert MIDI to note names
# #         notes = [librosa.midi_to_note(m, octave=True) for m in smoothed_midi]

# #         # 2. Deduplicate consecutive identical notes
# #         clean_notes = []
# #         for note in notes:
# #             if not clean_notes or clean_notes[-1] != note:
# #                 clean_notes.append(note)

# #         clean_notes = clean_notes[:32]

# #         # 3. Create ABC notation with correct accidentals & clef
# #         abc = create_abc(clean_notes)

# #         return jsonify({
# #             "notes": clean_notes,
# #             "abc": abc
# #         })

# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500

# #     finally:
# #         if os.path.exists(filepath):
# #             os.remove(filepath)


# # def create_abc(notes):
# #     if not notes:
# #         return "X:1\nT:No notes detected\nM:4/4\nL:1/4\nK:C clef=bass\nz4"

# #     abc_notes = []
    
# #     # Track average octave to automatically pick best staff clef
# #     octaves = []

# #     for note in notes:
# #         # Parse note elements including accidentals (e.g. D#3, Eb3, C4)
# #         pitch_part = note[:-1]  # 'D#', 'C', 'Eb'
# #         octave = int(note[-1])
# #         octaves.append(octave)

# #         # Map accidentals to ABC syntax
# #         abc_accidental = ""
# #         if "#" in pitch_part:
# #             abc_accidental = "^"
# #             letter = pitch_part.replace("#", "")
# #         elif "b" in pitch_part:
# #             abc_accidental = "_"
# #             letter = pitch_part.replace("b", "")
# #         else:
# #             letter = pitch_part

# #         # Map octaves to ABC syntax
# #         # if octave == 2:
# #         #     abc_pitch = letter + ",,"
# #         # elif octave == 3:
# #         #     abc_pitch = letter + ","
# #         # elif octave == 4:
# #         #     abc_pitch = letter
# #         # elif octave == 5:
# #         #     abc_pitch = letter.lower()
# #         # elif octave == 6:
# #         #     abc_pitch = letter.lower() + "'"
# #         # else:
# #         #     abc_pitch = letter
# #         # Fixed octave mapping relative to scientific pitch notation (C4 = Middle C)
# #         if octave == 2:
# #             abc_pitch = letter + ",,"  # C,, D,, E,,
# #         elif octave == 3:
# #             abc_pitch = letter + ","   # C, D, E, (Fits cleanly inside Bass Clef)
# #         elif octave == 4:
# #             abc_pitch = letter         # C D E
# #         elif octave == 5:
# #             abc_pitch = letter.lower() # c d e

# #         abc_notes.append(f"{abc_accidental}{abc_pitch}")

# #     # Select clef automatically (Bass clef for <= octave 3)
# #     avg_octave = sum(octaves) / len(octaves) if octaves else 4
# #     clef_type = "bass" if avg_octave < 3.8 else "treble"

# #     # Format 4 notes per bar
# #     music = []
# #     for i in range(0, len(abc_notes), 4):
# #         measure = abc_notes[i:i + 4]
# #         music.append(" ".join(measure))

# #     abc_music = " | ".join(music)

# #     return f"""X:1
# # T:MUSICA Transcription
# # M:4/4
# # L:1/4
# # K:C clef={clef_type}
# # {abc_music} |
# # """


# # if __name__ == "__main__":
# #     app.run(debug=True)
# from flask import Flask, render_template, request, jsonify
# import librosa
# import numpy as np
# import os
# import uuid

# app = Flask(__name__)

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# @app.route("/")
# def home():
#     return render_template("index.html")


# @app.route("/transcribe")
# def transcribe_page():
#     return render_template("transcribe.html")


# @app.route("/api/transcribe", methods=["POST"])
# def transcribe():
#     if "audio" not in request.files:
#         return jsonify({"error": "No audio file uploaded"}), 400

#     audio_file = request.files["audio"]
#     if audio_file.filename == "":
#         return jsonify({"error": "No file selected"}), 400

#     filename = str(uuid.uuid4()) + ".wav"
#     filepath = os.path.join(UPLOAD_FOLDER, filename)
#     audio_file.save(filepath)

#     try:
#         # Load audio
#         y, sr = librosa.load(filepath, sr=None, mono=True)

#         # 1. Extract Chroma CQT features (12 pitch classes)
#         chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
        
#         # 2. Extract fundamental frequency to know the exact octave
#         f0, voiced_flag, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C3"), fmax=librosa.note_to_hz("C5"))

#         note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
#         detected_notes = []

#         # Step through time frames (~150ms per step)
#         step = 12 
#         for i in range(0, chroma.shape[1], step):
#             frame_chroma = np.mean(chroma[:, i:i + step], axis=1)
            
#             # Check energy threshold (ignore silence)
#             if np.max(frame_chroma) > 0.4:
#                 pitch_class_idx = np.argmax(frame_chroma)
#                 pitch_letter = note_names[pitch_class_idx]

#                 # Find octave from f0
#                 f0_chunk = [f for f, v in zip(f0[i:i + step], voiced_flag[i:i + step]) if v and not np.isnan(f)]
#                 if f0_chunk:
#                     med_f = np.median(f0_chunk)
#                     octave = int(librosa.hz_to_midi(med_f) // 12) - 1
#                 else:
#                     octave = 3  # Default fallback for this register

#                 full_note = f"{pitch_letter}{octave}"

#                 if not detected_notes or detected_notes[-1] != full_note:
#                     detected_notes.append(full_note)

#         # Create ABC sheet music
#         abc = create_abc(detected_notes)

#         return jsonify({
#             "notes": detected_notes,
#             "abc": abc
#         })

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

#     finally:
#         if os.path.exists(filepath):
#             os.remove(filepath)

# def create_abc(notes):
#     if not notes:
#         return "X:1\nT:No notes detected\nM:4/4\nL:1/8\nK:C clef=bass\nz8"

#     abc_notes = []
#     octaves = []

#     for note in notes:
#         # Extract pitch name and octave number
#         pitch_part = note[:-1]
#         octave = int(note[-1])
#         octaves.append(octave)

#         # Map sharp/flat accidentals to ABC syntax
#         if "#" in pitch_part:
#             abc_acc = "^"
#             letter = pitch_part.replace("#", "")
#         elif "b" in pitch_part:
#             abc_acc = "_"
#             letter = pitch_part.replace("b", "")
#         else:
#             abc_acc = ""
#             letter = pitch_part

#         # Accurate Scientific Octave to ABC Conversion
#         if octave == 2:
#             abc_pitch = letter + ",,"
#         elif octave == 3:
#             abc_pitch = letter + ","   # Lower register (Bass Clef)
#         elif octave == 4:
#             abc_pitch = letter         # Middle register (Treble/Bass ledger)
#         elif octave == 5:
#             abc_pitch = letter.lower() # High register
#         else:
#             abc_pitch = letter

#         abc_notes.append(f"{abc_acc}{abc_pitch}")

#     # Set clef depending on detected average octave
#     avg_octave = sum(octaves) / len(octaves) if octaves else 3
#     clef_type = "bass" if avg_octave < 3.8 else "treble"

#     # Group 4 notes per bar line
#     measures = []
#     for i in range(0, len(abc_notes), 4):
#         measures.append(" ".join(abc_notes[i:i + 4]))

#     abc_music = " | ".join(measures)

#     return f"""X:1
# T:MUSICA Transcription
# M:4/4
# L:1/8
# K:C clef={clef_type}
# {abc_music} |
# """


# if __name__ == "__main__":
#     app.run(debug=True)
from flask import Flask, render_template, request, jsonify
import librosa
import numpy as np
import os
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/transcribe")
def transcribe_page():
    return render_template("transcribe.html")


@app.route("/api/transcribe", methods=["POST"])
def transcribe():

    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files["audio"]

    if audio_file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Save uploaded file
    filename = str(uuid.uuid4()) + ".wav"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(filepath)

    try:
        # --------------------------------------------------
        # LOAD AUDIO
        # --------------------------------------------------

        y, sr = librosa.load(
            filepath,
            sr=None,
            mono=True
        )

        # Remove very quiet background noise
        y, _ = librosa.effects.trim(
            y,
            top_db=35
        )

        # --------------------------------------------------
        # PITCH DETECTION
        # --------------------------------------------------

        hop_length = 256

        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            sr=sr,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C6"),
            frame_length=2048,
            hop_length=hop_length,
            fill_na=np.nan
        )

        # Convert frequencies to MIDI numbers
        midi = np.full(len(f0), np.nan)

        valid = (
            voiced_flag
            & ~np.isnan(f0)
            & (voiced_prob > 0.60)
        )

        midi[valid] = np.rint(
            librosa.hz_to_midi(f0[valid])
        )

        # --------------------------------------------------
        # SMOOTH PITCH
        # --------------------------------------------------

        # Remove very short pitch glitches.
        # We use a small median filter manually so
        # the program doesn't depend on another library.

        smoothed = midi.copy()

        window = 7
        half = window // 2

        for i in range(len(midi)):

            start = max(0, i - half)
            end = min(len(midi), i + half + 1)

            values = midi[start:end]
            values = values[~np.isnan(values)]

            if len(values) >= 3:
                smoothed[i] = np.median(values)

        # --------------------------------------------------
        # TURN PITCH FRAMES INTO NOTES
        # --------------------------------------------------

        runs = []

        current_note = None
        start_frame = None

        for i, value in enumerate(smoothed):

            if np.isnan(value):

                if current_note is not None:
                    runs.append(
                        (
                            start_frame,
                            i - 1,
                            current_note
                        )
                    )

                    current_note = None
                    start_frame = None

                continue

            note = int(round(value))

            if current_note is None:

                current_note = note
                start_frame = i

            elif note != current_note:

                runs.append(
                    (
                        start_frame,
                        i - 1,
                        current_note
                    )
                )

                current_note = note
                start_frame = i

        # Finish final note
        if current_note is not None:

            runs.append(
                (
                    start_frame,
                    len(smoothed) - 1,
                    current_note
                )
            )

        # --------------------------------------------------
        # REMOVE VERY SHORT GLITCHES
        # --------------------------------------------------

        clean_runs = []

        for start, end, note in runs:

            duration = (
                (end - start + 1)
                * hop_length
                / sr
            )

            # Ignore tiny pitch jumps
            if duration >= 0.08:

                clean_runs.append(
                    (start, end, note)
                )

        # --------------------------------------------------
        # MERGE IDENTICAL NEIGHBOURING NOTES
        # --------------------------------------------------

        merged_runs = []

        for start, end, note in clean_runs:

            if merged_runs and merged_runs[-1][2] == note:

                old_start, old_end, old_note = merged_runs[-1]

                merged_runs[-1] = (
                    old_start,
                    end,
                    old_note
                )

            else:

                merged_runs.append(
                    (start, end, note)
                )

        # --------------------------------------------------
        # LIMIT PROTOTYPE OUTPUT
        # --------------------------------------------------

        merged_runs = merged_runs[:32]

        # --------------------------------------------------
        # CONVERT MIDI TO NOTE NAMES
        # --------------------------------------------------

        detected_notes = []

        for start, end, midi_note in merged_runs:

            note_name = librosa.midi_to_note(
                midi_note,
                octave=True
            )

            detected_notes.append(note_name)

        # --------------------------------------------------
        # CREATE SHEET MUSIC
        # --------------------------------------------------

        abc = create_abc(detected_notes)

        # Send durations too
        durations = []

        for start, end, midi_note in merged_runs:

            duration = (
                (end - start + 1)
                * hop_length
                / sr
            )

            durations.append(
                round(duration, 2)
            )

        return jsonify({
            "notes": detected_notes,
            "durations": durations,
            "abc": abc
        })

    except Exception as e:

        print("TRANSCRIPTION ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        if os.path.exists(filepath):
            os.remove(filepath)


# ==========================================================
# CREATE ABC SHEET MUSIC
# ==========================================================

def create_abc(notes):

    if not notes:

        return """X:1
T:MUSICA Transcription
M:4/4
L:1/4
K:C clef=treble
z4
"""

    abc_notes = []
    octaves = []

    for note in notes:

        # Examples:
        # C4
        # A#3
        # D#4

        pitch_part = note[:-1]
        octave = int(note[-1])

        octaves.append(octave)

        # --------------------------------------------------
        # ACCIDENTALS
        # --------------------------------------------------

        if "#" in pitch_part:

            accidental = "^"
            letter = pitch_part.replace("#", "")

        elif "b" in pitch_part:

            accidental = "_"
            letter = pitch_part.replace("b", "")

        else:

            accidental = ""
            letter = pitch_part

        # --------------------------------------------------
        # ABC OCTAVE MAPPING
        #
        # Scientific:
        # C3 = C,
        # C4 = C
        # C5 = c
        # C6 = c'
        # --------------------------------------------------

        if octave == 2:

            abc_pitch = letter + ",,"

        elif octave == 3:

            abc_pitch = letter + ","

        elif octave == 4:

            abc_pitch = letter

        elif octave == 5:

            abc_pitch = letter.lower()

        elif octave == 6:

            abc_pitch = letter.lower() + "'"

        else:

            abc_pitch = letter

        abc_notes.append(
            accidental + abc_pitch
        )

    # --------------------------------------------------
    # CHOOSE CLEF
    # --------------------------------------------------

    average_octave = (
        sum(octaves) / len(octaves)
        if octaves
        else 4
    )

    if average_octave < 3.5:
        clef = "bass"
    else:
        clef = "treble"

    # --------------------------------------------------
    # CREATE MEASURES
    # --------------------------------------------------

    measures = []

    for i in range(0, len(abc_notes), 4):

        measure = abc_notes[i:i + 4]

        measures.append(
            " ".join(measure)
        )

    abc_music = " | ".join(measures)

    # --------------------------------------------------
    # FINAL ABC
    # --------------------------------------------------

    return f"""X:1
T:MUSICA Transcription
M:4/4
L:1/4
K:C clef={clef}
{abc_music} |
"""


if __name__ == "__main__":
    app.run(debug=True)