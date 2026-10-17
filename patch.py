"""
Fix the low-start audio issue.
- Normalizes the WAV to a consistent volume.
- Boosts the first 200ms so the first word starts at full volume.
- Trims any leading silence.
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


# New helper to fix the audio
FIX_AUDIO_HELPER = '''
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
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Fix Low-Start Audio")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # 1. Insert the helper function before "# ROUTES"
    if 'def fix_audio_attack' not in src:
        anchor = "# ============================================================\n# ROUTES"
        if anchor in src:
            src = src.replace(anchor, FIX_AUDIO_HELPER + "\n" + anchor, 1)
            print("  [OK] Added fix_audio_attack() function")
        else:
            print("  WARN: Could not find ROUTES anchor")

    # 2. Call the fixer inside /speak after generating the WAV
    old_speak = '''        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")'''

    new_speak = '''        # Generate (with silent retries)
        print(f"[speak] generating: {text[:40]!r} voice={voice}")
        wav_bytes = generate_speech(text, voice, speed)
        print(f"[speak] generated {len(wav_bytes)} bytes")

        # Fix the quiet-start issue
        wav_bytes = fix_audio_attack(wav_bytes)
        print(f"[speak] after audio fix: {len(wav_bytes)} bytes")'''

    if old_speak in src:
        src = src.replace(old_speak, new_speak, 1)
        print("  [OK] Wired fix_audio_attack into /speak")
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
    print("   1. Trims leading silence.")
    print("   2. Normalizes to -1 dBFS.")
    print("   3. Boosts the first 250ms if it's quieter than the rest.")
    print("   4. Falls back to original audio if anything fails.")
    print("=" * 60)


if __name__ == "__main__":
    patch()