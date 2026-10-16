"""
Make the hamburger button stay in place when scrolling.
Adds explicit position: fixed on mobile.
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


NEW_CSS = '''
  /* ---------- HAMBURGER: FIXED POSITION ON MOBILE ---------- */
  @media (max-width: 900px) {
    .menu-toggle {
      position: fixed !important;
      top: 16px !important;
      left: 16px !important;
      z-index: 200 !important;
      will-change: transform;
    }
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Fixed Hamburger")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'HAMBURGER: FIXED POSITION ON MOBILE' in src:
        print("  Already applied.")
        return

    # Insert at the very end of the <style> block so it wins the cascade
    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Hamburger is now position: fixed")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()