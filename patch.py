"""
Remove the custom history/popstate back-button logic.
Let the browser's back button behave naturally.
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
    print(" VoiceKit — Remove Back Button Trapping")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Remove the entire "MOBILE BACK BUTTON HANDLING (FIXED)" block
    pattern = re.compile(
        r'// =+\s*\n// MOBILE BACK BUTTON HANDLING.*?(?=\n// =+|\n</script>|\Z)',
        re.DOTALL
    )

    if pattern.search(src):
        src = pattern.sub('', src)
        print("  [OK] Removed back button handling logic")

    # Also remove the older block just in case
    old_pattern = re.compile(
        r'// =+\s*\n// MOBILE BACK BUTTON HANDLING \(FIXED\)\s*\n// =+.*?(?=\n// =+|\n</script>|\Z)',
        re.DOTALL
    )
    if old_pattern.search(src):
        src = old_pattern.sub('', src)
        print("  [OK] Removed older back button logic")

    if src == original:
        print("  No changes made — logic not found.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" What changed:")
    print("   • Removed history.pushState / popstate listeners")
    print("   • Back button now behaves naturally")
    print("   • Users switch views using the hamburger menu")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()