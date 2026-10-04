"""
Musica AI Vibe - Main Flask Application
Web server providing music upload, BPM/tempo detection, sheet music rendering,
interactive playable piano roll, and MIDI/MusicXML export.
"""

import os
import shutil
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from werkzeug.utils import secure_filename
from transcriber import transcribe_audio

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max upload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SAMPLES_DIR = os.path.join(BASE_DIR, "static", "samples")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac', 'm4a', 'aac', 'aiff', 'wma'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided in request."}), 400
        
    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    mode = request.form.get("mode", "polyphonic")
    if mode not in ["polyphonic", "melody"]:
        mode = "polyphonic"

    # Generate safe unique filename
    original_name = secure_filename(file.filename)
    unique_id = uuid.uuid4().hex[:8]
    ext = original_name.rsplit('.', 1)[1].lower()
    save_filename = f"{unique_id}_{original_name}"
    save_path = os.path.join(UPLOAD_DIR, save_filename)
    
    file.save(save_path)
    
    try:
        result = transcribe_audio(save_path, output_dir=UPLOAD_DIR, mode=mode)
        
        # Read MusicXML content directly for instant frontend rendering
        musicxml_path = os.path.join(UPLOAD_DIR, result["musicxml_file"])
        with open(musicxml_path, "r", encoding="utf-8") as f:
            musicxml_content = f.read()
            
        result["status"] = "success"
        result["musicxml_content"] = musicxml_content
        result["audio_url"] = f"/uploads/{result['audio_file']}"
        result["midi_url"] = f"/api/download/midi/{result['midi_file']}"
        result["musicxml_url"] = f"/api/download/musicxml/{result['musicxml_file']}"
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Transcription error: {str(e)}"}), 500


@app.route("/api/analyze-sample", methods=["POST"])
def analyze_sample():
    data = request.get_json() or {}
    sample_name = data.get("sample", "sample_classical_fur_elise.wav")
    mode = data.get("mode", "polyphonic")
    
    sample_path = os.path.join(SAMPLES_DIR, sample_name)
    if not os.path.exists(sample_path):
        return jsonify({"error": f"Sample not found: {sample_name}"}), 404
        
    unique_id = uuid.uuid4().hex[:8]
    dest_filename = f"sample_{unique_id}_{sample_name}"
    dest_path = os.path.join(UPLOAD_DIR, dest_filename)
    shutil.copyfile(sample_path, dest_path)
    
    try:
        result = transcribe_audio(dest_path, output_dir=UPLOAD_DIR, mode=mode)
        
        musicxml_path = os.path.join(UPLOAD_DIR, result["musicxml_file"])
        with open(musicxml_path, "r", encoding="utf-8") as f:
            musicxml_content = f.read()
            
        result["status"] = "success"
        result["musicxml_content"] = musicxml_content
        result["audio_url"] = f"/uploads/{result['audio_file']}"
        result["midi_url"] = f"/api/download/midi/{result['midi_file']}"
        result["musicxml_url"] = f"/api/download/musicxml/{result['musicxml_file']}"
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Sample transcription error: {str(e)}"}), 500


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/api/download/midi/<filename>")
def download_midi(filename):
    safe_name = secure_filename(filename)
    path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True, download_name=safe_name, mimetype="audio/midi")


@app.route("/api/download/musicxml/<filename>")
def download_musicxml(filename):
    safe_name = secure_filename(filename)
    path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True, download_name=safe_name, mimetype="application/vnd.recordare.musicxml+xml")


if __name__ == "__main__":
    print("=" * 60)
    print("  Musica AI Vibe Server Starting...")
    print("  Open your browser at: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
