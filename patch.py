"""
Fix: Replay button hover turns everything white (invisible text).
Force dark text when the background is light, in all states.
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
  /* ---------- FIX: HISTORY REPLAY BUTTON CONTRAST ---------- */
  .history-item button {
    padding: 5px 11px;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    color: #b0b0b8;
    font-size: 0.7rem;
    font-weight: 500;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s ease;
    flex-shrink: 0;
  }

  .history-item button:hover {
    background: #ffffff;
    border-color: #ffffff;
    color: #0a0a0a;   /* DARK text on white background */
    font-weight: 600;
  }

  .history-item button:active {
    transform: scale(0.98);
  }

  .history-item button:disabled {
    opacity: 0.6;
    cursor: wait;
  }

  /* Playing state — keep readable */
  .history-item button[data-playing="true"] {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.35);
    color: #ffffff;
    font-weight: 600;
  }

  .history-item button[data-playing="true"]:hover {
    background: #ffffff;
    border-color: #ffffff;
    color: #0a0a0a;
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Replay Button Hover Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'FIX: HISTORY REPLAY BUTTON CONTRAST' in src:
        print("  Already applied.")
        return

    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Hover contrast fix applied")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Fixed states:")
    print("   Idle     : transparent bg, muted text")
    print("   Hover    : WHITE bg, DARK text (visible)")
    print("   Playing  : light grey bg, white text")
    print("   Disabled : dimmed")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()