"""
Make the sidebar fit the viewport on mobile without scrolling.
Tighter spacing so all nav items are visible at once.
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
  /* ---------- SIDEBAR: FIT IN VIEWPORT (MOBILE) ---------- */
  @media (max-width: 900px) {
    .sidebar {
      padding-top: 76px !important;
      padding-bottom: 16px !important;
      overflow-y: hidden !important;   /* no scroll inside the sidebar */
      height: 100vh !important;
      height: 100dvh !important;       /* dynamic viewport height for mobile browsers */
      display: flex !important;
      flex-direction: column !important;
    }

    /* Brand — tighter */
    .sidebar-brand {
      padding: 4px 10px 12px !important;
      margin-bottom: 4px !important;
    }

    /* Nav sections — tighter spacing */
    .nav-section {
      margin-bottom: 12px !important;
    }

    .nav-label {
      font-size: 0.6rem !important;
      margin-bottom: 4px !important;
      padding: 0 10px !important;
    }

    .nav-btn {
      padding: 7px 10px !important;
      font-size: 0.82rem !important;
      gap: 9px !important;
    }

    .nav-icon {
      width: 15px !important;
      height: 15px !important;
    }

    .nav-badge {
      font-size: 0.6rem !important;
      padding: 1px 5px !important;
    }

    /* Footer pinned to the bottom, smaller */
    .sidebar-footer {
      margin-top: auto !important;
      padding-top: 12px !important;
      font-size: 0.68rem !important;
    }
  }

  /* Extra small phones — squeeze a bit more */
  @media (max-width: 480px) {
    .sidebar {
      padding-top: 72px !important;
    }

    .sidebar-brand {
      padding: 2px 10px 10px !important;
    }

    .nav-section {
      margin-bottom: 10px !important;
    }

    .nav-btn {
      padding: 6px 10px !important;
      font-size: 0.78rem !important;
    }

    .nav-icon {
      width: 14px !important;
      height: 14px !important;
    }
  }

  /* Landscape phones — no vertical room, use two columns */
  @media (max-height: 500px) and (orientation: landscape) {
    .sidebar {
      padding-top: 12px !important;
      overflow-y: auto !important;
    }

    .sidebar-brand {
      padding: 0 10px 8px !important;
    }
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Sidebar Fits Viewport")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'SIDEBAR: FIT IN VIEWPORT' in src:
        print("  Already applied.")
        return

    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Sidebar now fits the viewport")
    print()
    print(" What changed:")
    print("   • No scroll inside the sidebar on mobile")
    print("   • Tighter nav spacing (smaller padding, gaps)")
    print("   • Brand row compressed")
    print("   • Footer pinned to the bottom")
    print("   • Extra squeeze on phones under 480px")
    print("   • Landscape mode falls back to scroll")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()