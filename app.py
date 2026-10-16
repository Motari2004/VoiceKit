"""
VoiceKit — one URL, two faces.
    /              → HTML UI
    /speak         → JSON API (WAV)
    /voices        → JSON API
    /health        → JSON API
"""

import io
import re
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

UPSTREAM = "https://motari-txt2speech.hf.space"

MAX_TEXT_LENGTH  = 800
MIN_SPEED        = 0.5
MAX_SPEED        = 2.0
UPSTREAM_TIMEOUT = 15
POLL_INTERVAL    = 0.4
MAX_POLLS        = 20

VOICES = [
    "am_adam", "am_michael", "am_onyx", "am_puck", "am_echo",
    "am_eric", "am_fenrir", "am_liam", "am_santa",
    "bm_george", "bm_lewis", "bm_daniel", "bm_fable",
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "af_nova", "af_river", "af_jessica", "af_kore", "af_aoede", "af_alloy",
    "bf_emma", "bf_alice", "bf_isabella", "bf_lily",
]

app = Flask(__name__)
CORS(app)

_cache = {}
_cache_lock = threading.Lock()


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def call_upstream(text, voice, speed):
    r = requests.post(
        f"{UPSTREAM}/gradio_api/call/tts",
        json={"data": [text, voice, speed]},
        timeout=UPSTREAM_TIMEOUT,
    )
    r.raise_for_status()
    eid = r.json().get("event_id")
    if not eid:
        raise RuntimeError("No event_id")

    audio_url = None
    for _ in range(MAX_POLLS):
        r = requests.get(f"{UPSTREAM}/gradio_api/call/tts/{eid}", timeout=UPSTREAM_TIMEOUT)
        r.raise_for_status()
        match = re.search(r'https://[^"]+audio\.wav', r.text)
        if match:
            audio_url = match.group(0)
            break
        time.sleep(POLL_INTERVAL)

    if not audio_url:
        raise TimeoutError("No audio URL")

    r = requests.get(audio_url, timeout=UPSTREAM_TIMEOUT)
    r.raise_for_status()
    return r.content


def generate_speech(text, voice, speed):
    key = f"{voice}|{speed}|{text}"
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    wav = call_upstream(text, voice, speed)
    with _cache_lock:
        _cache[key] = wav
    return wav


# ---------- UI ----------
@app.route("/")
def index():
    return render_template("index.html")


# ---------- API ----------
@app.route("/health")
def health():
    return jsonify({"status": "ok", "cache_size": len(_cache)})


@app.route("/voices")
def voices():
    return jsonify({"count": len(VOICES), "voices": VOICES})


@app.route("/speak", methods=["POST", "OPTIONS"])
def speak():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data  = request.get_json() or {}
        text  = (data.get("text") or "").strip()
        voice = (data.get("voice") or "am_adam").strip()
        speed = float(data.get("speed", 1.0))

        if not text:
            return jsonify({"error": "Missing 'text'"}), 400
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({"error": f"Text too long (max {MAX_TEXT_LENGTH})"}), 400
        speed = max(MIN_SPEED, min(MAX_SPEED, speed))

        wav_bytes = generate_speech(text, voice, speed)

        return send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name=f"{voice}.wav",
        )
    except requests.Timeout:
        return jsonify({"error": "Upstream timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500