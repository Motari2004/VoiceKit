"""
Fill the leftover sidebar space on mobile.
- Removes the forced 'hidden' scroll but keeps it fitting
- Makes buttons taller to use the space
- Spreads sections out so it looks intentional, not clustered
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
  /* ---------- SIDEBAR: FILL THE MOBILE SPACE ---------- */
  @media (max-width: 900px) {
    .sidebar {
      padding-top: 90px !important;
      padding-bottom: 24px !important;
      height: 100vh !important;
      height: 100dvh !important;
      display: flex !important;
      flex-direction: column !important;
      overflow-y: auto !important;  /* scroll only if truly needed */
    }

    /* Space out the whole nav */
    .sidebar .nav-section:first-of-type {
      margin-top: 12px !important;
    }

    .nav-section {
      margin-bottom: 24px !important;  /* more breathing room */
    }

    .nav-label {
      font-size: 0.68rem !important;
      margin-bottom: 10px !important;
      padding: 0 10px !important;
      color: var(--text-muted) !important;
    }

    /* Bigger, more comfortable buttons */
    .nav-btn {
      padding: 12px 12px !important;
      font-size: 0.92rem !important;
      gap: 12px !important;
      margin-bottom: 4px !important;
      border-radius: 10px !important;
    }

    .nav-icon {
      width: 18px !important;
      height: 18px !important;
    }

    .nav-badge {
      font-size: 0.68rem !important;
      padding: 2px 7px !important;
    }

    /* Brand row — give it room */
    .sidebar-brand {
      padding: 4px 10px 20px !important;
      margin-bottom: 12px !important;
    }

    /* Footer pinned to bottom, slightly bigger */
    .sidebar-footer {
      margin-top: auto !important;
      padding-top: 20px !important;
      font-size: 0.72rem !important;
      color: var(--text-dim) !important;
    }
  }

  /* Shorter phones — still fit without scroll */
  @media (max-width: 900px) and (max-height: 700px) {
    .sidebar {
      padding-top: 80px !important;
    }

    .nav-section {
      margin-bottom: 16px !important;
    }

    .nav-btn {
      padding: 10px 12px !important;
      font-size: 0.88rem !important;
    }
  }

  /* Very short screens */
  @media (max-width: 900px) and (max-height: 600px) {
    .sidebar {
      padding-top: 76px !important;
    }

    .nav-section {
      margin-bottom: 12px !important;
    }

    .nav-btn {
      padding: 8px 12px !important;
      font-size: 0.85rem !important;
    }
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Fill Sidebar Space")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'SIDEBAR: FILL THE MOBILE SPACE' in src:
        print("  Already applied.")
        return

    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Sidebar now fills space with comfortable spacing")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()