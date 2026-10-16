"""
VoiceKit — Cloudinary Storage
- Uploads generated WAVs to Cloudinary
- Stores the secure URL in the history table
- Replay plays from Cloudinary (instant, no re-generation)
- Falls back to regeneration if URL is missing
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
# requirements.txt
# ============================================================
NEW_REQS = """flask
flask-cors
requests
psycopg[binary]
cloudinary
"""


# ============================================================
# Cloudinary setup block (inserted into app.py)
# ============================================================
CLOUDINARY_BLOCK = '''
# ============================================================
# CLOUDINARY
# ============================================================
import cloudinary
import cloudinary.uploader

_cloudinary_ready = False
if os.environ.get("CLOUDINARY_URL"):
    try:
        cloudinary.config(secure=True)
        _cloudinary_ready = True
        print("[cloudinary] configured")
    except Exception as e:
        print(f"[cloudinary] config failed: {e}")


def upload_to_cloudinary(wav_bytes, voice):
    """Upload WAV bytes to Cloudinary. Returns secure_url or None."""
    if not _cloudinary_ready:
        return None
    try:
        import hashlib
        public_id = "voicekit/" + hashlib.sha1(
            (voice + str(time.time())).encode()
        ).hexdigest()[:24]

        result = cloudinary.uploader.upload(
            io.BytesIO(wav_bytes),
            resource_type="video",
            public_id=public_id,
            format="wav",
            overwrite=False,
        )
        url = result.get("secure_url")
        print(f"[cloudinary] uploaded: {url}")
        return url
    except Exception as e:
        print(f"[cloudinary] upload failed: {e}")
        return None
'''


# ============================================================
# Updated /speak route
# ============================================================
NEW_SPEAK = '''@app.route("/speak", methods=["POST", "OPTIONS"])
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

        # Upload to Cloudinary + save history
        if device_id and DATABASE_URL:
            try:
                init_db()
                audio_url = upload_to_cloudinary(wav_bytes, voice)
                db_execute(
                    "INSERT INTO history (device_id, text, voice, speed, audio_url) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (device_id, text[:800], voice, speed, audio_url),
                )
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
'''


# ============================================================
# Updated /history GET
# ============================================================
NEW_HISTORY = '''@app.route("/history", methods=["GET"])
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
'''


# ============================================================
# Migration SQL
# ============================================================
MIGRATION = '''
                    # Ensure audio_url column exists (safe migration)
                    try:
                        cur.execute("ALTER TABLE history ADD COLUMN IF NOT EXISTS audio_url TEXT;")
                    except Exception:
                        pass
'''


# ============================================================
# Frontend replay
# ============================================================
NEW_REPLAY = '''      btn.onclick = () => {
        if (h.audio_url) {
          new Audio(h.audio_url).play();
          return;
        }

        btn.disabled = true;
        btn.textContent = '\\u23f3 Loading...';
        fetch('/speak', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: h.text,
            voice: h.voice,
            speed: h.speed,
            device_id: (typeof DEVICE_ID !== 'undefined') ? DEVICE_ID : ''
          })
        })
        .then(r => r.ok ? r.blob() : Promise.reject(new Error('Replay failed')))
        .then(blob => { new Audio(URL.createObjectURL(blob)).play(); })
        .catch(e => { console.error('Replay error:', e); })
        .finally(() => {
          btn.disabled = false;
          btn.textContent = '\\u25b6 Replay';
        });
      };'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Cloudinary Storage")
    print("=" * 60)

    # ---------- requirements ----------
    print("\n[1/3] requirements.txt")
    backup(REQ)
    with open(REQ, "w", encoding="utf-8") as f:
        f.write(NEW_REQS)
    print("  added cloudinary")

    # ---------- app.py ----------
    print("\n[2/3] app.py")
    if not os.path.exists(APP):
        print(f"  ERROR: {APP} not found")
        return
    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # Cloudinary block — insert before # UPSTREAM
    if 'import cloudinary' not in src:
        anchor = "# ============================================================\n# UPSTREAM"
        if anchor in src:
            src = src.replace(anchor, CLOUDINARY_BLOCK + "\n" + anchor, 1)
            changes.append("cloudinary block")

    # Migration in init_db
    if 'audio_url' not in src.split('CREATE TABLE IF NOT EXISTS history')[1][:400]:
        old_index = 'CREATE INDEX IF NOT EXISTS idx_history_device'
        if old_index in src:
            idx_pos = src.find(old_index)
            end_pos = src.find('"""', idx_pos)
            if end_pos != -1:
                src = src[:end_pos] + MIGRATION + src[end_pos:]
                changes.append("audio_url migration")

    # Replace /speak
    speak_pattern = re.compile(
        r'@app\.route\("/speak", methods=\["POST", "OPTIONS"\]\)\s*\ndef speak\(\):.*?(?=\n# ---------- FAVORITES|\n# =+\s*\n# FAVORITES)',
        re.DOTALL
    )
    if speak_pattern.search(src):
        src = speak_pattern.sub(NEW_SPEAK + "\n\n", src, count=1)
        changes.append("/speak")

    # Replace /history GET
    hist_pattern = re.compile(
        r'@app\.route\("/history", methods=\["GET"\]\)\s*\ndef get_history\(\):.*?(?=\n@app\.route\("/history", methods=\["DELETE")',
        re.DOTALL
    )
    if hist_pattern.search(src):
        src = hist_pattern.sub(NEW_HISTORY + "\n\n", src, count=1)
        changes.append("/history GET")

    if src == original:
        print("  No changes.")
    else:
        with open(APP, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"  [OK] Applied: {', '.join(changes)}")

    # ---------- index.html ----------
    print("\n[3/3] templates/index.html")
    if not os.path.exists(HTML):
        print(f"  ERROR: {HTML} not found")
        return
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    old_handler = re.search(
        r'btn\.onclick = (?:async )?\(\) => \{.*?\n      \};',
        src,
        re.DOTALL
    )
    if old_handler:
        src = src[:old_handler.start()] + NEW_REPLAY + src[old_handler.end():]
        print("  [OK] replay handler")

    if src != original:
        with open(HTML, "w", encoding="utf-8") as f:
            f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Next steps:")
    print()
    print(" 1. Add env vars to Vercel (Settings → Environment Variables):")
    print("    CLOUDINARY_CLOUD_NAME = your_cloud_name")
    print("    CLOUDINARY_API_KEY    = your_api_key")
    print("    CLOUDINARY_API_SECRET = your_api_secret")
    print()
    print(" 2. Add this in app.py — BEFORE the Cloudinary block:")
    print("    (the SDK reads these and builds CLOUDINARY_URL internally)")
    print()
    print("    import cloudinary")
    print("    cloudinary.config(")
    print("        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),")
    print("        api_key=os.environ.get('CLOUDINARY_API_KEY'),")
    print("        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),")
    print("        secure=True")
    print("    )")
    print()
    print(" 3. Install:")
    print("    pip install cloudinary")
    print()
    print(" 4. Deploy:")
    print("    vercel --prod")
    print()
    print(" 5. Verify:")
    print("    Generate once, then check the console:")
    print("    fetch('/history?device=' + localStorage.getItem('voicekit_device_id'))")
    print("      .then(r => r.json())")
    print("      .then(d => console.log(d))")
    print()
    print("    You should see 'audio_url' with a res.cloudinary.com link.")
    print()
    print("=" * 60)


if __name__ == "__main__":
    patch()