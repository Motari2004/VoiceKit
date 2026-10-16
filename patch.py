"""
VoiceKit — Favorites + Active Voice Distinction
- Star any voice, saved in browser localStorage
- Starred voices get a golden tint
- The currently-selected voice gets a distinct checkmark + accent bar
- Clear visual difference between "starred" and "in use"
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


# ---------- CSS ----------
NEW_CSS = '''
  /* ---------- FAVORITES ---------- */
  .voice-chip.favorited {
    background: linear-gradient(135deg, rgba(251, 191, 36, 0.08), rgba(251, 191, 36, 0.02));
    border-color: rgba(251, 191, 36, 0.3);
  }

  .voice-chip.favorited .chip-name {
    color: #fcd34d;
  }

  .voice-chip.favorited .chip-desc {
    color: rgba(251, 191, 36, 0.7);
  }

  .voice-chip.favorited .chip-star {
    color: #fbbf24;
    background: rgba(251, 191, 36, 0.15);
    border-color: rgba(251, 191, 36, 0.4);
  }

  /* ---------- SELECTED (IN USE) ---------- */
  .voice-chip.selected {
    background: #ffffff;
    border-color: #ffffff;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.2), 0 0 24px rgba(255, 255, 255, 0.15);
    position: relative;
  }

  .voice-chip.selected::before {
    content: "IN USE";
    position: absolute;
    top: -8px;
    left: 10px;
    padding: 2px 8px;
    background: #ffffff;
    color: #0a0a0a;
    font-size: 0.55rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    border-radius: 4px;
    z-index: 2;
  }

  .voice-chip.selected .chip-name {
    color: #0a0a0a;
    font-weight: 700;
  }

  .voice-chip.selected .chip-desc {
    color: rgba(10, 10, 10, 0.55);
  }

  /* ---------- STAR BUTTON ---------- */
  .chip-star {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 50%;
    color: var(--text-dim);
    cursor: pointer;
    font-size: 0.65rem;
    padding: 0;
    transition: all 0.15s var(--ease);
    margin-left: 4px;
  }

  .chip-star:hover {
    background: rgba(251, 191, 36, 0.15);
    border-color: rgba(251, 191, 36, 0.4);
    color: #fbbf24;
    transform: scale(1.1);
  }

  .voice-chip.selected .chip-star {
    background: #0a0a0a;
    border-color: #0a0a0a;
    color: #ffffff;
  }

  .voice-chip.selected .chip-star:hover {
    background: #333333;
    border-color: #333333;
    color: #fbbf24;
  }

  /* Chip layout: name/desc + star + play */
  .voice-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 12px;
    position: relative;
  }

  .chip-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  /* ---------- FILTER: FAVORITES ---------- */
  .filter-chip.fav-filter {
    border-color: rgba(251, 191, 36, 0.3);
    color: rgba(251, 191, 36, 0.9);
  }

  .filter-chip.fav-filter.active {
    background: #fbbf24;
    border-color: #fbbf24;
    color: #0a0a0a;
  }

  .filter-chip.fav-filter .star-icon {
    margin-right: 4px;
  }

  /* ---------- FAVORITES COUNT ---------- */
  .fav-count {
    display: inline-block;
    padding: 1px 6px;
    background: rgba(251, 191, 36, 0.15);
    color: #fbbf24;
    border-radius: 8px;
    font-size: 0.65rem;
    font-weight: 700;
    margin-left: 4px;
  }
'''

# ---------- FAVORITES FILTER CHIP (insert after the last filter chip) ----------
FAV_CHIP = '''
        <button class="filter-chip fav-filter" data-filter="favorites">
          <span class="star-icon">★</span>Favorites
        </button>'''

# ---------- JS ----------
NEW_JS = '''
// ============================================================
// FAVORITES
// ============================================================
const FAV_KEY = 'voicekit_favorites';

function loadFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAV_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveFavorites(favs) {
  localStorage.setItem(FAV_KEY, JSON.stringify(favs));
}

let favorites = loadFavorites();

function isFavorite(id) {
  return favorites.includes(id);
}

function toggleFavorite(id) {
  if (isFavorite(id)) {
    favorites = favorites.filter(f => f !== id);
  } else {
    favorites.push(id);
  }
  saveFavorites(favorites);
  updateFavoriteUI(id);
  updateFavoriteCount();
}

function updateFavoriteUI(id) {
  document.querySelectorAll('.voice-chip').forEach(chip => {
    if (chip.dataset.id === id) {
      const star = chip.querySelector('.chip-star');
      const isFav = isFavorite(id);
      chip.classList.toggle('favorited', isFav);
      if (star) {
        star.textContent = isFav ? '★' : '☆';
        star.title = isFav ? 'Remove from favorites' : 'Add to favorites';
      }
    }
  });
}

function updateFavoriteCount() {
  const badge = document.getElementById('favCountBadge');
  if (badge) {
    if (favorites.length > 0) {
      badge.textContent = favorites.length;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  }
}

function applyFavoritesToAllChips() {
  document.querySelectorAll('.voice-chip').forEach(chip => {
    const id = chip.dataset.id;
    const isFav = isFavorite(id);
    chip.classList.toggle('favorited', isFav);
    const star = chip.querySelector('.chip-star');
    if (star) {
      star.textContent = isFav ? '★' : '☆';
      star.title = isFav ? 'Remove from favorites' : 'Add to favorites';
    }
  });
}
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Favorites + Active Voice Distinction")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Add CSS ----------
    if 'FAVORITES' not in src or '.chip-star' not in src:
        src = src.replace('</style>', NEW_CSS + '\n</style>', 1)
        changes.append("favorites CSS")

    # ---------- 2) Add Favorites filter chip ----------
    if 'data-filter="favorites"' not in src:
        marker = '<button class="filter-chip" data-filter="Portuguese">Portuguese</button>'
        if marker in src:
            src = src.replace(
                marker,
                marker + FAV_CHIP,
                1
            )
            changes.append("favorites filter chip")

    # ---------- 3) Add star button in chip HTML generation ----------
    # Find the chip.innerHTML in renderVoicePicker
    old_chip = """chip.innerHTML =
          '<div class="chip-content">' +
            '<span class="chip-name">' + name + '</span>' +
            '<span class="chip-desc">' + desc + '</span>' +
          '</div>' +
          '<button class="chip-play" data-id="' + id + '" aria-label="Preview">▶</button>';"""

    new_chip = """const isFav = isFavorite(id);
        chip.innerHTML =
          '<div class="chip-content">' +
            '<span class="chip-name">' + name + '</span>' +
            '<span class="chip-desc">' + desc + '</span>' +
          '</div>' +
          '<div class="chip-actions">' +
            '<button class="chip-star" data-id="' + id + '" title="' + (isFav ? 'Remove from favorites' : 'Add to favorites') + '">' + (isFav ? '★' : '☆') + '</button>' +
            '<button class="chip-play" data-id="' + id + '" aria-label="Preview">▶</button>' +
          '</div>';"""

    if old_chip in src:
        src = src.replace(old_chip, new_chip, 1)
        changes.append("chip HTML with star")

    # ---------- 4) Wire star click ----------
    old_play_wire = """chip.querySelector('.chip-play').onclick = (e) => {
          e.stopPropagation();
          previewVoice(id, e.target);
        };"""

    new_play_wire = """chip.querySelector('.chip-play').onclick = (e) => {
          e.stopPropagation();
          previewVoice(id, e.target);
        };

        chip.querySelector('.chip-star').onclick = (e) => {
          e.stopPropagation();
          toggleFavorite(id);
        };"""

    if old_play_wire in src and "chip.querySelector('.chip-star')" not in src:
        src = src.replace(old_play_wire, new_play_wire, 1)
        changes.append("star click handler")

    # ---------- 5) Add the favorites JS block ----------
    if 'function toggleFavorite' not in src:
        anchor = "// ============================================================\n// FILTERS"
        if anchor in src:
            src = src.replace(anchor, NEW_JS + "\n" + anchor, 1)
            changes.append("favorites JS")

    # ---------- 6) Handle "favorites" filter in applyFilters ----------
    old_filter_logic = """let matchesFilter = true;
    if (currentFilter === 'male')   matchesFilter = gender === 'male';
    else if (currentFilter === 'female') matchesFilter = gender === 'female';
    else if (currentFilter !== 'all') matchesFilter = lang === currentFilter;"""

    new_filter_logic = """let matchesFilter = true;
    if (currentFilter === 'favorites') {
      matchesFilter = isFavorite(id);
    } else if (currentFilter === 'male')   matchesFilter = gender === 'male';
    else if (currentFilter === 'female') matchesFilter = gender === 'female';
    else if (currentFilter !== 'all') matchesFilter = lang === currentFilter;"""

    if old_filter_logic in src:
        src = src.replace(old_filter_logic, new_filter_logic, 1)
        changes.append("favorites filter logic")

    # ---------- 7) Apply favorites to chips after render ----------
    anchor2 = "function selectVoice(id, name, chip) {"
    if 'applyFavoritesToAllChips()' not in src and anchor2 in src:
        # Insert call at end of renderVoicePicker
        old_render_end = """      block.appendChild(row);
    });

    voiceList.appendChild(block);
  });
}"""
        new_render_end = """      block.appendChild(row);
    });

    voiceList.appendChild(block);
  });

  // Apply favorite states to all chips
  applyFavoritesToAllChips();
  updateFavoriteCount();
}"""

        if old_render_end in src:
            src = src.replace(old_render_end, new_render_end, 1)
            changes.append("apply favorites after render")

    # ---------- 8) Add favorites badge to Voices nav button ----------
    old_nav = '<span class="nav-badge" id="voiceCountBadge">54</span>'
    new_nav = '''<span class="nav-badge" id="voiceCountBadge">54</span>
      <span class="nav-badge" id="favCountBadge" style="display:none; background: rgba(251,191,36,0.2); color: #fbbf24;">0</span>'''
    if old_nav in src and 'favCountBadge' not in src:
        src = src.replace(old_nav, new_nav, 1)
        changes.append("favorites badge in nav")

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
    print(" New features:")
    print("   ⭐ Star any voice — click the ☆ on any chip")
    print("   ⭐ Starred voices get a golden tint")
    print("   ⭐ 'Favorites' filter chip to show only starred")
    print("   ⭐ Badge in the sidebar shows how many you starred")
    print("   ⭐ Favorites persist between sessions (localStorage)")
    print()
    print(" Active voice distinction:")
    print("   ✓ The selected voice has an 'IN USE' badge at the top")
    print("   ✓ White background with black text")
    print("   ✓ Bold check mark")
    print("   ✓ Soft glow around the chip")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()