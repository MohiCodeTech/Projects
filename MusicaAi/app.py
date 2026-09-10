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

    # Give the uploaded file a unique name
    filename = str(uuid.uuid4()) + ".wav"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    audio_file.save(filepath)

    try:
        # Load audio
        y, sr = librosa.load(filepath, sr=None, mono=True)

        # Detect pitch
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C3"),
            fmax=librosa.note_to_hz("C6")
        )

        notes = []

        for frequency, voiced in zip(f0, voiced_flag):

            if voiced and not np.isnan(frequency):

                midi_note = int(round(librosa.hz_to_midi(frequency)))

                # Convert MIDI to note name
                note_name = librosa.midi_to_note(
                    midi_note,
                    octave=True
                )

                if not notes or notes[-1] != note_name:
                    notes.append(note_name)

        # Remove duplicate consecutive notes
        clean_notes = []

        for note in notes:
            if not clean_notes or clean_notes[-1] != note:
                clean_notes.append(note)

        # Limit for prototype
        clean_notes = clean_notes[:32]

        # Create ABC notation
        abc = create_abc(clean_notes)

        return jsonify({
            "notes": clean_notes,
            "abc": abc
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        if os.path.exists(filepath):
            os.remove(filepath)


def create_abc(notes):

    if not notes:
        return "X:1\nT:No notes detected\nM:4/4\nL:1/4\nK:C\nz4"

    abc_notes = []

    for note in notes:

        # Convert note format such as C4 into ABC
        letter = note[0]
        octave = int(note[-1])

        # ABC middle octave is C
        if octave == 4:
            abc_note = letter

        elif octave == 5:
            abc_note = letter.lower()

        elif octave == 3:
            abc_note = letter + ","

        elif octave == 6:
            abc_note = letter.lower() + "'"

        else:
            abc_note = letter

        abc_notes.append(abc_note)

    # Put four notes per measure
    music = []

    for i in range(0, len(abc_notes), 4):

        measure = abc_notes[i:i + 4]

        music.append(" ".join(measure))

    abc_music = " | ".join(music)

    return f"""X:1
T:MUSICA Transcription
M:4/4
L:1/4
K:C
{abc_music} |
"""


if __name__ == "__main__":
    app.run(debug=True)