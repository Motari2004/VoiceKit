"""
VoiceKit — Cloudinary Upload (async, after response)
- WAV is sent to the user immediately
- Cloudinary upload + DB history save happens in a background thread
- User sees audio in ~2.5s; Cloudinary catches up in the background
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP  = os.path.join(BASE, "app.py")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


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
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Cloudinary Upload (after response)")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    speak_pattern = re.compile(
        r'@app\.route\("/speak", methods=\["POST", "OPTIONS"\]\)\s*\ndef speak\(\):.*?(?=\n# ---------- FAVORITES|\n# =+\s*\n# FAVORITES)',
        re.DOTALL
    )

    if speak_pattern.search(src):
        src = speak_pattern.sub(NEW_SPEAK + "\n\n", src, count=1)
        changes.append("/speak (async save)")

    if src == original:
        print("  No changes made.")
        return

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" New flow:")
    print("   1. User clicks Generate")
    print("   2. Server generates WAV (~2.5s)")
    print("   3. WAV is sent to user immediately")
    print("   4. Background thread uploads to Cloudinary")
    print("   5. Background thread saves history row")
    print()
    print(" The user sees no difference — the audio arrives the")
    print(" moment it's ready. Cloudinary + history catch up in")
    print(" the background (usually within 1-2 seconds after).")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" After generating, wait ~3 seconds then check History.")
    print(" Entries should have audio_url now.")
    print("=" * 60)


if __name__ == "__main__":
    patch()