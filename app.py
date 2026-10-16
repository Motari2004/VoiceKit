"""
VoiceKit API — clean routing layer on top of the HF Space.
Users call /speak. This forwards to the Space internally.
Deployed on Vercel as a Python serverless function.
"""

import io
import re
import time
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# ---------- UPSTREAM ----------
# Only this constant mentions Hugging Face.
UPSTREAM = "https://motari-txt2speech.hf.space"

# ---------- APP ----------
app = Flask(__name__)
CORS(app)


def call_upstream(text, voice, speed):
    """Forward to the Space and return WAV bytes."""
    # Step 1 — start job
    r = requests.post(
        f"{UPSTREAM}/gradio_api/call/tts",
        json={"data": [text, voice, speed]},
        timeout=8,
    )
    r.raise_for_status()
    eid = r.json()["event_id"]

    # Step 2 — poll for result (short loop — Vercel timeout is 10s)
    for _ in range(16):
        r = requests.get(
            f"{UPSTREAM}/gradio_api/call/tts/{eid}",
            timeout=5,
        )
        r.raise_for_status()
        match = re.search(r'https://[^"]+audio\.wav', r.text)
        if match:
            # Step 3 — download WAV
            audio = requests.get(match.group(0), timeout=8)
            audio.raise_for_status()
            return audio.content
        time.sleep(0.3)

    raise TimeoutError("Upstream took too long")


# ============================================================
# PUBLIC API
# ============================================================

@app.route("/speak", methods=["POST"])
def speak():
    try:
        data = request.get_json() or {}
        text = (data.get("text") or "").strip()
        voice = (data.get("voice") or "am_adam").strip()
        speed = float(data.get("speed", 1.0))

        if not text:
            return jsonify({"error": "Missing 'text'"}), 400
        if len(text) > 800:
            return jsonify({"error": "Text too long (max 800 chars)"}), 400
        if speed < 0.5 or speed > 2.0:
            speed = 1.0

        wav = call_upstream(text, voice, speed)

        return send_file(
            io.BytesIO(wav),
            mimetype="audio/wav",
            as_attachment=False,
            download_name="speech.wav",
        )
    except requests.Timeout:
        return jsonify({"error": "Upstream timeout — try again"}), 504
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/voices", methods=["GET"])
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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "VoiceKit API",
        "endpoints": {
            "POST /speak": "Generate speech. Body: {text, voice, speed}",
            "GET /voices": "List voices",
            "GET /health": "Health check",
        }
    })


# ---------- NO app.run() — Vercel imports `app` directly ----------