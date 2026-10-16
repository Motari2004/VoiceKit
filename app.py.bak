"""
VoiceKit — Text-to-Speech API with persistent favorites + history.
Deployed on Vercel as a Python serverless function.

Environment:
    DATABASE_URL  — Neon Postgres connection string
"""

import io
import os
import re
import time
import threading
import requests
import psycopg
from psycopg.rows import dict_row
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS


import cloudinary
import cloudinary.uploader

CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")
if CLOUDINARY_URL:
    # The cloudinary SDK reads CLOUDINARY_URL automatically,
    # but we can also configure explicitly from parts.
    pass


# ============================================================
# CONFIG
# ============================================================
UPSTREAM = "https://motari-txt2speech.hf.space"
DATABASE_URL = os.environ.get("DATABASE_URL", "")

MAX_TEXT_LENGTH  = 800
MIN_SPEED        = 0.5
MAX_SPEED        = 2.0
UPSTREAM_TIMEOUT = 15
POLL_INTERVAL    = 0.4
MAX_POLLS        = 20

VOICES = [
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro",
    "jm_kumo",
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
    "ef_dora", "em_alex", "em_santa",
    "ff_siwis",
    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    "if_sara", "im_nicola",
    "pf_dora", "pm_alex", "pm_santa",
]

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
        "Male": [("jm_kumo", "Kumo", "Calm")],
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
        "Female": [("ef_dora", "Dora", "Warm")],
        "Male": [
            ("em_alex", "Alex", "Clear"),
            ("em_santa", "Santa", "Deep"),
        ],
    },
    "French": {
        "Female": [("ff_siwis", "Siwis", "Clear")],
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
        "Female": [("if_sara", "Sara", "Clear")],
        "Male": [("im_nicola", "Nicola", "Warm")],
    },
    "Portuguese": {
        "Female": [("pf_dora", "Dora", "Warm")],
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
_db_initialized = False
_db_lock = threading.Lock()


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ============================================================
# DATABASE — Neon Postgres
# ============================================================
import urllib.parse

def _normalize_db_url(url):
    """Strip psycopg-incompatible query params (channel_binding, etc.)."""
    if not url:
        return url
    # Remove channel_binding — psycopg doesn't support it
    url = re.sub(r'[?&]channel_binding=[^&]*', '', url)
    # Ensure sslmode=require for Neon
    if 'sslmode=' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}sslmode=require"
    # Clean up doubled separators
    url = re.sub(r'[?&]+$', '', url)
    url = re.sub(r'[?&]{2,}', '&', url)
    return url


def get_db():
    """Open a new connection to Neon with keepalives enabled."""
    if not DATABASE_URL:
        return None
    url = _normalize_db_url(DATABASE_URL)
    return psycopg.connect(
        url,
        row_factory=dict_row,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
        connect_timeout=10,
    )


def init_db():
    global _db_initialized
    if _db_initialized:
        return
    with _db_lock:
        if _db_initialized:
            return
        if not DATABASE_URL:
            print("[db] DATABASE_URL not set — persistence disabled")
            _db_initialized = True
            return
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS favorites (
                            device_id  TEXT NOT NULL,
                            voice_id   TEXT NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            PRIMARY KEY (device_id, voice_id)
                        );
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS history (
                            audio_url  TEXT,
                            id         SERIAL PRIMARY KEY,
                            device_id  TEXT NOT NULL,
                            text       TEXT NOT NULL,
                            voice      TEXT NOT NULL,
                            speed      REAL NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_history_device
                        ON history (device_id, created_at DESC);
                    
                    # Add column if it doesn't exist (safe for existing DBs)
                    try:
                        cur.execute("ALTER TABLE history ADD COLUMN IF NOT EXISTS audio_url TEXT;")
                    except Exception:
                        pass
""")
                conn.commit()
            print("[db] Tables ready")
        except Exception as e:
            print(f"[db] init failed: {e}")
        finally:
            _db_initialized = True


def db_execute(query, params=None, fetch=False, fetch_one=False):
    """
    Execute a query with automatic retry on stale connection.
    Neon's serverless pooler may close idle connections.
    """
    for attempt in range(2):
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    if fetch:
                        result = cur.fetchall()
                    elif fetch_one:
                        result = cur.fetchone()
                    else:
                        result = None
                conn.commit()
                return result
        except psycopg.OperationalError as e:
            # Connection dropped — retry once
            print(f"[db] connection error (attempt {attempt+1}): {e}")
            if attempt == 0:
                continue
            raise
        except Exception:
            raise
    return None



# ============================================================
# UPSTREAM
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
        raise RuntimeError("No event_id")

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
        raise TimeoutError("No audio URL")

    r = requests.get(audio_url, timeout=UPSTREAM_TIMEOUT)
    r.raise_for_status()
    return r.content


def generate_speech(text, voice, speed):
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
# CLOUDINARY UPLOAD
# ============================================================
def upload_to_cloudinary(wav_bytes, voice, device_id):
    """Upload WAV bytes to Cloudinary. Returns secure_url or None."""
    if not os.environ.get("CLOUDINARY_URL"):
        return None
    try:
        import cloudinary
        import cloudinary.uploader

        # Public ID: unique per generation
        import hashlib
        public_id = "voicekit/" + hashlib.sha1(
            (voice + str(time.time()) + device_id).encode()
        ).hexdigest()[:20]

        result = cloudinary.uploader.upload(
            io.BytesIO(wav_bytes),
            resource_type="video",  # Cloudinary uses 'video' for audio
            public_id=public_id,
            format="wav",
            overwrite=True,
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"[cloudinary] upload failed: {e}")
        return None

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
        "db": bool(DATABASE_URL),
    })


@app.route("/voices")
def voices():
    return jsonify({"count": len(VOICES), "voices": VOICES})


@app.route("/voices/catalog")
def voices_catalog():
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
        device_id = (data.get("device_id") or "").strip()

        if not text:
            return jsonify({"error": "Missing 'text'"}), 400
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({"error": f"Text too long (max {MAX_TEXT_LENGTH})"}), 400

        speed = max(MIN_SPEED, min(MAX_SPEED, speed))

        # 1. Generate the audio (blocking — user waits for this)
        wav_bytes = generate_speech(text, voice, speed)

        # 2. Kick off upload + history save in the background
        if device_id:
            threading.Thread(
                target=_background_save,
                args=(wav_bytes, voice, device_id, text, speed),
                daemon=True,
            ).start()

        # 3. Return the WAV to the user immediately
        return send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name=f"{voice}.wav",
        )

    except requests.Timeout:
        return jsonify({"error": "Voice service is warming up. Try again in a moment."}), 504
    except TimeoutError:
        return jsonify({"error": "Voice service is warming up. Try again in a moment."}), 504
    except requests.HTTPError as e:
        return jsonify({"error": f"Upstream error: {e.response.status_code}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500


def _background_save(wav_bytes, voice, device_id, text, speed):
    """Upload to Cloudinary + save history. Runs after the response."""
    audio_url = None
    try:
        if _cloudinary_ready:
            audio_url = upload_to_cloudinary(wav_bytes, voice, device_id)
    except Exception as e:
        print(f"[cloudinary] background upload failed: {e}")

    try:
        if DATABASE_URL:
            init_db()
            db_execute(
                "INSERT INTO history (device_id, text, voice, speed, audio_url) "
                "VALUES (%s, %s, %s, %s, %s)",
                (device_id, text[:800], voice, speed, audio_url),
            )
            print(f"[history] saved (audio_url={audio_url})")
    except Exception as e:
        print(f"[db] history insert failed: {e}")



# ---------- FAVORITES ----------
@app.route("/favorites", methods=["GET"])
def get_favorites():
    device_id = (request.args.get("device") or "").strip()
    if not device_id or not DATABASE_URL:
        return jsonify({"favorites": []})

    try:
        init_db()
        rows = db_execute(
            "SELECT voice_id FROM favorites WHERE device_id = %s ORDER BY created_at",
            (device_id,),
            fetch=True,
        )
        return jsonify({"favorites": [r["voice_id"] for r in rows]})
    except Exception as e:
        print(f"[db] get favorites failed: {e}")
        return jsonify({"favorites": [], "error": str(e)[:200]})


@app.route("/favorites", methods=["POST", "OPTIONS"])
def save_favorites():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data = request.get_json() or {}
        device_id = (data.get("device") or "").strip()
        voice_ids = data.get("favorites") or []

        if not device_id:
            return jsonify({"error": "Missing 'device'"}), 400
        if not isinstance(voice_ids, list):
            return jsonify({"error": "'favorites' must be a list"}), 400

        if not DATABASE_URL:
            return jsonify({"status": "no-db", "favorites": voice_ids})

        init_db()

        with get_db() as conn:
            with conn.cursor() as cur:
                if voice_ids:
                    cur.execute(
                        "DELETE FROM favorites WHERE device_id = %s AND voice_id != ALL(%s)",
                        (device_id, voice_ids),
                    )
                else:
                    cur.execute("DELETE FROM favorites WHERE device_id = %s", (device_id,))

                for vid in voice_ids:
                    cur.execute(
                        "INSERT INTO favorites (device_id, voice_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (device_id, vid),
                    )
            conn.commit()

        return jsonify({"status": "saved", "favorites": voice_ids})
    except Exception as e:
        print(f"[db] save favorites failed: {e}")
        return jsonify({"error": str(e)[:250]}), 500


# ---------- HISTORY ----------
@app.route("/history", methods=["GET"])
def get_history():
    device_id = (request.args.get("device") or "").strip()
    limit = int(request.args.get("limit", 30))
    if not device_id or not DATABASE_URL:
        return jsonify({"history": []})

    try:
        init_db()
        rows = db_execute(
            "SELECT id, text, voice, speed, audio_url, created_at FROM history "
            "WHERE device_id = %s ORDER BY created_at DESC LIMIT %s",
            (device_id, limit),
            fetch=True,
        )

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "text": r["text"],
                "voice": r["voice"],
                "speed": r["speed"],
                "audio_url": r.get("audio_url"),
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            })
        return jsonify({"history": result})
    except Exception as e:
        print(f"[db] get history failed: {e}")
        return jsonify({"history": [], "error": str(e)[:200]})



@app.route("/history", methods=["DELETE", "OPTIONS"])
def delete_history():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data = request.get_json() or {}
        device_id = (data.get("device") or "").strip()

        if not device_id:
            return jsonify({"error": "Missing 'device'"}), 400
        if not DATABASE_URL:
            return jsonify({"status": "no-db"})

        init_db()
        db_execute("DELETE FROM history WHERE device_id = %s", (device_id,))
        return jsonify({"status": "cleared"})
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500



# ============================================================
# NO app.run() — VERCEL IMPORTS `app` DIRECTLY
# ============================================================
