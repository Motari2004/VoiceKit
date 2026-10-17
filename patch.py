"""
Clear the default text in the Generate box.
Remove 'Listen closely' from voice previews so it doesn't leak into new generations.
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
    print(" VoiceKit — Clear Default Text")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # 1. Clear the textarea default text
    # Match the <textarea ...> ... </textarea> block
    textarea_pattern = re.compile(
        r'<textarea id="text"([^>]*)>.*?</textarea>',
        re.DOTALL
    )
    
    if textarea_pattern.search(src):
        src = textarea_pattern.sub(
            r'<textarea id="text"\1></textarea>',
            src,
            count=1
        )
        print("  [OK] Cleared default textarea text")
    else:
        print("  WARN: Could not find textarea")

    # 2. Replace 'Listen closely' in the voice preview function
    # We'll change it to something neutral but still short so preview works
    old_preview_text = 'text: "Listen closely. You can barely tell this is not me talking.",'
    new_preview_text = 'text: "This is a preview of the voice.",'
    
    if old_preview_text in src:
        src = src.replace(old_preview_text, new_preview_text, 1)
        print("  [OK] Updated voice preview text")

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
    print()
    print(" The text box will now be empty when the page loads.")
    print("=" * 60)


if __name__ == "__main__":
    patch()