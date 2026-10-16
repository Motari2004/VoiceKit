"""
VoiceKit — Text-to-Speech API and Web UI
Deployed on Vercel as a Python serverless function.

Exposes:
    GET  /            → Web UI
    GET  /health      → health check
    GET  /voices      → list of available voices
    POST /speak       → generate speech, returns WAV
"""

import io
import re
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

# ============================================================
# CONFIG
# ============================================================
UPSTREAM = "https://motari-txt2speech.hf.space"

MAX_TEXT_LENGTH  = 800
MIN_SPEED        = 0.5
MAX_SPEED        = 2.0
UPSTREAM_TIMEOUT = 15
POLL_INTERVAL    = 0.4
MAX_POLLS        = 20

# ============================================================
# VOICE CATALOG
# ============================================================
VOICES = [
    # American Male
    "am_adam", "am_michael", "am_onyx", "am_puck", "am_echo",
    "am_eric", "am_fenrir", "am_liam", "am_santa",
    # British Male
    "bm_george", "bm_lewis", "bm_daniel", "bm_fable",
    # American Female
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "af_nova", "af_river", "af_jessica", "af_kore", "af_aoede", "af_alloy",
    # British Female
    "bf_emma", "bf_alice", "bf_isabella", "bf_lily",
]

# ============================================================
# APP
# ============================================================
app = Flask(__name__)
CORS(app)

# In-memory cache (resets between Vercel cold starts)
_cache = {}
_cache_lock = threading.Lock()


# ============================================================
# UPSTREAM CALL
# ============================================================
def call_upstream(text, voice, speed):
    """
    Forward a synthesis request to the Hugging Face Space.
    Returns WAV bytes on success, raises on failure.
    """
    # ---------- STEP 1: start job ----------
    r = requests.post(
        f"{UPSTREAM}/gradio_api/call/tts",
        json={"data": [text, voice, speed]},
        timeout=UPSTREAM_TIMEOUT,
    )
    r.raise_for_status()

    eid = r.json().get("event_id")
    if not eid:
        raise RuntimeError("Upstream did not return an event_id")

    # ---------- STEP 2: poll for result ----------
    audio_url = None
    for _ in range(MAX_POLLS):
        r = requests.get(
            f"{UPSTREAM}/gradio_api/call/tts/{eid}",
            timeout=UPSTREAM_TIMEOUT,
        )
        r.raise_for_status()

        match = re.search(r'https://[^"]+audio\.wav', r.text)
        if match:
            audio_url = match.group(0)
            break

        time.sleep(POLL_INTERVAL)

    if not audio_url:
        raise TimeoutError("Upstream did not return an audio URL in time")

    # ---------- STEP 3: download WAV ----------
    r = requests.get(audio_url, timeout=UPSTREAM_TIMEOUT)
    r.raise_for_status()
    return r.content


def generate_speech(text, voice="am_adam", speed=1.0):
    """Public wrapper — handles caching and validation."""
    # Cache key
    key = f"{voice}|{speed}|{text}"
    with _cache_lock:
        cached = _cache.get(key)
    if cached:
        return cached

    wav_bytes = call_upstream(text, voice, speed)

    with _cache_lock:
        _cache[key] = wav_bytes
        # Keep cache small — trim if it grows too large
        if len(_cache) > 100:
            # Drop oldest entries
            for k in list(_cache.keys())[:20]:
                _cache.pop(k, None)

    return wav_bytes


# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "time": time.time(),
        "cache_size": len(_cache),
    })


@app.route("/voices")
def voices():
    return jsonify({
        "count": len(VOICES),
        "voices": VOICES,
    })


@app.route("/speak", methods=["POST"])
def speak():
    """Generate speech and return WAV."""
    try:
        data  = request.get_json() or {}
        text  = (data.get("text") or "").strip()
        voice = (data.get("voice") or "am_adam").strip()
        speed = float(data.get("speed", 1.0))

        # ---------- VALIDATION ----------
        if not text:
            return jsonify({"error": "Missing 'text'"}), 400

        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                "error": f"Text too long (max {MAX_TEXT_LENGTH} chars)"
            }), 400

        if voice not in VOICES:
            # Accept unknown voices gracefully — upstream will reject if invalid
            pass

        if speed < MIN_SPEED:
            speed = MIN_SPEED
        elif speed > MAX_SPEED:
            speed = MAX_SPEED

        # ---------- GENERATE ----------
        wav_bytes = generate_speech(text, voice, speed)

        return send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name=f"{voice}.wav",
        )

    except requests.Timeout:
        return jsonify({"error": "Upstream timeout — try again"}), 504

    except requests.HTTPError as e:
        return jsonify({
            "error": f"Upstream error: {e.response.status_code}"
        }), 502

    except TimeoutError as e:
        return jsonify({"error": str(e)}), 504

    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500


@app.route("/clear-cache", methods=["POST"])
def clear_cache():
    with _cache_lock:
        _cache.clear()
    return jsonify({"status": "cleared"})


# ============================================================
# NO app.run() — VERCEL IMPORTS `app` DIRECTLY
# ============================================================