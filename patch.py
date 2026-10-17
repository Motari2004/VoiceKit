"""
Replace long presets with short, professional one-liners.
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
        <button data-p="In today's news, a major breakthrough.">News Brief</button>
        <button data-p="Relax. Close your eyes.">Meditation</button>
      </div>'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Short Professional Presets")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Replace the quick phrases div
    pattern = re.compile(r'<div class="quick">.*?</div>', re.DOTALL)
    if pattern.search(src):
        src = pattern.sub(NEW_QUICK_BUTTONS, src, count=1)
        print("  [OK] Replaced quick phrases with short one-liners")
    else:
        print("  WARN: Could not find the quick phrases div")

    # 2. Update the default textarea text to a short one too
    old_default = '<textarea id="text" maxlength="800" placeholder="Type or paste your script here...">Welcome back to the show. Today we are exploring the future of AI and how it is changing the way we create.</textarea>'
    new_default = '<textarea id="text" maxlength="800" placeholder="Type or paste your script here...">Welcome back to the show.</textarea>'

    if old_default in src:
        src = src.replace(old_default, new_default, 1)
        print("  [OK] Updated default text to a short sentence")
    else:
        # Regex fallback in case it was slightly different
        src = re.sub(
            r'(<textarea id="text" maxlength="800" placeholder="Type or paste your script here...">).*?(</textarea>)',
            r'\1Welcome back to the show.\2',
            src,
            count=1
        )
        print("  [OK] Updated default text (fallback)")

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