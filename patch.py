"""
Make the News Brief and Meditation presets full sentences.
Keep the others short.
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


NEW_QUICK_BUTTONS = '''      <div class="quick">
        <button data-p="Welcome back to the show.">Podcast Intro</button>
        <button data-p="Chapter One. The story begins here.">Audiobook</button>
        <button data-p="Here is how it works.">Explainer</button>
        <button data-p="Introducing our new product.">Ad Read</button>
        <button data-p="In today's news, a major scientific breakthrough has been announced that could change the future of renewable energy.">News Brief</button>
        <button data-p="Relax. Close your eyes. Take a deep breath in, and slowly let it out. You are exactly where you need to be.">Meditation</button>
      </div>'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Full Sentences for News & Meditation")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Find the existing quick div and replace it
    pattern = re.compile(r'<div class="quick">.*?</div>', re.DOTALL)
    
    if pattern.search(src):
        src = pattern.sub(NEW_QUICK_BUTTONS, src, count=1)
        print("  [OK] Updated presets (News & Meditation are now full sentences)")
    else:
        print("  WARN: Could not find the quick phrases div")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()