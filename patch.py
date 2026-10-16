"""
Add automatic retry to the upstream call.
The HF Space is often cold on first request. This makes the proxy
try again after a short delay before giving up.
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


NEW_CALL = '''def call_upstream(text, voice, speed, attempts=2):
    """
    Forward to the HF Space and return WAV bytes.
    Retries once if the first attempt fails — the Space is often cold
    on the first request after idle.
    """
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            # ---------- STEP 1: start job ----------
            r = requests.post(
                f"{UPSTREAM}/gradio_api/call/tts",
                json={"data": [text, voice, speed]},
                timeout=UPSTREAM_TIMEOUT,
            )
            r.raise_for_status()

            eid = r.json().get("event_id")
            if not eid:
                raise RuntimeError("Upstream did not return an event_id")

            # ---------- STEP 2: poll for result ----------
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
                raise TimeoutError("Upstream did not return audio in time")

            # ---------- STEP 3: download WAV ----------
            r = requests.get(audio_url, timeout=UPSTREAM_TIMEOUT)
            r.raise_for_status()
            return r.content

        except (requests.Timeout, TimeoutError) as e:
            last_error = e
            if attempt < attempts:
                time.sleep(1.5)  # wait before retry
                continue
            raise

        except Exception:
            raise

    raise last_error or TimeoutError("Upstream failed")


'''

NEW_SPEAK_ROUTE = '''@app.route("/speak", methods=["POST", "OPTIONS"])
def speak():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data  = request.get_json() or {}
        text  = (data.get("text") or "").strip()
        voice = (data.get("voice") or "am_adam").strip()
        speed = float(data.get("speed", 1.0))

        if not text:
            return jsonify({"error": "Missing 'text'"}), 400

        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                "error": f"Text too long (max {MAX_TEXT_LENGTH} chars)"
            }), 400

        speed = max(MIN_SPEED, min(MAX_SPEED, speed))

        wav_bytes = generate_speech(text, voice, speed)

        return send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name=f"{voice}.wav",
        )

    except requests.Timeout:
        return jsonify({
            "error": "Voice service is warming up. Try again in a moment."
        }), 504
    except TimeoutError:
        return jsonify({
            "error": "Voice service is warming up. Try again in a moment."
        }), 504
    except requests.HTTPError as e:
        return jsonify({
            "error": f"Upstream error: {e.response.status_code}"
        }), 502
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500


'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Upstream Retry Patch")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- Replace call_upstream ----------
    match = re.search(
        r'def call_upstream\(.*?\n(?=\ndef |\n#|@app\.route)',
        src,
        re.DOTALL
    )
    if match:
        src = src[:match.start()] + NEW_CALL + src[match.end():]
        changes.append("call_upstream with retry")
    else:
        # Fallback: use regex on just the def
        match = re.search(
            r'def call_upstream\(.*?\n\n',
            src,
            re.DOTALL
        )
        if match:
            src = src[:match.start()] + NEW_CALL + src[match.end():]
            changes.append("call_upstream (fallback)")

    # ---------- Replace /speak route ----------
    speak_match = re.search(
        r'@app\.route\("/speak".*?\n(?=\n@app\.route|\n# ===|\nif __name__)',
        src,
        re.DOTALL
    )
    if speak_match:
        src = src[:speak_match.start()] + NEW_SPEAK_ROUTE + src[speak_match.end():]
        changes.append("speak route")

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
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" The proxy now retries once after a 1.5s delay.")
    print(" Cold-start failures should mostly disappear.")
    print("=" * 60)


if __name__ == "__main__":
    patch()