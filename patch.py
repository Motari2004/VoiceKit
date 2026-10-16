"""
Fix: the sidebar toggle JS never adds the 'hidden' class to the hamburger.
Replace it with code that does.
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


NEW_JS = '''// Mobile sidebar toggle
function openSidebarMobile() {
  sidebar.classList.add('open');
  overlay.classList.add('show');
  menuToggle.classList.add('hidden');
}

function closeSidebarMobile() {
  sidebar.classList.remove('open');
  overlay.classList.remove('show');
  menuToggle.classList.remove('hidden');
}

menuToggle.onclick = (e) => {
  e.preventDefault();
  if (sidebar.classList.contains('open')) {
    closeSidebarMobile();
  } else {
    openSidebarMobile();
  }
};

overlay.onclick = closeSidebarMobile;

// Close when a nav button is tapped
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (window.innerWidth <= 900) closeSidebarMobile();
  });
});

// Escape key closes the sidebar
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && sidebar.classList.contains('open')) {
    closeSidebarMobile();
  }
});'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Hamburger JS Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Match the entire old toggle block
    pattern = re.compile(
        r'// Mobile sidebar toggle\s*\n'
        r'menuToggle\.onclick = \(\) => \{.*?\n'
        r'\};\s*\n'
        r'\s*\n'
        r'overlay\.onclick = \(\) => \{.*?\n'
        r'\};',
        re.DOTALL
    )

    if not pattern.search(src):
        print("  ERROR: could not find the toggle block.")
        print("  Look for '// Mobile sidebar toggle' in the HTML and share it.")
        return

    src = pattern.sub(lambda m: NEW_JS, src, count=1)

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Toggle JS replaced")
    print()
    print(" What it does now:")
    print("   • Tapping ☰      → sidebar opens + 'hidden' added to hamburger")
    print("   • Tapping ×      → sidebar closes + 'hidden' removed")
    print("   • Tapping overlay→ same")
    print("   • Tapping a nav  → same (on mobile)")
    print("   • Pressing Esc   → same")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()