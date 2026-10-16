"""
Nudge the hamburger up from 30px to 22px.
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


def patch():
    print("=" * 60)
    print(" VoiceKit — Nudge Hamburger Up")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Replace top: 30px in the hamburger rule
    pattern = re.compile(
        r'(\.menu-toggle\s*\{[^}]*?top:\s*)30px(\s*!important)',
        re.DOTALL
    )

    if pattern.search(src):
        src = pattern.sub(r'\g<1>22px\g<2>', src)
    else:
        # Fallback: any top: 30px !important on .menu-toggle
        src = src.replace("top: 30px !important", "top: 22px !important")

    if src == original:
        print("  No changes made — couldn't find top: 30px")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Hamburger moved up: 30px → 22px")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()