"""
Force the Stats button to appear for admin devices.
Removes the 'admin-only' class entirely and injects the button
into the DOM if it's missing.
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


NEW_JS = '''
// ============================================================
// FORCE ADMIN STATS BUTTON
// ============================================================
(async function forceAdminButton() {
  try {
    // 1. Get device ID
    const did = localStorage.getItem('voicekit_device_id') || '';
    if (!did) return;

    // 2. Check with the server
    const res = await fetch('/is-admin?device=' + encodeURIComponent(did));
    const data = await res.json();

    if (!data.admin) return;  // Not an admin, do nothing

    console.log('[admin] confirmed — revealing Stats button');

    // 3. Find the button in the DOM
    let statsBtn = document.querySelector('.nav-btn[data-view="stats"]');

    // 4. If the button doesn't exist at all, create and insert it
    if (!statsBtn) {
      console.log('[admin] creating Stats button from scratch');

      const navSections = document.querySelectorAll('.nav-section');
      const devSection = navSections[navSections.length - 1]; // Developers section

      if (devSection) {
        statsBtn = document.createElement('button');
        statsBtn.className = 'nav-btn';
        statsBtn.dataset.view = 'stats';
        statsBtn.innerHTML = `
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="20" x2="12" y2="10"></line>
            <line x1="18" y1="20" x2="18" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="16"></line>
          </svg>
          Stats
        `;
        devSection.appendChild(statsBtn);

        // Wire up the click event to show the stats view
        statsBtn.addEventListener('click', () => {
          document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
          statsBtn.classList.add('active');
          document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
          const target = document.getElementById('view-stats');
          if (target) target.classList.add('active');
          
          // Trigger stats load if the function exists
          if (typeof loadStats === 'function') loadStats();
          
          // Close mobile sidebar
          const sidebar = document.getElementById('sidebar');
          const overlay = document.getElementById('overlay');
          if (sidebar) sidebar.classList.remove('open');
          if (overlay) overlay.classList.remove('show');
        });
      }
    }

    // 5. Force it to be visible regardless of CSS
    if (statsBtn) {
      statsBtn.style.display = 'flex';
      statsBtn.style.visibility = 'visible';
      statsBtn.classList.remove('admin-only');
      statsBtn.classList.add('admin-visible');
    }

  } catch (e) {
    console.warn('[admin] force reveal failed:', e);
  }
})();
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Force Admin Stats Button")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # Remove any previous admin check scripts to avoid conflicts
    src = re.sub(
        r'// =+\s*\n// ADMIN MODE DETECTION.*?(?=\n// =+|\n</script>)',
        '',
        src,
        flags=re.DOTALL
    )
    src = re.sub(
        r'// =+\s*\n// FORCE ADMIN STATS BUTTON.*?(?=\n// =+|\n</script>)',
        '',
        src,
        flags=re.DOTALL
    )

    # Append the new script
    idx = src.rfind('</script>')
    if idx == -1:
        print("  ERROR: no closing </script> found")
        return

    src = src[:idx] + NEW_JS + '\n' + src[idx:]

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Force-reveal script added")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()