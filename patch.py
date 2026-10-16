"""
Full Voice Picker Patch
Replaces the basic <select> with a professional, styled voice picker
showing all 28 voices grouped by language and gender, with preview buttons.
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")

API_URL = "https://voicekit-api.vercel.app"


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


# ============================================================
# VOICE CATALOG — all 28 voices with metadata
# ============================================================
VOICE_CATALOG = {
    "American English": {
        "Male": [
            ("am_adam", "Adam", "Deep, broadcaster"),
            ("am_michael", "Michael", "Warm, natural"),
            ("am_onyx", "Onyx", "Rich, resonant"),
            ("am_puck", "Puck", "Playful"),
            ("am_echo", "Echo", "Bright"),
            ("am_eric", "Eric", "Clear"),
            ("am_fenrir", "Fenrir", "Deep, cinematic"),
            ("am_liam", "Liam", "Warm, friendly"),
            ("am_santa", "Santa", "Gravelly, storyteller"),
        ],
        "Female": [
            ("af_heart", "Heart", "Warm, emotive"),
            ("af_bella", "Bella", "Bright, clear"),
            ("af_nicole", "Nicole", "Soft, calm"),
            ("af_sarah", "Sarah", "Clear, neutral"),
            ("af_sky", "Sky", "Youthful, light"),
            ("af_nova", "Nova", "Crisp, modern"),
            ("af_river", "River", "Calm, flowing"),
            ("af_jessica", "Jessica", "Confident, sharp"),
            ("af_kore", "Kore", "Warm, poetic"),
            ("af_aoede", "Aoede", "Melodic, lyrical"),
            ("af_alloy", "Alloy", "Bright, energetic"),
        ],
    },
    "British English": {
        "Male": [
            ("bm_george", "George", "Warm, refined"),
            ("bm_lewis", "Lewis", "Deep, authoritative"),
            ("bm_daniel", "Daniel", "Clear, articulate"),
            ("bm_fable", "Fable", "Storyteller, warm"),
        ],
        "Female": [
            ("bf_emma", "Emma", "Warm, elegant"),
            ("bf_alice", "Alice", "Clear, bright"),
            ("bf_isabella", "Isabella", "Refined, smooth"),
            ("bf_lily", "Lily", "Youthful, gentle"),
        ],
    },
}


# ============================================================
# CSS
# ============================================================
PICKER_CSS = '''
/* ============================================================
   VOICE PICKER
   ============================================================ */
.voice-picker {
  margin-top: 6px;
}

.voice-search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.voice-search {
  flex: 1;
  position: relative;
}

.voice-search input {
  width: 100%;
  padding: 10px 14px 10px 36px;
  background: rgba(0,0,0,0.4);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  color: #fff;
  font-size: 0.85rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.voice-search input:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 0 3px rgba(34,211,238,0.1);
}
.voice-search::before {
  content: "🔍";
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.8rem;
  opacity: 0.5;
  pointer-events: none;
}

.voice-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 12px;
}

.filter-chip {
  padding: 5px 12px;
  font-size: 0.72rem;
  border-radius: 12px;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border);
  color: #bbb;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
  font-weight: 500;
}
.filter-chip:hover {
  background: rgba(34,211,238,0.1);
  border-color: rgba(34,211,238,0.3);
  color: #ddd;
}
.filter-chip.active {
  background: rgba(34,211,238,0.15);
  border-color: var(--cyan);
  color: var(--cyan);
  font-weight: 600;
}

.voice-list {
  max-height: 380px;
  overflow-y: auto;
  padding-right: 4px;
  margin-bottom: 12px;
}
.voice-list::-webkit-scrollbar { width: 6px; }
.voice-list::-webkit-scrollbar-track { background: transparent; }
.voice-list::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
}
.voice-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.2);
}

.voice-lang {
  margin-bottom: 16px;
}
.voice-lang.hidden { display: none; }

.voice-lang-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--cyan);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(34,211,238,0.15);
}
.voice-lang-header::before {
  content: "";
  width: 3px;
  height: 12px;
  background: var(--cyan);
  border-radius: 2px;
}

.voice-gender-label {
  font-size: 0.62rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 10px 0 6px;
  font-weight: 600;
}

.voice-chips {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 6px;
}

.voice-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
  overflow: hidden;
}
.voice-chip.hidden { display: none; }
.voice-chip:hover {
  background: rgba(34,211,238,0.08);
  border-color: rgba(34,211,238,0.3);
  transform: translateY(-1px);
}
.voice-chip.selected {
  background: linear-gradient(135deg, rgba(34,211,238,0.15), rgba(139,92,246,0.15));
  border-color: var(--cyan);
  box-shadow: 0 0 12px rgba(34,211,238,0.15);
}
.voice-chip.selected::before {
  content: "✓";
  position: absolute;
  top: 4px;
  right: 6px;
  font-size: 0.6rem;
  color: var(--cyan);
  font-weight: 700;
}

.chip-content {
  flex: 1;
  min-width: 0;
}

.chip-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: #ddd;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.voice-chip.selected .chip-name { color: #fff; }

.chip-desc {
  font-size: 0.65rem;
  color: #777;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}

.chip-play {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(34,211,238,0.12);
  border: 1px solid rgba(34,211,238,0.2);
  color: var(--cyan);
  cursor: pointer;
  font-size: 0.55rem;
  padding: 0;
  transition: all 0.15s;
}
.chip-play:hover {
  background: rgba(34,211,238,0.3);
  transform: scale(1.1);
}
.chip-play.playing {
  background: var(--cyan);
  color: #000;
  animation: pulse-chip 1s infinite;
}
@keyframes pulse-chip {
  0%, 100% { box-shadow: 0 0 0 0 rgba(34,211,238,0.4); }
  50% { box-shadow: 0 0 0 6px rgba(34,211,238,0); }
}

.voice-selected-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(34,211,238,0.1), rgba(139,92,246,0.1));
  border: 1px solid rgba(34,211,238,0.3);
  border-radius: 10px;
  font-size: 0.82rem;
}
.voice-selected-bar .label { color: #999; font-size: 0.72rem; }
.voice-selected-bar .name { color: #fff; font-weight: 700; font-size: 0.9rem; }
.voice-selected-bar .id {
  color: var(--cyan);
  font-family: 'Consolas', monospace;
  font-size: 0.72rem;
}

.voice-count {
  font-size: 0.7rem;
  color: #666;
  text-align: right;
  margin-top: -8px;
  margin-bottom: 8px;
}
'''


# ============================================================
# HTML for the picker
# ============================================================
def build_picker_html():
    lines = []
    lines.append('<div class="voice-picker">')

    # Search + count
    lines.append('  <div class="voice-search-row">')
    lines.append('    <div class="voice-search">')
    lines.append('      <input type="text" id="voiceSearch" placeholder="Search voices by name or ID..." autocomplete="off">')
    lines.append('    </div>')
    lines.append('  </div>')

    # Filter chips
    lines.append('  <div class="voice-filter" id="voiceFilter">')
    lines.append('    <button class="filter-chip active" data-filter="all">All</button>')
    lines.append('    <button class="filter-chip" data-filter="male">Male</button>')
    lines.append('    <button class="filter-chip" data-filter="female">Female</button>')
    lines.append('    <button class="filter-chip" data-filter="American English">American</button>')
    lines.append('    <button class="filter-chip" data-filter="British English">British</button>')
    lines.append('  </div>')

    # Voice count
    lines.append('  <div class="voice-count" id="voiceCount"></div>')

    # Voice list
    lines.append('  <div class="voice-list" id="voiceList">')

    for lang, groups in VOICE_CATALOG.items():
        lines.append(f'    <div class="voice-lang" data-lang="{lang}">')
        lines.append(f'      <div class="voice-lang-header">{lang}</div>')

        for gender in ("Male", "Female"):
            voices = groups.get(gender, [])
            if not voices:
                continue
            lines.append(f'      <div class="voice-gender-label">{gender}</div>')
            lines.append('      <div class="voice-chips">')
            for vid, name, desc in voices:
                selected = " selected" if vid == "am_adam" else ""
                lines.append(
                    f'        <div class="voice-chip{selected}" '
                    f'data-id="{vid}" '
                    f'data-name="{name.lower()}" '
                    f'data-lang="{lang}" '
                    f'data-gender="{gender.lower()}" '
                    f'title="{name} — {desc}">'
                )
                lines.append('          <div class="chip-content">')
                lines.append(f'            <span class="chip-name">{name}</span>')
                lines.append(f'            <span class="chip-desc">{desc}</span>')
                lines.append('          </div>')
                lines.append(
                    f'          <button class="chip-play" data-id="{vid}" title="Preview {name}">▶</button>'
                )
                lines.append('        </div>')
            lines.append('      </div>')

        lines.append('    </div>')

    lines.append('  </div>')

    # Selected info bar
    lines.append('  <div class="voice-selected-bar" id="voiceSelectedBar">')
    lines.append('    <span class="label">Selected</span>')
    lines.append('    <span class="name" id="selectedName">Adam</span>')
    lines.append('    <span class="id" id="selectedId">am_adam</span>')
    lines.append('  </div>')

    lines.append('</div>')
    return "\n".join(lines)


# ============================================================
# JavaScript for the picker
# ============================================================
PICKER_JS = '''
// ============================================================
// VOICE PICKER
// ============================================================
let selectedVoiceId = "am_adam";
let currentFilter = "all";
let currentSearch = "";

const voiceList = document.getElementById('voiceList');
const voiceSearch = document.getElementById('voiceSearch');
const voiceFilter = document.getElementById('voiceFilter');
const voiceCount = document.getElementById('voiceCount');
const selectedNameEl = document.getElementById('selectedName');
const selectedIdEl = document.getElementById('selectedId');

function updatePickerVisibility() {
  const chips = document.querySelectorAll('.voice-chip');
  let visible = 0;

  chips.forEach(chip => {
    const id     = chip.dataset.id.toLowerCase();
    const name   = chip.dataset.name;
    const lang   = chip.dataset.lang;
    const gender = chip.dataset.gender;

    const matchesSearch = !currentSearch
      || id.includes(currentSearch)
      || name.includes(currentSearch);

    let matchesFilter = true;
    if (currentFilter === 'male')   matchesFilter = gender === 'male';
    else if (currentFilter === 'female') matchesFilter = gender === 'female';
    else if (currentFilter !== 'all') matchesFilter = lang === currentFilter;

    const show = matchesSearch && matchesFilter;
    chip.classList.toggle('hidden', !show);
    if (show) visible++;
  });

  // Hide empty language blocks
  document.querySelectorAll('.voice-lang').forEach(block => {
    const anyVisible = block.querySelectorAll('.voice-chip:not(.hidden)').length;
    block.classList.toggle('hidden', anyVisible === 0);
  });

  // Update count
  if (voiceCount) {
    voiceCount.textContent = visible + ' voice' + (visible === 1 ? '' : 's');
  }
}

// ---------- Chip click — select ----------
document.addEventListener('click', (e) => {
  const playBtn = e.target.closest('.chip-play');
  if (playBtn) {
    e.stopPropagation();
    previewVoice(playBtn.dataset.id, playBtn);
    return;
  }

  const chip = e.target.closest('.voice-chip');
  if (!chip) return;

  document.querySelectorAll('.voice-chip').forEach(c => c.classList.remove('selected'));
  chip.classList.add('selected');

  selectedVoiceId = chip.dataset.id;
  const name = chip.querySelector('.chip-name').textContent;

  // Update selected bar
  if (selectedNameEl) selectedNameEl.textContent = name;
  if (selectedIdEl)   selectedIdEl.textContent = selectedVoiceId;

  // Sync the hidden <select> so speak() works
  const hiddenSelect = document.getElementById('voice');
  if (hiddenSelect) hiddenSelect.value = selectedVoiceId;
});

// ---------- Search ----------
if (voiceSearch) {
  voiceSearch.addEventListener('input', (e) => {
    currentSearch = e.target.value.toLowerCase().trim();
    updatePickerVisibility();
  });
}

// ---------- Filter chips ----------
if (voiceFilter) {
  voiceFilter.addEventListener('click', (e) => {
    const chip = e.target.closest('.filter-chip');
    if (!chip) return;

    voiceFilter.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    currentFilter = chip.dataset.filter;
    updatePickerVisibility();
  });
}

// ---------- Preview voice ----------
async function previewVoice(voiceId, btn) {
  if (btn) {
    btn.textContent = '⏳';
    btn.classList.add('playing');
  }

  try {
    const res = await fetch(`${API_URL}/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: "Listen closely. You can barely tell this is not me talking.",
        voice: voiceId,
        speed: 1.0
      })
    });

    if (!res.ok) throw new Error('Preview failed');

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();

    if (btn) {
      btn.textContent = '■';
      audio.onended = () => {
        btn.textContent = '▶';
        btn.classList.remove('playing');
      };
    }
  } catch (err) {
    console.error(err);
    if (btn) {
      btn.textContent = '✗';
      setTimeout(() => {
        btn.textContent = '▶';
        btn.classList.remove('playing');
      }, 1500);
    }
  }
}

// ---------- Initialize ----------
updatePickerVisibility();
'''


def patch():
    print("=" * 60)
    print(" Full Voice Picker Patch")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Add CSS before </style> ----------
    if '.voice-picker {' not in src:
        src = src.replace('</style>', PICKER_CSS + '\n</style>', 1)
        changes.append("picker CSS")

    # ---------- 2) Replace the <select id="voice"> block ----------
    # Find the select block (may span multiple lines)
    select_pattern = re.compile(
        r'<select\s+id="voice"[^>]*>.*?</select>',
        re.DOTALL | re.IGNORECASE
    )

    match = select_pattern.search(src)
    if match:
        # Keep a hidden <select> so existing speak() code still works
        replacement = (
            '<div style="display:none;">'
            '<select id="voice"><option value="am_adam" selected>am_adam</option></select>'
            '</div>\n'
            + build_picker_html()
        )
        src = src[:match.start()] + replacement + src[match.end():]
        changes.append("picker HTML")
    else:
        # If no select found, insert picker before the speed row
        marker = '<label>Speed</label>'
        if marker in src:
            src = src.replace(
                marker,
                build_picker_html() + '\n' + marker,
                1
            )
            changes.append("picker inserted")

    # ---------- 3) Append picker JS before closing </script> ----------
    if 'function updatePickerVisibility' not in src:
        last_script = src.rfind('</script>')
        if last_script != -1:
            src = src[:last_script] + PICKER_JS + '\n' + src[last_script:]
            changes.append("picker JS")

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
    print(f" Voices included: {sum(len(g['Male']) + len(g['Female']) for g in VOICE_CATALOG.values())}")
    print(" Layout:")
    print("   - Search box at the top")
    print("   - Filter chips: All / Male / Female / American / British")
    print("   - Grid of 28 voices, grouped by language and gender")
    print("   - Each chip shows name + description + ▶ preview button")
    print("   - Selected voice displayed in a highlighted bar at the bottom")
    print()
    print(" Reload:  Ctrl + Shift + R")
    print(f" Backup:  {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()