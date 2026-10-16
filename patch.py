"""
VoiceKit — Port 10000 Patch
- Changes the server port from 5000 to 10000
- Updates all API doc URLs in templates/index.html
- Backs up both files first
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP  = os.path.join(BASE, "app.py")
HTML = os.path.join(BASE, "templates", "index.html")

NEW_PORT = "10000"
OLD_PORT = "5000"


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.basename(path)}.bak")


def patch_app():
    print(f"\n[1/2] Patching app.py")
    if not os.path.exists(APP):
        print(f"  ERROR: {APP} not found")
        return False
    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # 1) PORT constant
    if re.search(r'^PORT\s*=\s*\d+', src, re.M):
        src = re.sub(r'^PORT\s*=\s*\d+', f'PORT = {NEW_PORT}', src, flags=re.M)
        changes.append("PORT constant")
    else:
        # Insert PORT after SPACE_URL if missing
        src = re.sub(
            r'(SPACE_URL\s*=\s*"[^"]+")',
            rf'\1\nPORT = {NEW_PORT}',
            src,
            count=1
        )
        changes.append("PORT inserted")

    # 2) app.run port
    if re.search(r'app\.run\([^)]*port\s*=\s*\d+', src):
        src = re.sub(
            r'(app\.run\([^)]*port\s*=\s*)\d+',
            rf'\g<1>{NEW_PORT}',
            src
        )
        changes.append("app.run port")

    # 3) Any remaining "localhost:5000" in the app.py banner
    if f"localhost:{OLD_PORT}" in src:
        src = src.replace(f"localhost:{OLD_PORT}", f"localhost:{NEW_PORT}")
        changes.append("banner URLs")

    if src == original:
        print("  [SKIP] app.py already on port 10000")
        return True

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Updated: {', '.join(changes)}")
    return True


def patch_html():
    print(f"\n[2/2] Patching templates/index.html")
    if not os.path.exists(HTML):
        print(f"  ERROR: {HTML} not found")
        return False
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Replace all localhost:5000 occurrences with localhost:10000
    count = src.count(f"localhost:{OLD_PORT}")
    src = src.replace(f"localhost:{OLD_PORT}", f"localhost:{NEW_PORT}")

    # Also handle bare :5000 in code examples
    count2 = src.count(f":{OLD_PORT}/")
    src = src.replace(f":{OLD_PORT}/", f":{NEW_PORT}/")

    # And bare ":5000" endpoints
    count3 = src.count(f"port={OLD_PORT}") + src.count(f"port :{OLD_PORT}")

    if src == original:
        print("  [SKIP] index.html already uses port 10000")
        return True

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Replaced {count + count2 + count3} port references")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print(" VoiceKit — Port 10000 Patch")
    print("=" * 60)

    ok1 = patch_app()
    ok2 = patch_html()

    print()
    print("=" * 60)
    if ok1 and ok2:
        print(" DONE")
        print("=" * 60)
        print()
        print(" Run: python app.py")
        print(" Open: http://localhost:10000")
        print()
        print(" Backups saved as:")
        print("   app.py.bak")
        print("   templates\\index.html.bak")
        print()
        print(" To restore:")
        print("   copy app.py.bak app.py")
        print("   copy templates\\index.html.bak templates\\index.html")
    else:
        print(" Some steps failed. Check the output above.")
    print("=" * 60)