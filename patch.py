"""
Handle the mobile back button.
When the user is in a view other than Generate and presses back,
it returns to Generate instead of exiting the app.
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
// MOBILE BACK BUTTON HANDLING
// ============================================================
(function () {
  // List of views we want to allow back navigation between
  const VIEWS = ['generate', 'voices', 'history', 'api', 'about'];

  function getCurrentView() {
    const active = document.querySelector('.view.active');
    return active ? active.id.replace('view-', '') : 'generate';
  }

  function switchToView(viewName) {
    document.querySelectorAll('.nav-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.view === viewName);
    });
    document.querySelectorAll('.view').forEach(v => {
      v.classList.toggle('active', v.id === 'view-' + viewName);
    });

    // Load history when needed
    if (viewName === 'history' && typeof window.loadServerHistory === 'function') {
      window.loadServerHistory();
    }
  }

  // Push a history entry whenever the user changes views
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      if (view && view !== 'generate') {
        history.pushState({ view }, '', '#' + view);
      } else {
        // Going back to Generate — replace, don't push
        history.replaceState({ view: 'generate' }, '', '#generate');
      }
    });
  });

  // Listen for back / forward
  window.addEventListener('popstate', (e) => {
    if (e.state && e.state.view) {
      switchToView(e.state.view);
    } else {
      // Default: back to generate
      const current = getCurrentView();
      if (current !== 'generate') {
        switchToView('generate');
        // Push one more so future back presses don't exit
        history.pushState({ view: 'generate' }, '', '#generate');
      }
    }
  });

  // Set the initial history state
  history.replaceState({ view: getCurrentView() }, '', location.hash || '#generate');
})();
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Mobile Back Button")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'MOBILE BACK BUTTON HANDLING' in src:
        print("  Already applied.")
        return

    # Append the JS before the closing </script>
    idx = src.rfind('</script>')
    if idx == -1:
        print("  ERROR: no closing </script> found")
        return

    src = src[:idx] + NEW_JS + '\n' + src[idx:]

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Mobile back button handler added")
    print()
    print(" Behavior now:")
    print("   • You're in Voices, tap back → goes to Generate")
    print("   • You're in History, tap back → goes to Generate")
    print("   • You're in API, tap back → goes to Generate")
    print("   • You're in Generate, tap back → exits the site (normal)")
    print("   • Browser forward button still works")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()