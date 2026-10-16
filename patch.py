"""
Fix: favorites aren't being applied to rendered chips.
Forces applyFavoritesToAllChips() to run after render, with retry.
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


# ---------- NEW applyFavoritesToAllChips: more robust ----------
NEW_APPLY = '''function applyFavoritesToAllChips() {
  console.log('[fav] applying favorites:', favorites);

  document.querySelectorAll('.voice-chip').forEach(chip => {
    const id = chip.dataset.id;
    const isFav = favorites.includes(id);

    chip.classList.toggle('favorited', isFav);

    const star = chip.querySelector('.chip-star');
    if (star) {
      star.textContent = isFav ? '★' : '☆';
      star.title = isFav ? 'Remove from favorites' : 'Add to favorites';
    }
  });

  const count = document.querySelectorAll('.voice-chip.favorited').length;
  console.log('[fav] chips marked favorited:', count);
}
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Favorites Render Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace applyFavoritesToAllChips with the robust version ----------
    pattern = re.compile(
        r'function applyFavoritesToAllChips\(\)\s*\{.*?\n\}\n',
        re.DOTALL
    )

    if pattern.search(src):
        src = pattern.sub(NEW_APPLY + '\n', src, count=1)
        changes.append("applyFavoritesToAllChips")

    # ---------- 2) Also apply inside renderVoicePicker ----------
    # Make sure it's called right after the voice list is populated
    if 'applyFavoritesToAllChips();' not in src.split('function renderVoicePicker')[1][:3000] if 'function renderVoicePicker' in src else False:
        old = "voiceList.appendChild(block);\n  });\n}"
        new = """voiceList.appendChild(block);
  });

  // Apply favorites immediately after render
  if (typeof applyFavoritesToAllChips === 'function') {
    applyFavoritesToAllChips();
  }
}"""
        if old in src:
            src = src.replace(old, new, 1)
            changes.append("renderVoicePicker call")

    # ---------- 3) Add a global retry at page load ----------
    # After loadVoices() runs, retry applying favorites a few times
    # (the catalog fetch is async, chips appear later)
    retry_js = '''
// Retry applying favorites after the chips render (catalog fetch is async)
let _favRetries = 0;
function retryFavorites() {
  _favRetries++;
  applyFavoritesToAllChips();
  updateFavoriteCount();
  if (_favRetries < 10) {
    setTimeout(retryFavorites, 300);
  }
}
setTimeout(retryFavorites, 400);
'''

    if 'retryFavorites' not in src:
        # Insert just before the closing </script>
        idx = src.rfind('</script>')
        if idx != -1:
            src = src[:idx] + retry_js + '\n' + src[idx:]
            changes.append("retry loop")

    # ---------- 4) Also apply on sync from server ----------
    old_sync = """if (Array.isArray(data.favorites)) {
      // Merge server favorites with local
      const merged = Array.from(new Set([...favorites, ...data.favorites]));
      if (merged.length !== favorites.length) {
        favorites = merged;
        saveFavorites(favorites);
        applyFavoritesToAllChips();
        updateFavoriteCount();
      }
    }"""

    new_sync = """if (Array.isArray(data.favorites)) {
      const merged = Array.from(new Set([...favorites, ...data.favorites]));
      favorites = merged;
      saveFavorites(favorites);
      applyFavoritesToAllChips();
      updateFavoriteCount();
    }"""

    if old_sync in src:
        src = src.replace(old_sync, new_sync, 1)
        changes.append("sync always applies")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" What was wrong:")
    print("   applyFavoritesToAllChips() was defined but never called")
    print("   after the async catalog fetch finished rendering chips.")
    print()
    print(" The fix:")
    print("   • applyFavoritesToAllChips is called inside renderVoicePicker")
    print("   • A retry loop runs 10 times every 300ms after page load")
    print("   • Console logs show how many chips got starred")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()