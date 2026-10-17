"""
Change the curl example to a Windows CMD compatible version.
Uses ^ for line continuation and escaped double quotes.
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


NEW_CURL = '''<code class="api-code">curl -X POST https://voicekit-prod.vercel.app/speak ^
  -H "Content-Type: application/json" ^
  -d "{\\"text\\": \\"Welcome to the show. Today we are exploring the future of AI voice synthesis.\\", \\"voice\\": \\"af_alloy\\", \\"speed\\": 1.0}" ^
  -o intro.wav</code>'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Windows CMD Curl Example")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # Find and replace the old curl block
    pattern = re.compile(
        r'<code class="api-code">curl -X POST https://voicekit-prod\.vercel\.app/speak.*?-o intro\.wav</code>',
        re.DOTALL
    )

    if pattern.search(src):
        src = pattern.sub(NEW_CURL, src, count=1)
        print("  [OK] Replaced curl example with Windows CMD compatible version")
    else:
        print("  WARN: Could not find the curl example")

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
    print(" The new example uses:")
    print("   ^ (caret) for line continuation in CMD")
    print("   \\\" (escaped quotes) for the JSON payload")
    print()
    print(" You can copy-paste it directly into Windows CMD.")
    print("=" * 60)


if __name__ == "__main__":
    patch()