"""
Remove the GET /health endpoint from the API Reference UI.
(Leaves the backend route intact, just hides it from the docs).
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
    print(" VoiceKit — Remove /health from Docs")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # Find the specific endpoint card for /health and remove it
    health_card_pattern = re.compile(
        r'<div class="endpoint-card">\s*<div><span class="endpoint-method get">GET</span><span class="endpoint-path">/health</span></div>\s*<div class="endpoint-desc">Service health and cache status.</div>\s*</div>',
        re.DOTALL
    )

    if health_card_pattern.search(src):
        src = health_card_pattern.sub('', src)
        print("  [OK] Removed /health card from API Reference")
    else:
        # Fallback: match just the line if the structure is slightly different
        fallback = re.compile(
            r'<div><span class="endpoint-method get">GET</span><span class="endpoint-path">/health</span></div>\s*<div class="endpoint-desc">Service health and cache status.</div>',
            re.DOTALL
        )
        if fallback.search(src):
            # We need to remove the parent div too
            src = re.sub(
                r'<div class="endpoint-card">\s*(<div><span class="endpoint-method get">GET</span><span class="endpoint-path">/health</span></div>\s*<div class="endpoint-desc">Service health and cache status.</div>)\s*</div>',
                '',
                src,
                flags=re.DOTALL
            )
            print("  [OK] Removed /health card (fallback)")
        else:
            print("  WARN: Could not find /health card")

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