"""
Update the API Reference examples to use af_alloy instead of am_michael.
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


def patch():
    print("=" * 60)
    print(" VoiceKit — Use af_alloy in API Examples")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Replace the voice in the three examples
    src = src.replace('"voice": "am_michael"', '"voice": "af_alloy"')
    src = src.replace('voice: "am_michael"', 'voice: "af_alloy"')

    # Also update the output filename since "podcast_intro" implies a male broadcaster
    src = src.replace('-o podcast_intro.wav', '-o intro.wav')
    src = src.replace('"podcast_intro.wav"', '"intro.wav"')

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Changed voice to af_alloy and filename to intro.wav")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()