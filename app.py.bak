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
app = Flask(__name__, static_folder="static", static_url_path="/static")
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
                    # ---------- favorites ----------
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS favorites (
                            device_id  TEXT NOT NULL,
                            voice_id   TEXT NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            PRIMARY KEY (device_id, voice_id)
                        );
                    """)

                    # ---------- history ----------
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS history (
                            id         SERIAL PRIMARY KEY,
                            device_id  TEXT NOT NULL,
                            text       TEXT NOT NULL,
                            voice      TEXT NOT NULL,
                            speed      REAL NOT NULL,
                            audio_url  TEXT,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)

                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_history_device
                        ON history (device_id, created_at DESC);
                    """)

                    # ---------- migration: add audio_url if missing ----------
                    # Safe for existing databases created before this column existed.
                    cur.execute("""
                        ALTER TABLE history
                        ADD COLUMN IF NOT EXISTS audio_url TEXT;
                    """)

                
                    # ---------- visits ----------
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS visits (
                            id          SERIAL PRIMARY KEY,
                            device_id   TEXT NOT NULL,
                            page        TEXT,
                            referrer    TEXT,
                            user_agent  TEXT,
                            country     TEXT,
                            created_at  TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)

                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_visits_device
                        ON visits (device_id, created_at DESC);
                    """)

                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_visits_date
                        ON visits (created_at DESC);
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
def call_upstream(text, voice, speed, attempts=3):
    """
    Forward to the HF Space. Retries up to `attempts` times with
    increasing delay. Returns WAV bytes on success, raises on final failure.
    """
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            if attempt > 1:
                # Wait progressively longer between retries
                delay = 2 + (attempt - 1) * 2   # 4s, 6s
                print(f"[upstream] retry {attempt}/{attempts} after {delay}s...")
                time.sleep(delay)

            print(f"[upstream] attempt {attempt}/{attempts}")

            # Step 1: start job
            r = requests.post(
                f"{UPSTREAM}/gradio_api/call/tts",
                json={"data": [text, voice, speed]},
                timeout=UPSTREAM_TIMEOUT,
            )
            r.raise_for_status()

            eid = r.json().get("event_id")
            if not eid:
                raise RuntimeError("No event_id returned")

            # Step 2: poll for result
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
                raise TimeoutError("No audio URL returned")

            # Step 3: download WAV
            r = requests.get(audio_url, timeout=UPSTREAM_TIMEOUT)
            r.raise_for_status()

            print(f"[upstream] success on attempt {attempt}")
            return r.content

        except (requests.Timeout, TimeoutError) as e:
            last_error = e
            print(f"[upstream] attempt {attempt} failed: {type(e).__name__}")
            continue

        except requests.HTTPError as e:
            last_error = e
            print(f"[upstream] HTTP error on attempt {attempt}: {e}")
            continue

        except Exception as e:
            last_error = e
            print(f"[upstream] unexpected error: {type(e).__name__}: {e}")
            continue

    print(f"[upstream] all {attempts} attempts failed")
    raise last_error or TimeoutError("All upstream attempts failed")




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
# CLOUDINARY
# ============================================================
import cloudinary
import cloudinary.uploader

_cloudinary_ready = False

def _init_cloudinary():
    """Read credentials from env vars and configure the SDK."""
    global _cloudinary_ready

    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key    = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

    # Fallback: parse CLOUDINARY_URL if present
    if not (cloud_name and api_key and api_secret):
        url = os.environ.get("CLOUDINARY_URL", "").strip()
        if url.startswith("cloudinary://"):
            try:
                body = url.replace("cloudinary://", "")
                creds, cloud_name = body.split("@", 1)
                api_key, api_secret = creds.split(":", 1)
            except Exception as e:
                print(f"[cloudinary] could not parse CLOUDINARY_URL: {e}")

    print(f"[cloudinary] env check: cloud={'set' if cloud_name else 'MISSING'} "
          f"key={'set' if api_key else 'MISSING'} "
          f"secret={'set' if api_secret else 'MISSING'}")

    if not (cloud_name and api_key and api_secret):
        print("[cloudinary] not configured — uploads will be skipped")
        _cloudinary_ready = False
        return

    try:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
        _cloudinary_ready = True
        print(f"[cloudinary] configured for cloud: {cloud_name}")
    except Exception as e:
        print(f"[cloudinary] config failed: {e}")
        _cloudinary_ready = False


# Run at import
_init_cloudinary()


def upload_to_cloudinary(wav_bytes, voice, device_id=""):
    """Upload WAV bytes to Cloudinary. Returns secure_url or None."""
    if not _cloudinary_ready:
        print("[cloudinary] upload skipped: not configured")
        return None

    try:
        import hashlib
        public_id = "voicekit/" + hashlib.sha1(
            (voice + str(time.time()) + device_id).encode()
        ).hexdigest()[:24]

        print(f"[cloudinary] uploading {len(wav_bytes)} bytes as {public_id}.wav...")

        result = cloudinary.uploader.upload(
            io.BytesIO(wav_bytes),
            resource_type="video",
            public_id=public_id,
            format="wav",
            overwrite=False,
        )
        url = result.get("secure_url")
        print(f"[cloudinary] upload OK: {url}")
        return url
    except Exception as e:
        print(f"[cloudinary] upload FAILED: {type(e).__name__}: {e}")
        return None




# ============================================================
# AUDIO POST-PROCESSING
# ============================================================
def fix_audio_attack(wav_bytes):
    """
    Fixes the 'quiet start then loud' issue.
    1. Trims leading silence.
    2. Normalizes to -1 dBFS.
    3. Boosts the first 250ms if it's quieter than the rest.
    """
    try:
        import numpy as np
        import soundfile as sf
        import io

        # Read WAV
        data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype='float32')
        
        # Handle mono/stereo
        if data.ndim > 1:
            mono = data.mean(axis=1)
        else:
            mono = data

        # 1. Trim leading silence (under -40dB)
        threshold = 0.01
        non_silent = np.where(np.abs(mono) > threshold)[0]
        if len(non_silent) > 0:
            start = non_silent[0]
            # Keep 20ms before the first sound
            start = max(0, start - int(samplerate * 0.02))
            data = data[start:]
            mono = mono[start:]

        # 2. Normalize to -1 dBFS (0.89)
        peak = np.max(np.abs(data))
        if peak > 0:
            target = 0.89
            data = data * (target / peak)

        # 3. Boost the first 250ms if it's quiet
        attack_samples = int(samplerate * 0.25)
        if len(data) > attack_samples:
            first_chunk = data[:attack_samples]
            first_peak = np.max(np.abs(first_chunk))
            overall_peak = np.max(np.abs(data))
            
            if first_peak > 0 and first_peak < (overall_peak * 0.6):
                # Boost first chunk so its peak matches 80% of overall
                boost = (overall_peak * 0.8) / first_peak
                # Apply smooth fade so it doesn't click
                fade = np.linspace(0.5, 1.0, attack_samples)
                data[:attack_samples] *= (boost * fade[:, np.newaxis] if data.ndim > 1 else boost * fade)

        # Re-normalize after boost
        peak = np.max(np.abs(data))
        if peak > 0.95:
            data = data * (0.95 / peak)

        # Write back to WAV
        out = io.BytesIO()
        sf.write(out, data, samplerate, format='WAV', subtype='PCM_16')
        return out.getvalue()

    except Exception as e:
        print(f"[audio-fix] failed: {e}")
        return wav_bytes  # Return original if anything breaks

# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def index():
    # Get device ID from cookie
    device_id = request.cookies.get("voicekit_device", "")

    # Check admin status
    is_admin = device_id in ADMIN_DEVICES if ADMIN_DEVICES else False

    return render_template("index.html", is_admin=is_admin)


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

        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")

        # Fix the quiet-start issue
        wav_bytes = fix_audio_attack(wav_bytes)
        print(f"[speak] after audio fix: {len(wav_bytes)} bytes")

        # Upload to Cloudinary
        audio_url = None
        if device_id and _cloudinary_ready:
            audio_url = upload_to_cloudinary(wav_bytes, voice, device_id)

        # Save history
        if device_id and DATABASE_URL:
            try:
                init_db()
                db_execute(
                    "INSERT INTO history (device_id, text, voice, speed, audio_url) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (device_id, text[:800], voice, speed, audio_url),
                )
                print(f"[speak] history saved")
            except Exception as e:
                print(f"[speak] history insert failed: {e}")

        return send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name=f"{voice}.wav",
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)[:250]}), 500



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
# VISIT TRACKING
# ============================================================
ADMIN_DEVICES = set(
    d.strip() for d in os.environ.get("ADMIN_DEVICES", "").split(",") if d.strip()
)


@app.route("/track", methods=["POST", "OPTIONS"])
def track_visit():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data = request.get_json() or {}
        device_id  = (data.get("device") or "").strip()
        page       = (data.get("page") or "generate").strip()[:50]
        referrer   = (data.get("referrer") or "")[:200]
        user_agent = (request.headers.get("User-Agent") or "")[:200]
        country    = (request.headers.get("x-vercel-ip-country") or "unknown")[:3]

        if not device_id:
            return jsonify({"error": "Missing device"}), 400
        if not DATABASE_URL:
            return jsonify({"status": "no-db"})

        init_db()
        db_execute(
            "INSERT INTO visits (device_id, page, referrer, user_agent, country) "
            "VALUES (%s, %s, %s, %s, %s)",
            (device_id, page, referrer, user_agent, country),
        )
        return jsonify({"status": "tracked"})
    except Exception as e:
        print(f"[db] track failed: {e}")
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/is-admin")
def is_admin():
    device_id = (request.args.get("device") or "").strip()
    return jsonify({"admin": device_id in ADMIN_DEVICES})


@app.route("/stats")
def stats():
    """Return aggregate statistics based on actual generations (history)."""
    device_id = (request.args.get("device") or "").strip()
    if device_id not in ADMIN_DEVICES:
        return jsonify({"error": "forbidden"}), 403

    if not DATABASE_URL:
        return jsonify({"error": "no-db"}), 500

    try:
        init_db()

        # 1. Overall totals from history
        total_gens = db_execute("SELECT COUNT(*) AS n FROM history", fetch_one=True)
        unique_devs = db_execute("SELECT COUNT(DISTINCT device_id) AS n FROM history", fetch_one=True)
        
        today_gens = db_execute(
            "SELECT COUNT(*) AS n FROM history WHERE created_at > NOW() - INTERVAL '1 day'",
            fetch_one=True,
        )
        
        new_today = db_execute(
            "SELECT COUNT(*) AS n FROM history "
            "WHERE created_at > NOW() - INTERVAL '1 day' "
            "AND device_id NOT IN ("
            "  SELECT device_id FROM history WHERE created_at < NOW() - INTERVAL '1 day'"
            ")",
            fetch_one=True,
        )

        # 2. Top Voices used
        voices = db_execute(
            "SELECT voice, COUNT(*) AS n FROM history "
            "GROUP BY voice ORDER BY n DESC LIMIT 10",
            fetch=True,
        )

        # 3. Daily activity
        daily = db_execute(
            "SELECT DATE(created_at) AS day, COUNT(*) AS gens, "
            "COUNT(DISTINCT device_id) AS uniques "
            "FROM history WHERE created_at > NOW() - INTERVAL '14 days' "
            "GROUP BY DATE(created_at) ORDER BY day DESC",
            fetch=True,
        )

        # 4. Recent Generations (The real proof of life)
        recent = db_execute(
            "SELECT device_id, text, voice, audio_url, created_at FROM history "
            "ORDER BY created_at DESC LIMIT 20",
            fetch=True,
        )

        return jsonify({
            "total": total_gens["n"] if total_gens else 0,
            "unique_devices": unique_devs["n"] if unique_devs else 0,
            "today": today_gens["n"] if today_gens else 0,
            "new_today": new_today["n"] if new_today else 0,
            "pages": [{"page": r["voice"], "count": r["n"]} for r in (voices or [])], # Now shows top voices
            "daily": [
                {"day": str(r["day"]), "visits": r["gens"], "uniques": r["uniques"]}
                for r in (daily or [])
            ],
            "devices": [
                {
                    "id": r["device_id"],
                    "count": r["n"],
                    "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
                    "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None
                }
                for r in (db_execute(
                    "SELECT device_id, COUNT(*) AS n, "
                    "MIN(created_at) AS first_seen, MAX(created_at) AS last_seen "
                    "FROM history GROUP BY device_id "
                    "ORDER BY n DESC",
                    fetch=True
                ) or [])
            ],
            "recent": [
                {
                    "full_device_id": r["device_id"],
                    "page": "Generate",
                    "country": "—", 
                    "device_type": r["voice"],
                    "user_agent": r["text"], # FULL TEXT
                    "audio_url": r.get("audio_url"),
                    "at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in (recent or [])
            ],
        })
    except Exception as e:
        print(f"[stats] failed: {e}")
        return jsonify({"error": str(e)[:200]}), 500



# ============================================================
# NO app.run() — VERCEL IMPORTS `app` DIRECTLY
# ============================================================
