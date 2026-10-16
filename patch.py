"""
Fix sidebar nav badge contrast.
When the Voices nav button is active, its badge turns white on white.
Force dark text on the badge in both states.
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
  /* ---------- FIX: NAV BADGE CONTRAST ---------- */
  .nav-badge {
    background: var(--bg);
    color: var(--text-muted);
    border: 1px solid var(--border);
  }

  .nav-btn.active .nav-badge {
    background: #ffffff;
    color: #0a0a0a;
    border-color: #ffffff;
    font-weight: 700;
  }

  /* ---------- FIX: NAV BUTTON ACTIVE STATE ---------- */
  /* When the accent is white, active nav background should be subtle grey,
     not white, or the text disappears. */

  .nav-btn.active {
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
  }

  .nav-btn.active .nav-icon {
    color: #ffffff;
  }

  .nav-btn.active:hover {
    background: rgba(255, 255, 255, 0.12);
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Nav Badge Contrast Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'FIX: NAV BADGE CONTRAST' in src:
        print("  Already applied.")
        return

    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Added nav badge + active nav contrast fix")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Fixed:")
    print("   • Voices badge '54' — now white pill with black text when active")
    print("   • Inactive badge — subtle background, readable text")
    print("   • Active nav button — soft grey instead of full white")
    print("   • Icon in active nav — bright white")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" Or hard-refresh: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()