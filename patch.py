"""
Remember the last selected voice after page reload.
Saves to localStorage whenever the user picks a voice,
and restores it on page load.
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
    print(" VoiceKit — Remember Selected Voice")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # 1) Update the initial state to read from localStorage
    old_state = '''let selectedVoiceId = "am_adam";
let selectedVoiceName = "Adam";'''

    new_state = '''// Restore last used voice from localStorage, or default to Adam
const _savedVoiceId = localStorage.getItem('voicekit_last_voice_id');
const _savedVoiceName = localStorage.getItem('voicekit_last_voice_name');
let selectedVoiceId = _savedVoiceId || "am_adam";
let selectedVoiceName = _savedVoiceName || "Adam";'''

    if old_state in src:
        src = src.replace(old_state, new_state, 1)
        changes.append("initial state from localStorage")

    # 2) Save on selectVoice
    old_select = '''function selectVoice(id, name, chip) {
  selectedVoiceId = id;
  selectedVoiceName = name;
  selectedName.textContent = name;
  selectedId.textContent = id;

  document.querySelectorAll('.voice-chip').forEach(c => c.classList.remove('selected'));
  chip.classList.add('selected');
  updateVoiceIndicator();
}'''

    new_select = '''function selectVoice(id, name, chip) {
  selectedVoiceId = id;
  selectedVoiceName = name;
  selectedName.textContent = name;
  selectedId.textContent = id;

  // Persist so it survives reload
  localStorage.setItem('voicekit_last_voice_id', id);
  localStorage.setItem('voicekit_last_voice_name', name);

  document.querySelectorAll('.voice-chip').forEach(c => c.classList.remove('selected'));
  chip.classList.add('selected');
  updateVoiceIndicator();
}'''

    if old_select in src:
        src = src.replace(old_select, new_select, 1)
        changes.append("save on selectVoice")

    # 3) Also save if the "IN USE" chip gets selected via a different path
    #    (safety net: update on indicator sync)
    old_indicator = '''function updateVoiceIndicator() {
  const nameEl = document.getElementById('genVoiceName');
  const idEl   = document.getElementById('genVoiceId');
  if (nameEl) nameEl.textContent = selectedVoiceName;
  if (idEl)   idEl.textContent   = selectedVoiceId;
}'''

    new_indicator = '''function updateVoiceIndicator() {
  const nameEl = document.getElementById('genVoiceName');
  const idEl   = document.getElementById('genVoiceId');
  if (nameEl) nameEl.textContent = selectedVoiceName;
  if (idEl)   idEl.textContent   = selectedVoiceId;

  // Persist every time the indicator updates
  if (selectedVoiceId) {
    localStorage.setItem('voicekit_last_voice_id', selectedVoiceId);
    localStorage.setItem('voicekit_last_voice_name', selectedVoiceName);
  }
}'''

    if old_indicator in src:
        src = src.replace(old_indicator, new_indicator, 1)
        changes.append("save on indicator update")

    # 4) Mark the saved voice as selected on initial render
    old_render = "const isSelected = id === selectedVoiceId;"
    new_render = "const isSelected = id === selectedVoiceId;  // includes restored voice"
    if old_render in src:
        # Just confirm it's there — no change needed, but add a comment for clarity
        pass

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
    print(" Behavior now:")
    print("   • Pick any voice → saved to localStorage")
    print("   • Reload the page → voice is restored")
    print("   • The selected chip shows 'IN USE' immediately")
    print("   • The Generate view shows the last used voice")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()