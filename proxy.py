"""
VoiceKit proxy.
Exposes /speak on your own domain. Forwards to the HF Space internally.
Users never see huggingface.co.
"""

import io
import re
import time
import os
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# The only place HF is mentioned in this entire codebase.
UPSTREAM = "https://motari-txt2speech.hf.space"

app = Flask(__name__)
CORS(app)


def call_upstream(text, voice, speed):
    """Forward to HF, return WAV bytes."""
    # Step 1 — start job
    r = requests.post(
        f"{UPSTREAM}/gradio_api/call/tts",
        json={"data": [text, voice, speed]},
        timeout=30,
    )
    r.raise_for_status()
    eid = r.json()["event_id"]

    # Step 2 — poll for result
    for _ in range(60):
        r = requests.get(
            f"{UPSTREAM}/gradio_api/call/tts/{eid}",
            timeout=30,
        )
        r.raise_for_status()
        match = re.search(r'https://[^"]+audio\.wav', r.text)
        if match:
            # Step 3 — download WAV
            audio = requests.get(match.group(0), timeout=30)
            audio.raise_for_status()
            return audio.content
        time.sleep(0.5)

    raise TimeoutError("Upstream timed out")


# ============================================================
# PUBLIC API — this is what users see and call
# ============================================================

@app.route("/speak", methods=["POST"])
def speak():
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    voice = (data.get("voice") or "am_adam").strip()
    speed = float(data.get("speed", 1.0))

    if not text:
        return jsonify({"error": "Missing 'text'"}), 400
    if len(text) > 800:
        return jsonify({"error": "Text too long (max 800 chars)"}), 400

    try:
        wav = call_upstream(text, voice, speed)
        return send_file(
            io.BytesIO(wav),
            mimetype="audio/wav",
            as_attachment=False,
            download_name="speech.wav",
        )
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)