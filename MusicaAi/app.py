from flask import Flask, render_template, request, jsonify
import librosa
import numpy as np
import os
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================================================
# HOME
# ==========================================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================================
# TRANSCRIBE PAGE
# ==========================================================

@app.route("/transcribe")
def transcribe_page():
    return render_template("transcribe.html")


# ==========================================================
# AUDIO TRANSCRIPTION API
# ==========================================================

@app.route("/api/transcribe", methods=["POST"])
def transcribe():

    # ------------------------------------------------------
    # CHECK FILE
    # ------------------------------------------------------

    if "audio" not in request.files:
        return jsonify({
            "error": "No audio file uploaded"
        }), 400

    audio_file = request.files["audio"]

    if audio_file.filename == "":
        return jsonify({
            "error": "No file selected"
        }), 400

    # ------------------------------------------------------
    # SAVE TEMPORARY FILE
    # ------------------------------------------------------

    filename = str(uuid.uuid4()) + ".wav"

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    audio_file.save(filepath)

    try:

        # ==================================================
        # LOAD AUDIO
        # ==================================================

        y, sr = librosa.load(
            filepath,
            sr=None,
            mono=True
        )

        # Remove silence at beginning/end
        y, _ = librosa.effects.trim(
            y,
            top_db=35
        )

        if len(y) == 0:
            return jsonify({
                "error": "The audio file appears to be empty."
            }), 400


        # ==================================================
        # 1. BPM DETECTION
        # ==================================================

        onset_envelope = librosa.onset.onset_strength(
            y=y,
            sr=sr
        )

        tempo, beat_frames = librosa.beat.beat_track(
            y=y,
            sr=sr,
            onset_envelope=onset_envelope
        )

        tempo = np.asarray(
            tempo
        ).flatten()

        if len(tempo) > 0:
            bpm = float(tempo[0])
        else:
            bpm = 120.0

        # Keep BPM within a sensible range
        while bpm < 60:
            bpm *= 2

        while bpm > 200:
            bpm /= 2

        bpm = round(
            bpm,
            1
        )


        # ==================================================
        # 2. PITCH DETECTION
        # ==================================================

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


        # ==================================================
        # 3. CONVERT FREQUENCY → MIDI
        # ==================================================

        midi = np.full(
            len(f0),
            np.nan
        )

        valid = (
            voiced_flag
            & ~np.isnan(f0)
            & (voiced_prob >= 0.60)
        )

        midi[valid] = np.rint(
            librosa.hz_to_midi(
                f0[valid]
            )
        )


        # ==================================================
        # 4. SMOOTH PITCH
        # ==================================================

        smoothed = midi.copy()

        window_size = 7

        half_window = window_size // 2

        for i in range(len(midi)):

            start = max(
                0,
                i - half_window
            )

            end = min(
                len(midi),
                i + half_window + 1
            )

            window_values = midi[start:end]

            valid_values = window_values[
                ~np.isnan(window_values)
            ]

            if len(valid_values) >= 3:

                smoothed[i] = np.median(
                    valid_values
                )


        # ==================================================
        # 5. CREATE NOTE EVENTS
        #
        # IMPORTANT:
        # We keep repeated notes as separate events.
        # ==================================================

        note_events = []

        current_midi = None
        start_frame = None

        for frame_index, value in enumerate(smoothed):

            # ------------------------------------------------
            # SILENCE
            # ------------------------------------------------

            if np.isnan(value):

                if current_midi is not None:

                    note_events.append({
                        "start_frame": start_frame,
                        "end_frame": frame_index - 1,
                        "midi": current_midi
                    })

                    current_midi = None
                    start_frame = None

                continue


            current_note = int(
                round(value)
            )


            # ------------------------------------------------
            # FIRST NOTE
            # ------------------------------------------------

            if current_midi is None:

                current_midi = current_note

                start_frame = frame_index

                continue


            # ------------------------------------------------
            # PITCH CHANGE
            # ------------------------------------------------

            if current_note != current_midi:

                note_events.append({
                    "start_frame": start_frame,
                    "end_frame": frame_index - 1,
                    "midi": current_midi
                })

                current_midi = current_note

                start_frame = frame_index


        # ==================================================
        # FINISH LAST NOTE
        # ==================================================

        if current_midi is not None:

            note_events.append({
                "start_frame": start_frame,
                "end_frame": len(smoothed) - 1,
                "midi": current_midi
            })


        # ==================================================
        # 6. CONVERT FRAMES → TIME
        # ==================================================

        processed_events = []

        for event in note_events:

            frame_count = (
                event["end_frame"]
                - event["start_frame"]
                + 1
            )

            duration_seconds = (
                frame_count
                * hop_length
                / sr
            )

            start_seconds = (
                event["start_frame"]
                * hop_length
                / sr
            )

            # Ignore tiny pitch glitches
            if duration_seconds < 0.08:
                continue

            processed_events.append({
                "midi": int(event["midi"]),

                "start": round(
                    float(start_seconds),
                    3
                ),

                "duration": round(
                    float(duration_seconds),
                    3
                )
            })


        # ==================================================
        # 7. REMOVE VERY CLOSE DUPLICATE EVENTS
        #
        # This does NOT merge normal repeated notes.
        # It only removes accidental duplicate detections
        # occurring almost at exactly the same time.
        # ==================================================

        cleaned_events = []

        for event in processed_events:

            if not cleaned_events:

                cleaned_events.append(
                    event
                )

                continue

            previous = cleaned_events[-1]

            same_note = (
                previous["midi"]
                == event["midi"]
            )

            almost_same_time = (
                abs(
                    previous["start"]
                    - event["start"]
                )
                < 0.035
            )

            if same_note and almost_same_time:

                previous["duration"] = max(
                    previous["duration"],
                    event["duration"]
                )

            else:

                cleaned_events.append(
                    event
                )


        # ==================================================
        # 8. LIMIT EVENTS
        # ==================================================

        cleaned_events = cleaned_events[:128]


        # ==================================================
        # 9. CONVERT MIDI → NOTE NAMES
        # ==================================================

        detected_notes = []

        durations = []

        beat_durations = []

        playback_events = []

        seconds_per_beat = 60.0 / bpm


        for event in cleaned_events:

            midi_note = event["midi"]

            note_name = librosa.midi_to_note(
                midi_note,
                octave=True
            )

            duration = float(
                event["duration"]
            )

            start = float(
                event["start"]
            )

            beats = (
                duration
                / seconds_per_beat
            )

            detected_notes.append(
                note_name
            )

            durations.append(
                round(
                    duration,
                    3
                )
            )

            beat_durations.append(
                round(
                    beats,
                    3
                )
            )

            playback_events.append({

                "note": note_name,

                "midi": int(
                    midi_note
                ),

                "start": round(
                    start,
                    3
                ),

                "duration": round(
                    duration,
                    3
                ),

                "beats": round(
                    beats,
                    3
                )
            })


        # ==================================================
        # 10. CREATE SHEET MUSIC
        # ==================================================

        abc = create_abc(
            playback_events,
            bpm
        )


        # ==================================================
        # DEBUG
        # ==================================================

        print()
        print("======================================")
        print("MUSICA TRANSCRIPTION")
        print("======================================")

        print("BPM:", bpm)

        print("Notes:")
        print(detected_notes)

        print("Durations:")
        print(durations)

        print("Events:")
        print(playback_events)

        print("======================================")
        print()


        # ==================================================
        # RETURN DATA
        # ==================================================

        return jsonify({

            "notes": detected_notes,

            "durations": durations,

            "beat_durations": beat_durations,

            "bpm": bpm,

            "events": playback_events,

            "abc": abc

        })


    # ======================================================
    # ERROR
    # ======================================================

    except Exception as e:

        print()
        print("MUSICA ERROR:")
        print(e)
        print()

        return jsonify({
            "error": str(e)
        }), 500


    # ======================================================
    # DELETE TEMPORARY FILE
    # ======================================================

    finally:

        if os.path.exists(filepath):

            os.remove(filepath)


# ==========================================================
# CREATE ABC SHEET MUSIC
# ==========================================================

def create_abc(events, bpm):

    if not events:

        return f"""X:1
T:MUSICA Transcription
M:4/4
L:1/4
Q:1/4={round(bpm)}
K:C clef=treble
z4
"""


    abc_notes = []

    octaves = []


    # ------------------------------------------------------
    # Convert each detected event
    # ------------------------------------------------------

    for event in events:

        note = event["note"]

        beats = event["beats"]

        pitch_part = note[:-1]

        octave = int(
            note[-1]
        )

        octaves.append(
            octave
        )


        # --------------------------------------------------
        # Accidentals
        # --------------------------------------------------

        if "#" in pitch_part:

            accidental = "^"

            letter = pitch_part.replace(
                "#",
                ""
            )

        elif "b" in pitch_part:

            accidental = "_"

            letter = pitch_part.replace(
                "b",
                ""
            )

        else:

            accidental = ""

            letter = pitch_part


        # --------------------------------------------------
        # Scientific pitch → ABC
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

            abc_pitch = (
                letter.lower()
                + "'"
            )

        else:

            abc_pitch = letter


        # --------------------------------------------------
        # Quantize duration
        #
        # ABC uses:
        #
        # 0.25 = sixteenth
        # 0.5  = eighth
        # 1    = quarter
        # 2    = half
        # 4    = whole
        # --------------------------------------------------

        possible_lengths = [
            0.25,
            0.5,
            0.75,
            1.0,
            1.5,
            2.0,
            3.0,
            4.0
        ]

        closest_length = min(
            possible_lengths,
            key=lambda x: abs(
                x - beats
            )
        )


        # --------------------------------------------------
        # ABC duration
        # --------------------------------------------------

        if closest_length == 0.25:

            duration_text = "/4"

        elif closest_length == 0.5:

            duration_text = "/2"

        elif closest_length == 0.75:

            duration_text = "3/4"

        elif closest_length == 1.0:

            duration_text = ""

        elif closest_length == 1.5:

            duration_text = "3/2"

        elif closest_length == 2.0:

            duration_text = "2"

        elif closest_length == 3.0:

            duration_text = "3"

        elif closest_length == 4.0:

            duration_text = "4"

        else:

            duration_text = ""


        abc_notes.append(
            accidental
            + abc_pitch
            + duration_text
        )


    # ======================================================
    # CHOOSE CLEF
    # ======================================================

    average_octave = (
        sum(octaves)
        / len(octaves)
    )

    if average_octave < 3.5:

        clef = "bass"

    else:

        clef = "treble"


    # ======================================================
    # CREATE MEASURES
    # ======================================================

    measures = []

    current_measure = []

    current_beats = 0.0


    for index, event in enumerate(events):

        beats = event["beats"]

        # Keep measures approximately 4 beats
        if (
            current_measure
            and current_beats + beats > 4.0
        ):

            measures.append(
                " ".join(
                    current_measure
                )
            )

            current_measure = []

            current_beats = 0.0


        current_measure.append(
            abc_notes[index]
        )

        current_beats += min(
            beats,
            4.0
        )


        if current_beats >= 4.0:

            measures.append(
                " ".join(
                    current_measure
                )
            )

            current_measure = []

            current_beats = 0.0


    if current_measure:

        measures.append(
            " ".join(
                current_measure
            )
        )


    abc_music = " | ".join(
        measures
    )


    # ======================================================
    # FINAL ABC
    # ======================================================

    abc = f"""X:1
T:MUSICA Transcription
M:4/4
L:1/4
Q:1/4={round(bpm)}
K:C clef={clef}
{abc_music} |
"""


    return abc


# ==========================================================
# START FLASK
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )