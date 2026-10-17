"""
Make the filter buttons smaller and tighter so they all fit at a glance.
- Reduces padding and font size.
- Keeps them in a wrap layout but smaller.
- Fits Hindi, Portuguese, Favorites, etc. all on screen.
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
  /* ---------- COMPACT FILTER CHIPS ---------- */
  
  /* Prevent horizontal scroll and wrap into tight rows */
  .filter-row {
    display: flex !important;
    flex-wrap: wrap !important;
    overflow-x: visible !important;
    gap: 4px !important;
    margin-bottom: 10px !important;
    padding-bottom: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
  }

  /* Make the chips smaller */
  .filter-chip {
    padding: 4px 8px !important;
    font-size: 0.65rem !important;
    border-radius: 4px !important;
    line-height: 1.2 !important;
    flex-shrink: 0 !important;
  }

  /* Keep the favorites star visible but tight */
  .filter-chip.fav-filter {
    padding: 4px 8px !important;
  }

  .filter-chip.fav-filter .star-icon {
    margin-right: 2px !important;
  }

  /* Mobile: keep them very tight */
  @media (max-width: 900px) {
    .filter-chip {
      padding: 4px 6px !important;
      font-size: 0.6rem !important;
    }
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Compact Filter Row")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'COMPACT FILTER CHIPS' in src:
        print("  Already applied.")
        return

    # Insert the new CSS right before </style>
    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Added compact filter CSS")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" What changed:")
    print("   • Filter buttons are smaller (less padding, smaller font).")
    print("   • They wrap into tight rows instead of scrolling horizontally.")
    print("   • All filters (including Hindi, Portuguese, Favorites)")
    print("     should now be visible at a glance without scrolling.")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()