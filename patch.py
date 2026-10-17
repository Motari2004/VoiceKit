"""
Swap the voice list order so Male appears before Female.
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
    print(" VoiceKit — Male Voices First")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Find the loop that iterates genders and swap the order
    old_loop = "['Female', 'Male'].forEach(gender => {"
    new_loop = "['Male', 'Female'].forEach(gender => {"

    if old_loop in src:
        src = src.replace(old_loop, new_loop, 1)
        print("  [OK] Swapped order: Male first, then Female")
    elif new_loop in src:
        print("  [SKIP] Male is already first")
    else:
        print("  WARN: Could not find the gender loop")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()