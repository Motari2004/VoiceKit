"""
Raise contrast across the entire UI.
- Footer text darker -> brighter
- Muted icons brighter
- Dim text (--text-dim) lighter so it's readable
- Secondary text (--text-muted) brighter
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
  /* ---------- CONTRAST BOOST ---------- */
  :root {
    /* Brighter greys for readability on dark backgrounds */
    --text:        #f5f5f7;    /* was #f4f4f5 — nearly white */
    --text-muted:  #b0b0b8;    /* was #8a8a93 — now clearly readable */
    --text-dim:    #7a7a84;    /* was #5a5a63 — visible but subdued */
  }

  /* Sidebar footer */
  .sidebar-footer {
    color: var(--text-dim);
    font-size: 0.72rem;
  }

  .sidebar-footer a {
    color: var(--text-muted);
    font-weight: 500;
  }

  .sidebar-footer a:hover {
    color: var(--text);
  }

  /* Bottom footer */
  .footer {
    color: var(--text-muted);
    font-size: 0.78rem;
  }

  .footer a {
    color: var(--text-muted);
    font-weight: 500;
  }

  .footer a:hover {
    color: var(--text);
  }

  /* Nav icons — brighter by default */
  .nav-icon {
    color: var(--text-muted);
  }

  .nav-btn {
    color: var(--text-muted);
  }

  .nav-btn:hover .nav-icon {
    color: var(--text);
  }

  .nav-btn.active .nav-icon {
    color: var(--text);
  }

  /* Nav section labels */
  .nav-label {
    color: var(--text-dim);
    font-weight: 600;
  }

  /* Card titles and hints */
  .card-title {
    color: var(--text-muted);
  }

  .card-hint {
    color: var(--text-muted);
  }

  /* Chip play buttons — brighter icons */
  .chip-play {
    color: var(--text);
    border-color: rgba(255, 255, 255, 0.2);
    font-weight: 700;
  }

  .chip-play:hover {
    background: var(--text);
    color: var(--bg);
    border-color: var(--text);
  }

  .chip-play.playing {
    background: var(--text);
    color: var(--bg);
    border-color: var(--text);
  }

  /* Voice chip descriptions */
  .chip-desc {
    color: var(--text-muted);
  }

  /* Selected bar */
  .selected-bar .label {
    color: var(--text-muted);
  }

  .selected-bar .id {
    color: var(--text-muted);
  }

  /* Status text */
  .status {
    color: var(--text-muted);
  }

  /* Speed label */
  .speed-label {
    color: var(--text-muted);
  }

  /* Filter chips */
  .filter-chip {
    color: var(--text-muted);
  }

  .filter-chip:hover {
    color: var(--text);
  }

  /* Quick buttons */
  .quick button {
    color: var(--text-muted);
  }

  .quick button:hover {
    color: var(--text);
  }

  /* History meta */
  .history-item .meta {
    color: var(--text-muted);
  }

  /* Empty states */
  .empty {
    color: var(--text-muted);
  }

  /* Download and secondary buttons */
  .download-btn {
    color: var(--text-muted);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .download-btn:hover:not(:disabled) {
    color: var(--text);
    border-color: rgba(255, 255, 255, 0.35);
  }

  /* API code text is lighter */
  .api-code {
    color: #e0e0e0;
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Contrast Boost")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'CONTRAST BOOST' in src:
        print("  Already applied.")
        return

    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Contrast boost applied")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Brighter now:")
    print("   • --text:       #f5f5f7   (main text)")
    print("   • --text-muted: #b0b0b8   (secondary text, was #8a8a93)")
    print("   • --text-dim:   #7a7a84   (tertiary, was #5a5a63)")
    print()
    print(" Specifically:")
    print("   • Footer text is now clearly readable")
    print("   • Sidebar labels are brighter")
    print("   • Play buttons have stronger borders + brighter icons")
    print("   • Voice descriptions are easier to read")
    print("   • Card titles and hints are visible")
    print("   • API code text is lighter")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()