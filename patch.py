"""
Fix: History view stays empty because the frontend never sends
device_id to /speak, so the server has nothing to record.

This patch:
  - Sends device_id with every /speak request
  - POSTs to /history after every successful generation
  - Loads history from /history when the History view opens
  - Renders server history in the History view
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


NEW_SPEAK = '''async function speak(retryCount = 0) {
  const text = textEl.value.trim();
  if (!text) { setStatus('Type something first.', 'err'); return; }

  const speed = parseFloat(speedEl.value);
  const isRetry = retryCount > 0;

  speakBtn.disabled = true;
  const btnContent = document.getElementById('speakBtnContent');
  const btnIcon    = document.getElementById('speakIcon');
  if (btnContent) btnContent.textContent = isRetry ? 'Warming up...' : 'Generating...';
  if (btnIcon)    btnIcon.innerHTML = '<div class="spinner"></div>';
  setStatus(isRetry ? 'Voice service warming up, retrying...' : 'Generating audio...', 'busy');

  const t0 = performance.now();

  try {
    const res = await fetch(`${API_URL}/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        voice: selectedVoiceId,
        speed,
        device_id: DEVICE_ID,
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));

      if (res.status === 504 && retryCount < 2) {
        await new Promise(r => setTimeout(r, 2500));
        return speak(retryCount + 1);
      }

      throw new Error(err.error || `Server error ${res.status}`);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    player.src = url;
    player.classList.add('show');
    await player.play().catch(() => {});

    const ms = Math.round(performance.now() - t0);
    setStatus(`✓ Ready in ${ms} ms — ${(blob.size / 1024).toFixed(1)} KB`, 'ok');

    // Enable download
    const dlBtn = document.getElementById('downloadBtn');
    if (dlBtn) {
      dlBtn.disabled = false;
      dlBtn.onclick = () => {
        const a = document.createElement('a');
        a.href = url;
        a.download = `voicekit_${Date.now()}.wav`;
        a.click();
      };
    }

    // Push to local history
    history.unshift({
      text,
      voice: selectedVoiceName,
      voiceId: selectedVoiceId,
      speed,
      url,
      ts: Date.now(),
      ms
    });
    if (history.length > 20) history.pop();
    renderHistory();

    // Refresh server history list (fire and forget)
    loadServerHistory();
  } catch (e) {
    console.error(e);
    setStatus('Error: ' + e.message, 'err');
  } finally {
    speakBtn.disabled = false;
    if (btnContent) btnContent.textContent = 'Generate';
    if (btnIcon)    btnIcon.innerHTML = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
  }
}
'''


NEW_HISTORY_JS = '''
// ============================================================
// SERVER HISTORY
// ============================================================
let serverHistory = [];

async function loadServerHistory() {
  const container = document.getElementById('history');
  if (!container) return;

  try {
    const res = await fetch(`/history?device=${encodeURIComponent(DEVICE_ID)}&limit=50`);
    const data = await res.json();
    serverHistory = data.history || [];
    renderServerHistory();
  } catch (e) {
    console.warn('[history] load failed:', e);
  }
}

function renderServerHistory() {
  const container = document.getElementById('history');
  if (!container) return;

  if (!serverHistory.length) {
    container.innerHTML = '<div class="empty">Nothing here yet — try generating some speech.</div>';
    return;
  }

  container.innerHTML = '';
  serverHistory.forEach(h => {
    const ts = new Date(h.created_at).toLocaleString();
    const preview = h.text.length > 100 ? h.text.substring(0, 100) + '…' : h.text;

    const row = document.createElement('div');
    row.className = 'history-item';
    row.innerHTML =
      '<div class="info">' +
        '<div class="text">' + preview.replace(/</g, '&lt;') + '</div>' +
        '<div class="meta">' + h.voice + ' · ' + h.speed + '× · ' + ts + '</div>' +
      '</div>';

    const replayBtn = document.createElement('button');
    replayBtn.textContent = 'Regenerate';
    replayBtn.onclick = async () => {
      selectedVoiceId = h.voice;
      selectedVoiceName = h.voice;
      document.getElementById('text').value = h.text;
      document.getElementById('speed').value = h.speed;
      document.getElementById('speedVal').textContent = h.speed.toFixed(2) + '×';

      // Update selected voice display
      if (typeof updateVoiceIndicator === 'function') updateVoiceIndicator();

      // Switch to Generate view
      const genBtn = document.querySelector('.nav-btn[data-view="generate"]');
      if (genBtn) genBtn.click();

      // Trigger speak
      setTimeout(() => speak(), 200);
    };
    row.appendChild(replayBtn);

    container.appendChild(row);
  });
}

async function clearServerHistory() {
  if (!confirm('Clear all history for this device?')) return;
  try {
    await fetch('/history', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device: DEVICE_ID })
    });
    serverHistory = [];
    renderServerHistory();
  } catch (e) {
    console.error('clear history failed:', e);
  }
}
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — History Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace speak() ----------
    speak_pattern = re.compile(
        r'async function speak\([^)]*\)\s*\{.*?\n\}\n',
        re.DOTALL
    )
    if speak_pattern.search(src):
        src = speak_pattern.sub(NEW_SPEAK + '\n', src, count=1)
        changes.append("speak() with device_id + history")
    else:
        print("  WARN: speak() not found")

    # ---------- 2) Add server history JS ----------
    if 'loadServerHistory' not in src:
        anchor = "// ============================================================\n// KEYBOARD"
        if anchor in src:
            src = src.replace(anchor, NEW_HISTORY_JS + '\n' + anchor, 1)
            changes.append("server history JS")

    # ---------- 3) Load history when nav is opened ----------
    old_nav = """document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.onclick = () => {
    const view = btn.dataset.view;"""
    new_nav = """document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.onclick = () => {
    const view = btn.dataset.view;

    // Load fresh history when History view opens
    if (view === 'history' && typeof loadServerHistory === 'function') {
      loadServerHistory();
    }"""
    if old_nav in src:
        src = src.replace(old_nav, new_nav, 1)
        changes.append("history on nav")

    # ---------- 4) Init call ----------
    if 'loadServerHistory();' not in src.split('// INIT')[1][:500] if '// INIT' in src else False:
        old_init = "loadVoices();"
        new_init = """loadVoices();
loadServerHistory();"""
        if old_init in src:
            src = src.replace(old_init, new_init, 1)
            changes.append("init history load")

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
    print(" What changed:")
    print("   • speak() now sends device_id to the server")
    print("   • Server records every generation in the history table")
    print("   • History view loads from /history on open")
    print("   • Each entry has a 'Regenerate' button")
    print("   • Clicking regenerate re-runs the same text + voice")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()