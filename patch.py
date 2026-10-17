"""
Add 1 second of silence before the audio starts.
This fixes the 'quiet start' issue and prevents browser clipping.
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


# New helper function
ADD_SILENCE_HELPER = '''
# ============================================================
# AUDIO POST-PROCESSING (Lead-in Silence)
# ============================================================
def add_lead_silence(wav_bytes, seconds=1.0):
    """
    Adds pure silence to the start of the WAV.
    Fixes the 'quiet start' issue and prevents browser clipping.
    """
    try:
        import numpy as np
        import soundfile as sf
        import io

        # Read WAV
        data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype='float32')
        
        # Create silence
        silence_samples = int(samplerate * seconds)
        
        if data.ndim > 1:
            # Stereo
            silence = np.zeros((silence_samples, data.shape[1]), dtype='float32')
        else:
            # Mono
            silence = np.zeros(silence_samples, dtype='float32')
        
        # Concatenate silence + audio
        new_data = np.concatenate([silence, data], axis=0)
        
        # Write back to WAV
        out = io.BytesIO()
        sf.write(out, new_data, samplerate, format='WAV', subtype='PCM_16')
        return out.getvalue()

    except Exception as e:
        print(f"[audio-silence] failed: {e}")
        return wav_bytes  # Return original if anything breaks
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Add 1 Second Lead Silence")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # 1. Insert the helper function before "# ROUTES"
    if 'def add_lead_silence' not in src:
        anchor = "# ============================================================\n# ROUTES"
        if anchor in src:
            src = src.replace(anchor, ADD_SILENCE_HELPER + "\n" + anchor, 1)
            print("  [OK] Added add_lead_silence() function")
        else:
            print("  WARN: Could not find ROUTES anchor")

    # 2. Call the silence function inside /speak after generating the WAV
    # Look for where we added fix_audio_attack earlier, or just after generate_speech
    old_speak = '''        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")

        # Fix the quiet-start issue
        wav_bytes = fix_audio_attack(wav_bytes)
        print(f"[speak] after audio fix: {len(wav_bytes)} bytes")'''

    new_speak = '''        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")

        # Fix the quiet-start issue
        wav_bytes = fix_audio_attack(wav_bytes)
        
        # Add 1 second of silence at the start
        wav_bytes = add_lead_silence(wav_bytes, seconds=1.0)
        print(f"[speak] after audio processing: {len(wav_bytes)} bytes")'''

    if old_speak in src:
        src = src.replace(old_speak, new_speak, 1)
        print("  [OK] Wired add_lead_silence into /speak")
    else:
        # Fallback: just add it after generate_speech if the old block wasn't found
        fallback_old = '''        wav_bytes = generate_speech(text, voice, speed)'''
        fallback_new = '''        wav_bytes = generate_speech(text, voice, speed)
        wav_bytes = add_lead_silence(wav_bytes, seconds=1.0)'''
        if fallback_old in src:
            src = src.replace(fallback_old, fallback_new, 1)
            print("  [OK] Wired add_lead_silence (fallback)")
        else:
            print("  WARN: Could not find /speak generation block")

    if src == original:
        print("  No changes made.")
        return

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" What it does:")
    print("   • Adds exactly 1.0 second of pure silence to the start of every WAV.")
    print("   • Prevents the browser from clipping the first word.")
    print("   • Fixes the 'quiet start' issue permanently.")
    print("=" * 60)


if __name__ == "__main__":
    patch()