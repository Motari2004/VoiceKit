"""
VoiceKit — Silent Retry on Warm-Up
- The server retries upstream up to 3 times with increasing delays
- Only returns 504 if ALL attempts fail
- The frontend already retries on 504 — this adds server-side retries too
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


NEW_CALL_UPSTREAM = '''def call_upstream(text, voice, speed, attempts=3):
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
                match = re.search(r'https://[^"]+audio\\.wav', r.text)
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

        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")

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
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Silent Retry")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace call_upstream ----------
    pattern = re.compile(
        r'def call_upstream\(.*?\n(?=\n\ndef generate_speech)',
        re.DOTALL
    )

    if pattern.search(src):
        src = pattern.sub(lambda m: NEW_CALL_UPSTREAM, src, count=1)
        changes.append("call_upstream (silent retry)")
    else:
        print("  WARN: could not find call_upstream")

    # ---------- 2) Replace /speak route ----------
    speak_pattern = re.compile(
        r'@app\.route\("/speak", methods=\["POST", "OPTIONS"\]\).*?(?=\n# -+ FAVORITES|\n# =+\s*\n# FAVORITES)',
        re.DOTALL
    )

    if speak_pattern.search(src):
        src = speak_pattern.sub(lambda m: NEW_SPEAK + "\n\n", src, count=1)
        changes.append("/speak route")
    else:
        print("  WARN: could not find /speak route")

    # ---------- 3) Also bump UPSTREAM_TIMEOUT if it's very short ----------
    if "UPSTREAM_TIMEOUT = 15" not in src and "UPSTREAM_TIMEOUT =" in src:
        src = re.sub(
            r'UPSTREAM_TIMEOUT\s*=\s*\d+',
            'UPSTREAM_TIMEOUT = 15',
            src
        )
        changes.append("UPSTREAM_TIMEOUT")

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
    print(" New behavior:")
    print("   • Server tries the HF Space up to 3 times")
    print("   • Waits 4s between attempt 1→2, 6s between 2→3")
    print("   • User sees nothing unless all 3 fail")
    print("   • Logs every attempt to Vercel console")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("=" * 60)


if __name__ == "__main__":
    patch()