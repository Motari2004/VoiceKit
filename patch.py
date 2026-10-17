"""
VoiceKit — Server-Side Admin Rendering
1. Flask reads the device cookie and evaluates admin status.
2. Jinja injects the Stats button ONLY for admins.
3. Removes all old JS hacks.
4. Adds a tiny cookie-setter at the top of the script.
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP  = os.path.join(BASE, "app.py")
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


# ============================================================
# 1. NEW FLASK ROUTE
# ============================================================
NEW_INDEX_ROUTE = '''@app.route("/")
def index():
    # Get device ID from cookie
    device_id = request.cookies.get("voicekit_device", "")

    # Check admin status
    is_admin = device_id in ADMIN_DEVICES if ADMIN_DEVICES else False

    return render_template("index.html", is_admin=is_admin)
'''

# ============================================================
# 2. NEW HTML SNIPPETS
# ============================================================
# The Stats button, wrapped in Jinja
JINJA_STATS_BTN = '''    {% if is_admin %}
    <button class="nav-btn" data-view="stats" id="statsNavBtn">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="20" x2="12" y2="10"></line>
        <line x1="18" y1="20" x2="18" y2="4"></line>
        <line x1="6" y1="20" x2="6" y2="16"></line>
      </svg>
      Stats
    </button>
    {% endif %}'''

# The cookie setter — placed at the top of the main script
COOKIE_SETTER = '''// ============================================================
// ENSURE DEVICE COOKIE IS SET (for server-side admin check)
// ============================================================
(function ensureDeviceCookie() {
  let did = localStorage.getItem('voicekit_device_id');
  if (!did) {
    did = 'dev_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('voicekit_device_id', did);
  }
  // Set cookie with 1-year expiry
  document.cookie = "voicekit_device=" + did + "; max-age=31536000; path=/; SameSite=Lax";
})();
'''


def patch_app():
    print("\n[1/2] Patching app.py")
    if not os.path.exists(APP):
        print(f"  ERROR: {APP} not found")
        return False
    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Replace the index route
    index_pattern = re.compile(
        r'@app\.route\("/"\)\s*\ndef index\(\):.*?(?=\n@app\.route|\n# =+)',
        re.DOTALL
    )

    if index_pattern.search(src):
        src = index_pattern.sub(NEW_INDEX_ROUTE + "\n", src, count=1)
        print("  [OK] index route updated to pass is_admin")
    else:
        print("  WARN: Could not find the index route to replace.")

    # Make sure ADMIN_DEVICES is defined BEFORE the route
    if 'ADMIN_DEVICES = set(' not in src:
        anchor = "# ============================================================\n# ROUTES"
        if anchor in src:
            src = src.replace(
                anchor,
                'ADMIN_DEVICES = set(\n    d.strip() for d in os.environ.get("ADMIN_DEVICES", "").split(",") if d.strip()\n)\n\n' + anchor,
                1
            )
            print("  [OK] ADMIN_DEVICES moved above routes")
        else:
            print("  WARN: Could not place ADMIN_DEVICES before routes.")

    if src != original:
        with open(APP, "w", encoding="utf-8") as f:
            f.write(src)
    return True


def patch_html():
    print("\n[2/2] Patching templates/index.html")
    if not os.path.exists(HTML):
        print(f"  ERROR: {HTML} not found")
        return False
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # 1. Remove old Stats button (if any)
    old_btn_pattern = re.compile(
        r'<button class="nav-btn[^"]*" data-view="stats".*?</button>',
        re.DOTALL
    )
    if old_btn_pattern.search(src):
        src = old_btn_pattern.sub('', src)
        print("  [OK] Removed old Stats button")

    # 2. Insert the Jinja Stats button after the About button
    about_pattern = re.compile(
        r'(<button class="nav-btn" data-view="about">.*?</button>)',
        re.DOTALL
    )
    match = about_pattern.search(src)
    if match:
        src = src[:match.end()] + '\n' + JINJA_STATS_BTN + '\n' + src[match.end():]
        print("  [OK] Inserted Jinja-wrapped Stats button")
    else:
        print("  WARN: Could not find the About button to insert after.")

    # 3. Remove the old admin JS scripts (multiple patterns)
    patterns_to_remove = [
        r'// =+\s*\n// ADMIN MODE DETECTION \(ROBUST\).*?(?=\n// =+|\n</script>)',
        r'// =+\s*\n// FORCE ADMIN STATS BUTTON.*?(?=\n// =+|\n</script>)',
        r'// =+\s*\n// SIMPLE ADMIN UNHIDE SCRIPT.*?(?=\n// =+|\n</script>)',
        r'// -+\s*\n// Admin detection\s*\n// -+.*?(?=\n// =+|\n</script>)',
    ]
    for pat in patterns_to_remove:
        if re.search(pat, src, re.DOTALL):
            src = re.sub(pat, '', src, flags=re.DOTALL)
            print("  [OK] Removed old admin JS block")

    # 4. Insert the cookie setter at the top of the script
    # Find the first <script> tag and add the cookie setter right after it
    script_open = src.find('<script>')
    if script_open != -1 and 'ensureDeviceCookie' not in src:
        insert_at = src.find('\n', script_open) + 1
        src = src[:insert_at] + COOKIE_SETTER + '\n' + src[insert_at:]
        print("  [OK] Added cookie setter")

    # 5. Ensure loadStats is still wired up (it is from the previous patch)
    if 'statsNavBtn' in src and 'loadStats' not in src:
        print("  WARN: loadStats function may be missing.")

    if src == original:
        print("  No changes made to HTML.")
        return True

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)
    return True


if __name__ == "__main__":
    print("=" * 60)
    print(" VoiceKit — Server-Side Admin Rendering")
    print("=" * 60)

    ok1 = patch_app()
    ok2 = patch_html()

    print()
    print("=" * 60)
    print(" DONE" if (ok1 and ok2) else " DONE WITH ERRORS")
    print("=" * 60)
    print()
    print(" How it works now:")
    print("   1. Browser loads the page → sets a 'voicekit_device' cookie")
    print("   2. Flask reads the cookie → checks ADMIN_DEVICES")
    print("   3. If admin, Jinja injects the Stats button into the HTML")
    print("   4. No JS hiding/unhiding needed")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" IMPORTANT: After deploying, you must visit the site TWICE.")
    print("   1st visit: sets the cookie")
    print("   2nd visit: Flask sees the cookie → Stats button appears")
    print()
    print(" If the button doesn't appear on the 2nd visit:")
    print("   • Hard-refresh: Ctrl + Shift + R")
    print("   • Check that ADMIN_DEVICES is set in Vercel")
    print("   • Check that the env var matches your device ID exactly")
    print("=" * 60)