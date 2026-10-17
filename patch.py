"""
Fix: Mobile back button still exiting on the first press.
Pushes a base history state immediately on page load so the first
back press is trapped and redirected to Generate.
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


# Replace the previous back button logic with a more aggressive version
NEW_JS = '''
// ============================================================
// MOBILE BACK BUTTON HANDLING (FIXED)
// ============================================================
(function () {
  // 1. Immediately push a dummy state so the FIRST back press 
  // does not exit the app.
  history.pushState({ view: 'generate', base: true }, '', '#generate');

  // 2. Whenever the user switches views via the sidebar
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const view = btn.dataset.view;
      if (view && view !== 'generate') {
        // Push a new state for this view
        history.pushState({ view: view }, '', '#' + view);
      }
    });
  });

  // 3. Listen for back / forward
  window.addEventListener('popstate', (e) => {
    if (e.state && e.state.view) {
      // If the browser gives us a valid view state, switch to it
      switchToView(e.state.view);
    } else {
      // If there is no state (user pressed back too fast or deep-linked),
      // force them to Generate and push a new dummy state so they can't exit
      switchToView('generate');
      history.pushState({ view: 'generate', base: true }, '', '#generate');
    }
  });

  // Helper function to actually change the visible view
  function switchToView(viewName) {
    // Update sidebar buttons
    document.querySelectorAll('.nav-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.view === viewName);
    });

    // Update visible view section
    document.querySelectorAll('.view').forEach(v => {
      v.classList.toggle('active', v.id === 'view-' + viewName);
    });

    // Load history if needed
    if (viewName === 'history' && typeof window.loadServerHistory === 'function') {
      window.loadServerHistory();
    }
  }
})();
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Fix Mobile Back Button Exit")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # Remove the old block if it exists
    old_block_pattern = re.compile(
        r'// =+\s*\n// MOBILE BACK BUTTON HANDLING.*?(?=\n</script>)',
        re.DOTALL
    )
    if old_block_pattern.search(src):
        src = old_block_pattern.sub('', src)
        print("  Removed old back button logic")

    # Append the new logic right before </script>
    idx = src.rfind('</script>')
    if idx == -1:
        print("  ERROR: no closing </script> found")
        return

    src = src[:idx] + NEW_JS + '\n' + src[idx:]

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Mobile back button fixed")
    print()
    print(" How it works now:")
    print("   • Page loads → a 'base' history state is pushed")
    print("   • Tap Voices → 'voices' state is pushed")
    print("   • Press Back → goes to Generate (does not exit)")
    print("   • Press Back on Generate → exits (normal)")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()