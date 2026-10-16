"""
Set the brand version text to 1.2
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


def patch():
    print("=" * 60)
    print(" VoiceKit — Set Version to 1.2")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # If brand-version span exists, update it
    if '<span class="brand-version">' in src:
        src = re.sub(
            r'<span class="brand-version">[^<]*</span>',
            '<span class="brand-version">v1.2</span>',
            src
        )
        changes.append("updated to v1.2")
    else:
        # Re-add it after the brand-name span
        pattern = re.compile(
            r'(<span class="brand-name">VoiceKit</span>)',
            re.DOTALL
        )
        if pattern.search(src):
            src = pattern.sub(
                r'\1\n      <span class="brand-version">v1.2</span>',
                src,
                count=1
            )
            changes.append("re-added as v1.2")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()