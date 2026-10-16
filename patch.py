"""
Force the sidebar content down on mobile with !important.
The earlier patch was overridden by a later rule.
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
  /* ---------- FORCE: SIDEBAR CONTENT BELOW HAMBURGER ---------- */
  @media (max-width: 900px) {
    .sidebar,
    aside.sidebar,
    #sidebar {
      padding-top: 90px !important;
    }

    /* Also push the very first child (brand row) down */
    .sidebar > .sidebar-brand,
    .sidebar > :first-child {
      margin-top: 0 !important;
    }
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Force Sidebar Padding")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'FORCE: SIDEBAR CONTENT BELOW HAMBURGER' in src:
        print("  Already applied.")
        return

    # Insert this at the very end of the <style> block so it wins the cascade
    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Sidebar padding forced with !important")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()