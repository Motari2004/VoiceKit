"""
Fix play button contrast when playing.
The chip-play button turns white/light when active, but the icon
stays light too, so the play triangle disappears.

This patch forces dark icon color when playing.
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
  /* ---------- FIX: PLAY BUTTON CONTRAST ---------- */
  .chip-play {
    background: var(--bg);
    color: var(--text-muted);
    border: 1px solid var(--border-hi);
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
    font-size: 0.55rem;
    line-height: 1;
  }

  /* When the chip is selected, invert properly */
  .voice-chip.selected .chip-play {
    background: #0a0a0a;
    color: #ffffff;
    border-color: #0a0a0a;
  }

  .voice-chip.selected .chip-play:hover {
    background: #333333;
    color: #ffffff;
    border-color: #333333;
  }

  .voice-chip.selected .chip-play.playing {
    background: #0a0a0a;
    color: #ffffff;
    border-color: #0a0a0a;
  }

  /* Also fix any inline SVG inside the play button */
  .chip-play svg {
    width: 8px;
    height: 8px;
    fill: currentColor;
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Play Button Contrast Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'FIX: PLAY BUTTON CONTRAST' in src:
        print("  Already applied.")
        return

    src = src.replace('</style>', NEW_CSS + '\n</style>', 1)

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Play button contrast fix applied")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Fixed:")
    print("   • Idle: muted grey on dark (readable)")
    print("   • Hover: white bg, dark icon (clear)")
    print("   • Playing: white bg, dark icon (visible)")
    print("   • Selected chip: black bg, white icon (inverted)")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()