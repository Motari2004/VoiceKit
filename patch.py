"""
VoiceKit — Persistence Patch
Adds Neon Postgres for favorites and history.
- Creates favorites + history tables
- /favorites GET/POST endpoints
- /history GET/POST endpoints
- Frontend uses device_id + server sync
Backs up everything first.
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP  = os.path.join(BASE, "app.py")
REQ  = os.path.join(BASE, "requirements.txt")
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


# ============================================================
# NEW app.py
# ============================================================
NEW_APP = r'''"""
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
# DATABASE
# ============================================================
def get_db():
    if not DATABASE_URL:
        return None
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


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
                    """)
                conn.commit()
            print("[db] Tables ready")
        except Exception as e:
            print(f"[db] init failed: {e}")
        finally:
            _db_initialized = True


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

        wav_bytes = generate_speech(text, voice, speed)

        # Record history (best-effort)
        if device_id and DATABASE_URL:
            try:
                init_db()
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO history (device_id, text, voice, speed) VALUES (%s, %s, %s, %s)",
                            (device_id, text[:800], voice, speed),
                        )
                    conn.commit()
            except Exception as e:
                print(f"[db] history insert failed: {e}")

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


# ---------- FAVORITES ----------
@app.route("/favorites", methods=["GET"])
def get_favorites():
    device_id = (request.args.get("device") or "").strip()
    if not device_id:
        return jsonify({"favorites": []})
    if not DATABASE_URL:
        return jsonify({"favorites": []})

    try:
        init_db()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT voice_id FROM favorites WHERE device_id = %s ORDER BY created_at",
                    (device_id,),
                )
                rows = cur.fetchall()
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
                # Delete removed
                if voice_ids:
                    cur.execute(
                        "DELETE FROM favorites WHERE device_id = %s AND voice_id != ALL(%s)",
                        (device_id, voice_ids),
                    )
                else:
                    cur.execute("DELETE FROM favorites WHERE device_id = %s", (device_id,))

                # Insert new
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
    if not device_id:
        return jsonify({"history": []})

    if not DATABASE_URL:
        return jsonify({"history": []})

    try:
        init_db()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, text, voice, speed, created_at FROM history WHERE device_id = %s ORDER BY created_at DESC LIMIT %s",
                    (device_id, limit),
                )
                rows = cur.fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "text": r["text"],
                "voice": r["voice"],
                "speed": r["speed"],
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
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM history WHERE device_id = %s", (device_id,))
            conn.commit()

        return jsonify({"status": "cleared"})
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500


# ============================================================
# NO app.run() — VERCEL IMPORTS `app` DIRECTLY
# ============================================================
'''


# ============================================================
# requirements.txt
# ============================================================
NEW_REQS = """flask
flask-cors
requests
psycopg[binary]
"""


# ============================================================
# Frontend JS addition
# ============================================================
FRONTEND_JS = r'''
// ============================================================
// DEVICE ID + PERSISTENCE
// ============================================================
function getDeviceId() {
  let id = localStorage.getItem('voicekit_device_id');
  if (!id) {
    id = 'dev_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('voicekit_device_id', id);
  }
  return id;
}

const DEVICE_ID = getDeviceId();

async function syncFavoritesFromServer() {
  try {
    const res = await fetch(`/favorites?device=${encodeURIComponent(DEVICE_ID)}`);
    const data = await res.json();
    if (Array.isArray(data.favorites)) {
      // Merge server favorites with local
      const merged = Array.from(new Set([...favorites, ...data.favorites]));
      if (merged.length !== favorites.length) {
        favorites = merged;
        saveFavorites(favorites);
        applyFavoritesToAllChips();
        updateFavoriteCount();
      }
    }
  } catch (e) {
    console.warn('[favorites] sync failed:', e);
  }
}

async function pushFavoritesToServer() {
  try {
    await fetch('/favorites', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device: DEVICE_ID, favorites })
    });
  } catch (e) {
    console.warn('[favorites] push failed:', e);
  }
}

async function loadHistoryFromServer() {
  try {
    const res = await fetch(`/history?device=${encodeURIComponent(DEVICE_ID)}&limit=30`);
    const data = await res.json();
    if (Array.isArray(data.history)) {
      serverHistory = data.history;
    }
  } catch (e) {
    console.warn('[history] load failed:', e);
  }
}

async function pushHistoryToServer(entry) {
  try {
    await fetch('/history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device: DEVICE_ID, ...entry })
    });
  } catch (e) {
    console.warn('[history] push failed:', e);
  }
}

let serverHistory = [];
'''


# ============================================================
# PATCH
# ============================================================
def patch():
    print("=" * 60)
    print(" VoiceKit — Persistence Patch")
    print("=" * 60)

    # ---------- app.py ----------
    print("\n[1/3] app.py")
    backup(APP)
    with open(APP, "w", encoding="utf-8") as f:
        f.write(NEW_APP)
    print("  rewrote with favorites + history")

    # ---------- requirements.txt ----------
    print("\n[2/3] requirements.txt")
    backup(REQ)
    with open(REQ, "w", encoding="utf-8") as f:
        f.write(NEW_REQS)
    print("  added psycopg[binary]")

    # ---------- index.html ----------
    print("\n[3/3] templates/index.html")
    if not os.path.exists(HTML):
        print(f"  ERROR: {HTML} not found")
        return
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # Insert DEVICE_ID + persistence helpers before "// LOAD VOICES"
    anchor = "// ============================================================\n// LOAD VOICES"
    if 'voicekit_device_id' not in src and anchor in src:
        src = src.replace(anchor, FRONTEND_JS + "\n" + anchor, 1)
        changes.append("persistence helpers")

    # Update speak() to send device_id
    old_body = "body: JSON.stringify({ text, voice: selectedVoiceId, speed })"
    new_body = "body: JSON.stringify({ text, voice: selectedVoiceId, speed, device_id: DEVICE_ID })"
    if old_body in src:
        src = src.replace(old_body, new_body)
        changes.append("device_id in speak")

    # After a successful generation, push history
    old_hist = "history.unshift({ text, voice: selectedVoiceName, speed, url, ts: Date.now(), ms });"
    new_hist = """history.unshift({ text, voice: selectedVoiceName, speed, url, ts: Date.now(), ms });
    pushHistoryToServer({ text, voice: selectedVoiceId, speed });"""
    if old_hist in src and 'pushHistoryToServer' in src:
        src = src.replace(old_hist, new_hist)
        changes.append("push history on generate")

    # Wire toggleFavorite to push to server
    old_toggle = """function toggleFavorite(id) {
  if (isFavorite(id)) {
    favorites = favorites.filter(f => f !== id);
  } else {
    favorites.push(id);
  }
  saveFavorites(favorites);
  updateFavoriteUI(id);
  updateFavoriteCount();
}"""

    new_toggle = """function toggleFavorite(id) {
  if (isFavorite(id)) {
    favorites = favorites.filter(f => f !== id);
  } else {
    favorites.push(id);
  }
  saveFavorites(favorites);
  updateFavoriteUI(id);
  updateFavoriteCount();
  pushFavoritesToServer();
}"""

    if old_toggle in src:
        src = src.replace(old_toggle, new_toggle)
        changes.append("favorite sync")

    # On page load, sync from server
    old_init = "loadVoices();\nsetStatus('Ready."
    new_init = """loadVoices();
syncFavoritesFromServer();
loadHistoryFromServer();
setStatus('Ready."""
    if old_init in src and 'syncFavoritesFromServer' in src:
        src = src.replace(old_init, new_init)
        changes.append("init server sync")

    if src == original:
        print("  No changes.")
    else:
        with open(HTML, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"  [OK] Applied: {', '.join(changes)}")

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Next steps:")
    print("   1. Rotate the Neon password (you pasted it in chat)")
    print("   2. Add DATABASE_URL to Vercel env vars")
    print("   3. pip install psycopg[binary]")
    print("   4. vercel --prod")
    print()
    print(" New API endpoints:")
    print("   GET    /favorites?device=xxx")
    print("   POST   /favorites")
    print("   GET    /history?device=xxx")
    print("   DELETE /history")
    print()
    print(" Frontend behavior:")
    print("   • Generates a device_id on first visit (localStorage)")
    print("   • Favorites sync from/to the server on load + on change")
    print("   • History is pushed after every generation")
    print("   • localStorage still works as a cache")
    print()
    print(" Backups saved as .bak files.")
    print("=" * 60)


if __name__ == "__main__":
    patch()