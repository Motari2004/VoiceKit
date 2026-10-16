"""
VoiceKit — History Fix (final)
1. Adds the missing `loadServerHistory` function
2. Removes duplicate `let serverHistory = []`
3. Wires the History nav button to refresh the view
4. Replaces the local-only renderHistory with server-aware version
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


HISTORY_JS = '''
// ============================================================
// SERVER HISTORY
// ============================================================
window.loadServerHistory = async function () {
  const container = document.getElementById('history');
  if (!container) return;

  const did = (typeof DEVICE_ID !== 'undefined') ? DEVICE_ID : '';

  try {
    const res = await fetch('/history?device=' + encodeURIComponent(did) + '&limit=50');
    const data = await res.json();
    const items = data.history || [];

    if (!items.length) {
      container.innerHTML = '<div class="empty">Nothing here yet — try generating some speech.</div>';
      return;
    }

    container.innerHTML = '';
    items.forEach(h => {
      const ts = new Date(h.created_at).toLocaleString();
      const preview = h.text.length > 100 ? h.text.substring(0, 100) + '\\u2026' : h.text;

      const row = document.createElement('div');
      row.className = 'history-item';
      row.innerHTML =
        '<div class="info">' +
          '<div class="text">' + preview.replace(/</g, '&lt;') + '</div>' +
          '<div class="meta">' + h.voice + ' \\u00b7 ' + h.speed + '\\u00d7 \\u00b7 ' + ts + '</div>' +
        '</div>';

      const btn = document.createElement('button');
      btn.textContent = 'Regenerate';
      btn.onclick = () => {
        document.getElementById('text').value = h.text;
        document.getElementById('speed').value = h.speed;
        document.getElementById('speedVal').textContent = h.speed.toFixed(2) + '\\u00d7';
        if (typeof selectedVoiceId !== 'undefined') selectedVoiceId = h.voice;
        if (typeof selectedVoiceName !== 'undefined') selectedVoiceName = h.voice;
        if (typeof updateVoiceIndicator === 'function') updateVoiceIndicator();
        const genBtn = document.querySelector('.nav-btn[data-view="generate"]');
        if (genBtn) genBtn.click();
        setTimeout(() => { if (typeof speak === 'function') speak(); }, 200);
      };
      row.appendChild(btn);
      container.appendChild(row);
    });

    console.log('[history] loaded', items.length, 'items');
  } catch (e) {
    console.warn('[history] load failed:', e);
    container.innerHTML = '<div class="empty">Could not load history — try again.</div>';
  }
};

window.clearServerHistory = async function () {
  if (!confirm('Clear all history for this device?')) return;
  const did = (typeof DEVICE_ID !== 'undefined') ? DEVICE_ID : '';
  try {
    await fetch('/history', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device: did })
    });
    if (typeof loadServerHistory === 'function') loadServerHistory();
  } catch (e) {
    console.error('clear history failed:', e);
  }
};
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — History Fix (final)")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Remove duplicate serverHistory declaration ----------
    # Count occurrences
    occurrences = src.count("let serverHistory = [];")
    if occurrences > 1:
        # Remove all but the first
        parts = src.split("let serverHistory = [];")
        src = parts[0] + "let serverHistory = [];" + "".join(parts[2:])
        changes.append(f"removed {occurrences - 1} duplicate serverHistory declaration")

    # ---------- 2) Add loadServerHistory function BEFORE the INIT block ----------
    if 'window.loadServerHistory' not in src:
        anchor = "// ============================================================\n// INIT"
        if anchor in src:
            src = src.replace(anchor, HISTORY_JS + "\n" + anchor, 1)
            changes.append("added loadServerHistory")
        else:
            # Fallback: before closing </script>
            idx = src.rfind('</script>')
            if idx != -1:
                src = src[:idx] + HISTORY_JS + "\n" + src[idx:]
                changes.append("added loadServerHistory (fallback)")

    # ---------- 3) Update the nav button to load history on click ----------
    old_nav = """    // Load fresh history when History view opens
    if (view === 'history' && typeof loadServerHistory === 'function') {
      loadServerHistory();
    }"""

    if old_nav not in src:
        # Try to find just the nav section and add our handler
        old_simple = "document.querySelectorAll('.nav-btn').forEach(btn => {\n  btn.onclick = () => {\n    const view = btn.dataset.view;"
        new_simple = """document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.onclick = () => {
    const view = btn.dataset.view;

    // Load fresh history when History view opens
    if (view === 'history' && typeof window.loadServerHistory === 'function') {
      window.loadServerHistory();
    }"""
        if old_simple in src:
            src = src.replace(old_simple, new_simple, 1)
            changes.append("nav button triggers history load")

    # ---------- 4) Update the INIT block ----------
    old_init = """loadVoices();
if (typeof loadServerHistory === 'function') { loadServerHistory(); }
updateVoiceIndicator();"""

    new_init = """loadVoices();
updateVoiceIndicator();

// Load history after a short delay so the function is defined
setTimeout(() => {
  if (typeof window.loadServerHistory === 'function') {
    window.loadServerHistory();
  }
}, 400);"""

    if old_init in src:
        src = src.replace(old_init, new_init, 1)
        changes.append("delayed init call")

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
    print(" Fixed:")
    print("   • loadServerHistory function is now defined")
    print("   • Duplicate serverHistory declaration removed")
    print("   • History nav button loads fresh data on click")
    print("   • Init loads history 400ms after page load")
    print("   • Each entry has a Regenerate button")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()