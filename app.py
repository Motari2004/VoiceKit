"""
VoiceKit — Text-to-Speech API and Web UI
Deployed on Vercel as a Python serverless function.
"""

import io
import re
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

# ---------- CONFIG ----------
SPACE_URL = "https://motari-txt2speech.hf.space"

app = Flask(__name__)
CORS(app)

_cache = {}
_cache_lock = threading.Lock()


# ---------- CORE ----------
def generate_speech(text, voice="am_adam", speed=1.0):
    key = f"{voice}|{speed}|{text}"
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    start = requests.post(
        f"{SPACE_URL}/gradio_api/call/tts",
        json={"data": [text, voice, speed]},
        timeout=15,
    )
    start.raise_for_status()
    eid = start.json().get("event_id")
    if not eid:
        raise RuntimeError("No event_id returned from Space")

    audio_url = None
    for _ in range(20):
        res = requests.get(
            f"{SPACE_URL}/gradio_api/call/tts/{eid}",
            timeout=10,
        )
        res.raise_for_status()
        raw = res.text

        match = re.search(r'https://[^"]+audio\.wav', raw)
        if match:
            audio_url = match.group(0)
            break

        time.sleep(0.4)

    if not audio_url:
        raise TimeoutError("Space did not return audio in time")

    audio = requests.get(audio_url, timeout=15)
    audio.raise_for_status()
    wav_bytes = audio.content

    with _cache_lock:
        _cache[key] = wav_bytes

    return wav_bytes


# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": time.time()})


@app.route("/voices")
def voices():
    return jsonify({
        "voices": [
            "am_adam", "am_michael", "am_onyx", "am_puck", "am_echo",
            "am_eric", "am_fenrir", "am_liam", "am_santa",
            "bm_george", "bm_lewis", "bm_daniel", "bm_fable",
            "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_nova",
            "bf_emma", "bf_alice", "bf_lily",
        ]
    })


@app.route("/speak", methods=["POST"])
def speak():
    try:
        data  = request.get_json() or {}
        text  = (data.get("text") or "").strip()
        voice = (data.get("voice") or "am_adam").strip()
        speed = float(data.get("speed", 1.0))

        if not text:
            return jsonify({"error": "Missing 'text'"}), 400
        if len(text) > 800:
            return jsonify({"error": "Text too long (max 800 chars)"}), 400
        if speed < 0.5 or speed > 2.0:
            speed = 1.0

        wav_bytes = generate_speech(text, voice, speed)

        return send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name=f"{voice}.wav",
        )
    except requests.Timeout:
        return jsonify({"error": "Space timed out — try again"}), 504
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500


# ---------- NO app.run() — VERCEL HANDLES THIS ----------