"""
Fix: restore the sidebar footer text with version v1.2
- Remove any misplaced v1.2 next to the brand name
- Update the sidebar footer to say "VoiceKit v1.2"
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
    print(" VoiceKit — Fix Version Placement")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # 1) Remove the wrongly-placed v1.2 next to the brand name
    src = re.sub(
        r'\s*<span class="brand-version">[^<]*</span>',
        '',
        src
    )

    # 2) Fix the sidebar footer to say "VoiceKit v1.2"
    footer_pattern = re.compile(
        r'<div class="sidebar-footer">.*?</div>',
        re.DOTALL
    )

    new_footer = '''<div class="sidebar-footer">
    <span style="opacity: 0.6;">VoiceKit v1.2</span>
  </div>'''

    if footer_pattern.search(src):
        src = footer_pattern.sub(new_footer, src, count=1)
        changes.append("sidebar footer")
    else:
        # Insert before </aside>
        aside_close = "</aside>"
        if aside_close in src:
            src = src.replace(
                aside_close,
                new_footer + "\n" + aside_close,
                1
            )
            changes.append("sidebar footer (inserted)")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print(" Result:")
    print("   • Removed the stray 'v1.2' next to VoiceKit brand")
    print("   • Sidebar footer now shows: 'VoiceKit v1.2'")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()