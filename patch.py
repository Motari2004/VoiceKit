"""
Move the hamburger button down on mobile so it aligns
with the sidebar's top padding.
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
  /* ---------- HAMBURGER: MOVE DOWN ON MOBILE ---------- */
  @media (max-width: 900px) {
    .menu-toggle {
      top: 30px !important;   /* was 16px — now 30px */
      left: 16px !important;
    }
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Move Hamburger Down")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'HAMBURGER: MOVE DOWN ON MOBILE' in src:
        print("  Already applied.")
        return

    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Hamburger moved down to 30px")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()