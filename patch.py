"""
Force the API Reference examples to use speed: 1.0.
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
    print(" VoiceKit — Force API Speed to 1.0")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Replace the speed in all possible formats
    src = src.replace('"speed": 1.1', '"speed": 1.0')
    src = src.replace('speed: 1.1', 'speed: 1.0')
    src = src.replace('"speed": 1', '"speed": 1.0') # In case it got truncated
    src = src.replace('speed: 1,', 'speed: 1.0,')

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Set speed to 1.0 in all API examples")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()