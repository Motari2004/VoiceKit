"""
VoiceKit — Cloudinary (final, verified)
Replaces the entire Cloudinary block + /speak route with a clean
version that:
  - Reads 3 env vars AND falls back to CLOUDINARY_URL
  - Logs every step
  - Uploads synchronously (guaranteed to complete before response)
  - Never returns audio_url=None silently
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, "app.py")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


CLOUDINARY_BLOCK = '''# ============================================================
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
'''


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

        # 1. Generate audio
        print(f"[speak] generating: {text[:40]!r} voice={voice} speed={speed}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")

        # 2. Upload to Cloudinary FIRST (synchronous, blocking)
        audio_url = None
        if device_id:
            print(f"[speak] uploading to cloudinary...")
            audio_url = upload_to_cloudinary(wav_bytes, voice, device_id)
            print(f"[speak] cloudinary result: {audio_url}")

        # 3. Save to history
        if device_id and DATABASE_URL:
            try:
                init_db()
                db_execute(
                    "INSERT INTO history (device_id, text, voice, speed, audio_url) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (device_id, text[:800], voice, speed, audio_url),
                )
                print(f"[speak] history saved with audio_url={audio_url}")
            except Exception as e:
                print(f"[speak] history insert failed: {e}")

        # 4. Return WAV
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
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)[:250]}), 500
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Cloudinary Final Fix")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace the entire Cloudinary block ----------
    # Match from "# CLOUDINARY" up to the next "# ======" section
    cloud_pattern = re.compile(
        r'# =+\s*\n# CLOUDINARY.*?(?=\n# =+\s*\n# [A-Z])',
        re.DOTALL
    )

    if cloud_pattern.search(src):
        src = cloud_pattern.sub(CLOUDINARY_BLOCK + "\n\n", src, count=1)
        changes.append("cloudinary block")
    else:
        # Insert before the UPSTREAM block
        anchor = "# ============================================================\n# UPSTREAM"
        if anchor in src:
            src = src.replace(anchor, CLOUDINARY_BLOCK + "\n" + anchor, 1)
            changes.append("cloudinary block inserted")
        else:
            print("  ERROR: cannot find anchor for Cloudinary block")
            return

    # ---------- 2) Replace the /speak route ----------
    speak_pattern = re.compile(
        r'@app\.route\("/speak", methods=\["POST", "OPTIONS"\]\).*?(?=\n# -+ FAVORITES|\n# =+\s*\n# FAVORITES)',
        re.DOTALL
    )

    if speak_pattern.search(src):
        src = speak_pattern.sub(NEW_SPEAK + "\n\n", src, count=1)
        changes.append("/speak route")
    else:
        print("  WARN: /speak route not found")

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
    print(" Now:")
    print("   1. Deploy: vercel --prod")
    print("   2. Generate a NEW phrase (old entries won't update)")
    print("   3. Check Vercel function logs — you'll see:")
    print("        [cloudinary] env check: cloud=set key=set secret=set")
    print("        [cloudinary] configured for cloud: dndxu5ak")
    print("        [cloudinary] uploading XXXX bytes as voicekit/...wav...")
    print("        [cloudinary] upload OK: https://res.cloudinary.com/...")
    print("        [speak] history saved with audio_url=https://...")
    print()
    print(" If you see 'env check: cloud=MISSING', the Vercel env")
    print(" vars aren't being read. Add them and REDEPLOY.")
    print()
    print("=" * 60)


if __name__ == "__main__":
    patch()