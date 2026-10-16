"""
Replace the browser tab favicon with the mic.png image.
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
    print(" VoiceKit — Favicon Update")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # Match any existing <link rel="icon" ...>
    favicon_pattern = re.compile(
        r'<link rel="icon"[^>]*>',
        re.DOTALL
    )

    new_favicon = (
        '<link rel="icon" type="image/png" href="/static/mic.png">'
    )

    if favicon_pattern.search(src):
        src = favicon_pattern.sub(new_favicon, src, count=1)
        changes.append("favicon link")
    else:
        # No favicon — add one before </head>
        src = src.replace('</head>', '  ' + new_favicon + '\n</head>', 1)
        changes.append("favicon inserted")

    # Also add apple-touch-icon for mobile home screens
    if 'apple-touch-icon' not in src:
        src = src.replace(
            '</head>',
            '  <link rel="apple-touch-icon" href="/static/mic.png">\n</head>',
            1
        )
        changes.append("apple-touch-icon")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print(" Result:")
    print("   • Browser tab favicon = mic.png")
    print("   • Apple touch icon = mic.png (for iOS home screen)")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" NOTE: Browsers cache favicons aggressively.")
    print(" After deploy, do a HARD refresh: Ctrl + Shift + R")
    print(" Or open in an incognito window to see the new icon.")
    print("=" * 60)


if __name__ == "__main__":
    patch()