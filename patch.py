"""
Voice Indicator Patch
- Adds a "Currently using" voice display to the Generate view
- Adds a "Change voice" button that jumps to the Voices view
- Shows a small dot + name + id inline
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
    print(" Voice Indicator Patch")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Add CSS for the voice indicator ----------
    new_css = '''
  /* ---------- VOICE INDICATOR ---------- */
  .voice-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    margin-bottom: 14px;
  }

  .voice-indicator .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-soft);
    flex-shrink: 0;
  }

  .voice-indicator .label {
    font-size: 0.68rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    flex-shrink: 0;
  }

  .voice-indicator .voice-name {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.01em;
  }

  .voice-indicator .voice-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--text-dim);
    padding: 2px 6px;
    background: var(--bg);
    border-radius: 4px;
  }

  .voice-indicator .change-btn {
    margin-left: auto;
    padding: 5px 10px;
    background: transparent;
    border: 1px solid var(--border-hi);
    border-radius: 6px;
    color: var(--text-muted);
    font-size: 0.7rem;
    font-weight: 500;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s var(--ease);
    flex-shrink: 0;
  }

  .voice-indicator .change-btn:hover {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
  }
'''

    if 'voice-indicator' not in src:
        src = src.replace('</style>', new_css + '\n</style>', 1)
        changes.append("indicator CSS")

    # ---------- 2) Insert the indicator HTML into the Generate view ----------
    # Insert after the card-header of the Text-to-speak card
    marker = '<span class="card-hint" id="charCount">0 / 800</span>\n      </div>\n      <textarea id="text"'
    replacement = '''<span class="card-hint" id="charCount">0 / 800</span>
      </div>

      <!-- Voice indicator -->
      <div class="voice-indicator">
        <span class="dot"></span>
        <span class="label">Using</span>
        <span class="voice-name" id="genVoiceName">Adam</span>
        <span class="voice-id" id="genVoiceId">am_adam</span>
        <button class="change-btn" id="changeVoiceBtn">Change →</button>
      </div>

      <textarea id="text"'''

    if 'genVoiceName' not in src and marker in src:
        src = src.replace(marker, replacement, 1)
        changes.append("indicator HTML")
    elif 'genVoiceName' in src:
        changes.append("indicator already present")

    # ---------- 3) Add JS to sync the indicator ----------
    js_addition = '''
// ============================================================
// VOICE INDICATOR SYNC
// ============================================================
function updateVoiceIndicator() {
  const nameEl = document.getElementById('genVoiceName');
  const idEl   = document.getElementById('genVoiceId');
  if (nameEl) nameEl.textContent = selectedVoiceName;
  if (idEl)   idEl.textContent   = selectedVoiceId;
}

// "Change voice" button → jump to Voices view
const changeVoiceBtn = document.getElementById('changeVoiceBtn');
if (changeVoiceBtn) {
  changeVoiceBtn.onclick = () => {
    // Simulate clicking the Voices nav button
    const voicesNavBtn = document.querySelector('.nav-btn[data-view="voices"]');
    if (voicesNavBtn) voicesNavBtn.click();
  };
}
'''

    # Insert after the existing selectVoice function
    anchor = "function selectVoice(id, name, chip) {"
    if 'updateVoiceIndicator' not in src and anchor in src:
        # Find the end of the selectVoice function
        start = src.find(anchor)
        # Find the matching closing brace
        depth = 0
        i = start
        end = -1
        while i < len(src):
            if src[i] == '{':
                depth += 1
            elif src[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
            i += 1

        if end > 0:
            # Insert after the function
            src = src[:end] + "\n" + js_addition + src[end:]
            changes.append("indicator JS")

    # ---------- 4) Call updateVoiceIndicator inside selectVoice ----------
    # Find the line inside selectVoice that ends with chip.classList.add('selected');
    old_line = "chip.classList.add('selected');\n}"
    new_line = "chip.classList.add('selected');\n  updateVoiceIndicator();\n}"

    if 'updateVoiceIndicator();' not in src.split('function selectVoice')[1][:600] if 'function selectVoice' in src else False:
        # Try to insert inside selectVoice
        if old_line in src:
            src = src.replace(old_line, new_line, 1)
            changes.append("selectVoice sync")

    # ---------- 5) Also initialize on page load ----------
    old_init = "loadVoices();\nsetStatus('Ready."
    new_init = "loadVoices();\nupdateVoiceIndicator();\nsetStatus('Ready."

    if 'updateVoiceIndicator();\nsetStatus' not in src and old_init in src:
        src = src.replace(old_init, new_init, 1)
        changes.append("init call")

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
    print(" What's new:")
    print("   • Voice indicator appears in the Generate view")
    print("   • Shows: dot + 'USING' + voice name + voice id")
    print("   • 'Change →' button jumps to the Voices view")
    print("   • Indicator updates automatically when you pick a voice")
    print()
    print(" Reload: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()