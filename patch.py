"""
VoiceKit — Cloudinary Audio Storage
- Uploads generated WAVs to Cloudinary
- Saves the URL in the history table
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
# PATCH 1: requirements.txt
# ============================================================
NEW_REQS = """flask
flask-cors
requests
psycopg[binary]
cloudinary
"""


# ============================================================
# PATCH 2: app.py additions
# ============================================================
CLOUDINARY_IMPORT = '''
import cloudinary
import cloudinary.uploader

CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")
if CLOUDINARY_URL:
    # The cloudinary SDK reads CLOUDINARY_URL automatically,
    # but we can also configure explicitly from parts.
    pass
'''


CLOUDINARY_UPLOAD_FN = '''
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
'''


# ============================================================
# PATCH 3: Updated /speak to upload + save URL
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

        # Upload to Cloudinary + save history (best effort)
        if device_id and DATABASE_URL:
            try:
                init_db()
                audio_url = upload_to_cloudinary(wav_bytes, voice, device_id)
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO history (device_id, text, voice, speed, audio_url) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (device_id, text[:800], voice, speed, audio_url),
                        )
                    conn.commit()
            except Exception as e:
                print(f"[db] history insert failed: {e}")

        response = send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name=f"{voice}.wav",
        )
        return response

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
# PATCH 4: Updated /history to include audio_url
# ============================================================
NEW_HISTORY_GET = '''@app.route("/history", methods=["GET"])
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
# PATCH 5: Frontend — replay from Cloudinary URL when present
# ============================================================
NEW_REPLAY = '''      btn.onclick = () => {
        if (h.audio_url) {
          // Instant replay from Cloudinary
          new Audio(h.audio_url).play();
          return;
        }

        // Fallback: regenerate
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
        .then(blob => {
          new Audio(URL.createObjectURL(blob)).play();
        })
        .catch(e => {
          console.error('Replay error:', e);
          alert('Could not replay. Try again.');
        })
        .finally(() => {
          btn.disabled = false;
          btn.textContent = '\\u25b6 Replay';
        });
      };'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Cloudinary Audio Storage")
    print("=" * 60)

    # ---------- requirements.txt ----------
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

    # Add cloudinary import near the top
    if 'import cloudinary' not in src:
        anchor = "from flask_cors import CORS"
        if anchor in src:
            src = src.replace(anchor, anchor + "\n\n" + CLOUDINARY_IMPORT, 1)
            changes.append("cloudinary import")

    # Add the upload function before "# ROUTES"
    if 'def upload_to_cloudinary' not in src:
        anchor = "# ============================================================\n# ROUTES"
        if anchor in src:
            src = src.replace(anchor, CLOUDINARY_UPLOAD_FN + "\n" + anchor, 1)
            changes.append("cloudinary upload function")

    # Replace the /speak route
    speak_pattern = re.compile(
        r'@app\.route\("/speak", methods=\["POST", "OPTIONS"\]\)\s*\ndef speak\(\):.*?(?=\n# ---------- FAVORITES|\n# =+\s*\n# FAVORITES)',
        re.DOTALL
    )
    if speak_pattern.search(src):
        src = speak_pattern.sub(NEW_SPEAK + "\n\n", src, count=1)
        changes.append("/speak route")

    # Replace the /history GET route
    hist_pattern = re.compile(
        r'@app\.route\("/history", methods=\["GET"\]\)\s*\ndef get_history\(\):.*?(?=\n@app\.route\("/history", methods=\["DELETE")',
        re.DOTALL
    )
    if hist_pattern.search(src):
        src = hist_pattern.sub(NEW_HISTORY_GET + "\n\n", src, count=1)
        changes.append("/history GET route")

    # Add audio_url column migration (safe if already exists)
    old_create = 'CREATE TABLE IF NOT EXISTS history ('
    new_create = '''CREATE TABLE IF NOT EXISTS history (
                            audio_url  TEXT,'''
    if old_create in src and 'audio_url' not in src.split('CREATE TABLE IF NOT EXISTS history')[1][:200]:
        src = src.replace(old_create, new_create, 1)
        # Also add ALTER TABLE for existing tables
        alter_sql = '''
                    # Add column if it doesn't exist (safe for existing DBs)
                    try:
                        cur.execute("ALTER TABLE history ADD COLUMN IF NOT EXISTS audio_url TEXT;")
                    except Exception:
                        pass
'''
        # Insert right after the CREATE INDEX statement
        old_index = 'CREATE INDEX IF NOT EXISTS idx_history_device'
        if old_index in src:
            # Find the end of the CREATE INDEX statement
            idx_pos = src.find(old_index)
            end_pos = src.find('"""', idx_pos)
            if end_pos != -1:
                src = src[:end_pos] + alter_sql + src[end_pos:]
                changes.append("audio_url column migration")

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
    changes = []

    # Replace the replay button handler
    old_handler = re.search(
        r'btn\.onclick = async \(\) => \{.*?\n      \};',
        src,
        re.DOTALL
    )

    if old_handler:
        src = src[:old_handler.start()] + NEW_REPLAY + src[old_handler.end():]
        changes.append("replay handler")

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
    print()
    print(" 1. Get your Cloudinary URL:")
    print("    - Sign up at cloudinary.com (free tier: 25GB storage)")
    print("    - Dashboard shows: cloudinary://API_KEY:API_SECRET@CLOUD_NAME")
    print()
    print(" 2. Add to Vercel env vars:")
    print("    CLOUDINARY_URL = cloudinary://...")
    print()
    print(" 3. Add to local env (for testing):")
    print("    set CLOUDINARY_URL=cloudinary://...")
    print()
    print(" 4. Install:")
    print("    pip install cloudinary")
    print()
    print(" 5. Deploy:")
    print("    vercel --prod")
    print()
    print(" What happens:")
    print("   • Every generation uploads to Cloudinary")
    print("   • URL saved in the history table")
    print("   • Replay plays the URL directly — instant")
    print("   • Old entries (no URL) still regenerate")
    print()
    print("=" * 60)


if __name__ == "__main__":
    patch()