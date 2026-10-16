"""
VoiceKit — one Flask app, one URL.
    /              → HTML UI
    /speak         → JSON API (returns WAV)
    /voices        → JSON API (all 54 voices)
    /health        → JSON API
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
# ALL 54 VOICES
# ============================================================
VOICES = [
    # ---------- American English — Female ----------
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",

    # ---------- American English — Male ----------
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",

    # ---------- British English — Female ----------
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",

    # ---------- British English — Male ----------
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",

    # ---------- Japanese — Female ----------
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro",

    # ---------- Japanese — Male ----------
    "jm_kumo",

    # ---------- Mandarin Chinese — Female ----------
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",

    # ---------- Mandarin Chinese — Male ----------
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",

    # ---------- Spanish — Female ----------
    "ef_dora",

    # ---------- Spanish — Male ----------
    "em_alex", "em_santa",

    # ---------- French — Female ----------
    "ff_siwis",

    # ---------- Hindi — Female ----------
    "hf_alpha", "hf_beta",

    # ---------- Hindi — Male ----------
    "hm_omega", "hm_psi",

    # ---------- Italian — Female ----------
    "if_sara",

    # ---------- Italian — Male ----------
    "im_nicola",

    # ---------- Portuguese — Female ----------
    "pf_dora",

    # ---------- Portuguese — Male ----------
    "pm_alex", "pm_santa",
]

# ============================================================
# VOICE METADATA (for the UI)
# ============================================================
VOICE_CATALOG = {
    "American English": {
        "Female": [
            ("af_alloy", "Alloy", "Bright, energetic"),
            ("af_aoede", "Aoede", "Melodic, lyrical"),
            ("af_bella", "Bella", "Bright, clear"),
            ("af_heart", "Heart", "Warm, emotive"),
            ("af_jessica", "Jessica", "Confident, sharp"),
            ("af_kore", "Kore", "Warm, poetic"),
            ("af_nicole", "Nicole", "Soft, calm"),
            ("af_nova", "Nova", "Crisp, modern"),
            ("af_river", "River", "Calm, flowing"),
            ("af_sarah", "Sarah", "Clear, neutral"),
            ("af_sky", "Sky", "Youthful, light"),
        ],
        "Male": [
            ("am_adam", "Adam", "Deep, broadcaster"),
            ("am_echo", "Echo", "Bright"),
            ("am_eric", "Eric", "Clear"),
            ("am_fenrir", "Fenrir", "Deep, cinematic"),
            ("am_liam", "Liam", "Warm, friendly"),
            ("am_michael", "Michael", "Warm, natural"),
            ("am_onyx", "Onyx", "Rich, resonant"),
            ("am_puck", "Puck", "Playful"),
            ("am_santa", "Santa", "Gravelly, storyteller"),
        ],
    },
    "British English": {
        "Female": [
            ("bf_alice", "Alice", "Clear, bright"),
            ("bf_emma", "Emma", "Warm, elegant"),
            ("bf_isabella", "Isabella", "Refined, smooth"),
            ("bf_lily", "Lily", "Youthful, gentle"),
        ],
        "Male": [
            ("bm_daniel", "Daniel", "Clear, articulate"),
            ("bm_fable", "Fable", "Storyteller, warm"),
            ("bm_george", "George", "Warm, refined"),
            ("bm_lewis", "Lewis", "Deep, authoritative"),
        ],
    },
    "Japanese": {
        "Female": [
            ("jf_alpha", "Alpha", "Clear"),
            ("jf_gongitsune", "Gongitsune", "Storyteller"),
            ("jf_nezumi", "Nezumi", "Light"),
            ("jf_tebukuro", "Tebukuro", "Warm"),
        ],
        "Male": [
            ("jm_kumo", "Kumo", "Calm"),
        ],
    },
    "Mandarin Chinese": {
        "Female": [
            ("zf_xiaobei", "Xiaobei", "Bright"),
            ("zf_xiaoni", "Xiaoni", "Soft"),
            ("zf_xiaoxiao", "Xiaoxiao", "Clear"),
            ("zf_xiaoyi", "Xiaoyi", "Warm"),
        ],
        "Male": [
            ("zm_yunjian", "Yunjian", "Clear"),
            ("zm_yunxi", "Yunxi", "Warm"),
            ("zm_yunxia", "Yunxia", "Soft"),
            ("zm_yunyang", "Yunyang", "Bright"),
        ],
    },
    "Spanish": {
        "Female": [
            ("ef_dora", "Dora", "Warm"),
        ],
        "Male": [
            ("em_alex", "Alex", "Clear"),
            ("em_santa", "Santa", "Deep"),
        ],
    },
    "French": {
        "Female": [
            ("ff_siwis", "Siwis", "Clear"),
        ],
        "Male": [],
    },
    "Hindi": {
        "Female": [
            ("hf_alpha", "Alpha", "Warm"),
            ("hf_beta", "Beta", "Clear"),
        ],
        "Male": [
            ("hm_omega", "Omega", "Deep"),
            ("hm_psi", "Psi", "Clear"),
        ],
    },
    "Italian": {
        "Female": [
            ("if_sara", "Sara", "Clear"),
        ],
        "Male": [
            ("im_nicola", "Nicola", "Warm"),
        ],
    },
    "Portuguese": {
        "Female": [
            ("pf_dora", "Dora", "Warm"),
        ],
        "Male": [
            ("pm_alex", "Alex", "Clear"),
            ("pm_santa", "Santa", "Deep"),
        ],
    },
}

# ============================================================
# APP
# ============================================================
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


# ============================================================
# UPSTREAM CALL
# ============================================================
def call_upstream(text, voice, speed):
    r = requests.post(
        f"{UPSTREAM}/gradio_api/call/tts",
        json={"data": [text, voice, speed]},
        timeout=UPSTREAM_TIMEOUT,
    )
    r.raise_for_status()
    eid = r.json().get("event_id")
    if not eid:
        raise RuntimeError("Upstream did not return an event_id")

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
        raise TimeoutError("Upstream did not return audio in time")

    r = requests.get(audio_url, timeout=UPSTREAM_TIMEOUT)
    r.raise_for_status()
    return r.content


def generate_speech(text, voice="am_adam", speed=1.0):
    key = f"{voice}|{speed}|{text}"
    with _cache_lock:
        cached = _cache.get(key)
    if cached:
        return cached

    wav = call_upstream(text, voice, speed)

    with _cache_lock:
        _cache[key] = wav
        if len(_cache) > 100:
            for k in list(_cache.keys())[:20]:
                _cache.pop(k, None)

    return wav


# ============================================================
# UI
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# API
# ============================================================
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "time": time.time(),
        "cache_size": len(_cache),
    })


@app.route("/voices")
def voices():
    """Return all 54 voices as a flat list."""
    return jsonify({
        "count": len(VOICES),
        "voices": VOICES,
    })


@app.route("/voices/catalog")
def voices_catalog():
    """Return voices organized by language and gender (for the UI)."""
    return jsonify(VOICE_CATALOG)


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
            return jsonify({
                "error": f"Text too long (max {MAX_TEXT_LENGTH} chars)"
            }), 400

        speed = max(MIN_SPEED, min(MAX_SPEED, speed))

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
        return jsonify({"error": f"Upstream error: {e.response.status_code}"}), 502
    except TimeoutError as e:
        return jsonify({"error": str(e)}), 504
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500


@app.route("/clear-cache", methods=["POST"])
def clear_cache():
    with _cache_lock:
        _cache.clear()
    return jsonify({"status": "cleared"})