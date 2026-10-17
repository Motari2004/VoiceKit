"""
Remove all audio processing (silence and volume fix) from Vercel.
Let the Hugging Face Space handle the audio processing.
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


def patch():
    print("=" * 60)
    print(" VoiceKit — Remove Vercel Audio Processing")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # 1. Revert the /speak route to NOT call the audio fixes
    old_speak = '''        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")

        # Fix the quiet-start issue
        wav_bytes = fix_audio_attack(wav_bytes)
        
        # Add 1 second of silence at the start
        wav_bytes = add_lead_silence(wav_bytes, seconds=1.0)
        print(f"[speak] after audio processing: {len(wav_bytes)} bytes")'''

    new_speak = '''        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")'''

    if old_speak in src:
        src = src.replace(old_speak, new_speak, 1)
        print("  [OK] Removed audio processing from /speak route")
    else:
        # Fallback: just remove the lines individually
        src = src.replace('        wav_bytes = fix_audio_attack(wav_bytes)\n', '')
        src = src.replace('        wav_bytes = add_lead_silence(wav_bytes, seconds=1.0)\n', '')
        src = src.replace('        print(f"[speak] after audio processing: {len(wav_bytes)} bytes")\n', '')
        print("  [OK] Removed audio processing lines (fallback)")

    # 2. Remove the fix_audio_attack function block
    pattern1 = re.compile(
        r'# =+\s*\n# AUDIO POST-PROCESSING\s*\n# =+\s*\n\ndef fix_audio_attack\(.*?(?=\n# =+|\n@app\.route|\Z)',
        re.DOTALL
    )
    if pattern1.search(src):
        src = pattern1.sub('', src)
        print("  [OK] Removed fix_audio_attack() function")

    # 3. Remove the add_lead_silence function block
    pattern2 = re.compile(
        r'# =+\s*\n# AUDIO POST-PROCESSING \(Lead-in Silence\)\s*\n# =+\s*\n\ndef add_lead_silence\(.*?(?=\n# =+|\n@app\.route|\Z)',
        re.DOTALL
    )
    if pattern2.search(src):
        src = pattern2.sub('', src)
        print("  [OK] Removed add_lead_silence() function")

    if src == original:
        print("  No changes made.")
        return

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" Vercel now sends the audio straight through.")
    print(" The 1.5s silence is handled entirely by Hugging Face.")
    print("=" * 60)


if __name__ == "__main__":
    patch()