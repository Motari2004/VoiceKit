"""
Use the real vintage mic image (with its purple background) as the brand mark.
1. Creates a `static/` folder
2. Tells Flask to serve static files
3. Replaces the brand mark with an <img> tag
4. Keeps everything else the same
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")
APP  = os.path.join(BASE, "app.py")
STATIC_DIR = os.path.join(BASE, "static")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


NEW_BRAND = (
    '<img src="/static/mic.png" alt="VoiceKit" '
    'style="width:36px; height:36px; border-radius:9px; object-fit:cover; '
    'box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35);">'
)


def patch():
    print("=" * 60)
    print(" VoiceKit — Image Brand Mark")
    print("=" * 60)

    # 1. Create static folder
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR)
        print(f"  created -> {os.path.relpath(STATIC_DIR, BASE)}")
    else:
        print(f"  static/ already exists")

    # 2. Ensure app.py serves static files
    if not os.path.exists(APP):
        print(f"  ERROR: {APP} not found")
        return
    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        app_src = f.read()

    if 'static_folder="static"' not in app_src and "static_folder='static'" not in app_src:
        # Replace the Flask() call to include static_folder
        old_flask = "app = Flask(__name__)"
        new_flask = 'app = Flask(__name__, static_folder="static", static_url_path="/static")'
        if old_flask in app_src:
            app_src = app_src.replace(old_flask, new_flask, 1)
            with open(APP, "w", encoding="utf-8") as f:
                f.write(app_src)
            print("  [OK] Flask now serves /static/*")
        else:
            print("  WARN: could not find Flask(__name__) call in app.py")
    else:
        print("  Flask static folder already configured")

    # 3. Replace the brand mark in index.html
    if not os.path.exists(HTML):
        print(f"  ERROR: {HTML} not found")
        return
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    pattern = re.compile(
        r'<div class="brand-mark"[^>]*>.*?</div>',
        re.DOTALL
    )

    if pattern.search(src):
        src = pattern.sub(NEW_BRAND, src, count=1)
        with open(HTML, "w", encoding="utf-8") as f:
            f.write(src)
        print("  [OK] Brand mark replaced with <img>")
    else:
        print("  WARN: could not find brand-mark div")

    print()
    print("=" * 60)
    print(" NEXT STEP — Save the image")
    print("=" * 60)
    print()
    print(" Save your microphone image as a PNG at:")
    print()
    print(f"   {STATIC_DIR}\\mic.png")
    print()
    print(" Requirements:")
    print("   • Square (e.g., 512x512 or 1024x1024)")
    print("   • PNG or JPG format")
    print("   • Filename must be exactly: mic.png")
    print("   • Keep the purple background in the image")
    print()
    print(" Then deploy:")
    print("   vercel --prod")
    print()
    print(" Or test locally:")
    print("   python app.py")
    print("   open http://localhost:10000")
    print()
    print("=" * 60)


if __name__ == "__main__":
    patch()