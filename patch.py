"""
Bypass fix: add the Stats button with an ID and unhide it via a separate script.
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
    print(" VoiceKit — Admin Button ID Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # 1. Ensure the Stats button exists in the HTML and has an ID
    if 'id="statsNavBtn"' not in src:
        # Look for the About button to insert after
        about_btn_pattern = r'(<button class="nav-btn" data-view="about">.*?</button>)'
        match = re.search(about_btn_pattern, src, re.DOTALL)
        
        if match:
            # Insert the Stats button right after About
            stats_btn = '''
    <button class="nav-btn" data-view="stats" id="statsNavBtn" style="display: none;">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="20" x2="12" y2="10"></line>
        <line x1="18" y1="20" x2="18" y2="4"></line>
        <line x1="6" y1="20" x2="6" y2="16"></line>
      </svg>
      Stats
    </button>'''
            src = src[:match.end()] + stats_btn + src[match.end():]
            print("  [OK] Injected Stats button with ID")
        else:
            print("  WARN: Could not find the About button to insert after.")

    # 2. Remove any old admin scripts to prevent conflicts
    src = re.sub(
        r'// =+\s*\n// (ADMIN MODE DETECTION|FORCE ADMIN STATS BUTTON).*?(?=\n// =+|\n</script>)',
        '',
        src,
        flags=re.DOTALL
    )

    # 3. Add a clean, isolated script at the very end
    clean_script = '''
// ============================================================
// SIMPLE ADMIN UNHIDE SCRIPT
// ============================================================
setTimeout(async () => {
  try {
    const did = localStorage.getItem('voicekit_device_id');
    if (!did) return;

    const res = await fetch('/is-admin?device=' + encodeURIComponent(did));
    const data = await res.json();

    console.log('[admin-check] status:', data);

    if (data.admin) {
      const btn = document.getElementById('statsNavBtn');
      if (btn) {
        btn.style.display = 'flex';
        console.log('[admin-check] Stats button revealed');
      } else {
        console.error('[admin-check] Stats button NOT FOUND in DOM');
      }
    }
  } catch (e) {
    console.error('[admin-check] error:', e);
  }
}, 1000); // Wait 1 second to ensure everything is loaded
'''

    idx = src.rfind('</script>')
    if idx != -1:
        src = src[:idx] + clean_script + '\n' + src[idx:]
        print("  [OK] Added clean admin unhide script")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print()
    print(" Then check the browser console for '[admin-check] status:'")
    print("=" * 60)


if __name__ == "__main__":
    patch()