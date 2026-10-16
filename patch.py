"""
Repair the Speak button and JS wiring.
Fixes:
  - Ensures the Speak button has a child #speakIcon
  - Ensures there is a #downloadBtn
  - Rewrites the JS speak() to be defensive: uses whatever exists
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


NEW_ACTION_ROW = '''<div class="action-row">
        <button class="speak-btn primary" id="speakBtn">
          <span class="play-icon" id="speakIcon">
            <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          </span>
          <span id="speakBtnContent">Generate</span>
        </button>
        <button class="download-btn" id="downloadBtn" title="Download WAV" disabled>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </button>
      </div>'''


NEW_SPEAK_JS = '''async function speak() {
  const text = textEl.value.trim();
  if (!text) { setStatus('Type something first.', 'err'); return; }

  const speed = parseFloat(speedEl.value);

  // Set loading state (defensively)
  speakBtn.disabled = true;
  const btnContent = document.getElementById('speakBtnContent');
  const btnIcon    = document.getElementById('speakIcon');
  if (btnContent) btnContent.textContent = 'Generating...';
  if (btnIcon)    btnIcon.innerHTML = '<div class="spinner"></div>';
  setStatus('Generating audio...', 'busy');

  const t0 = performance.now();

  try {
    const res = await fetch(`${API_URL}/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice: selectedVoiceId, speed })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    player.src = url;
    player.classList.add('show');
    await player.play().catch(() => {});

    const ms = Math.round(performance.now() - t0);
    setStatus(`✓ Ready in ${ms} ms — ${(blob.size / 1024).toFixed(1)} KB`, 'ok');

    // Enable download button
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

    history.unshift({ text, voice: selectedVoiceName, speed, url, ts: Date.now(), ms });
    if (history.length > 20) history.pop();
    renderHistory();
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


def patch():
    print("=" * 60)
    print(" VoiceKit — Repair Speak Button")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace the action-row / speak button block ----------
    # Find the button block by its id="speakBtn"
    btn_pattern = re.compile(
        r'<button[^>]*id="speakBtn"[^>]*>.*?</button>',
        re.DOTALL
    )

    match = btn_pattern.search(src)
    if match:
        # Check if it already has a proper inner structure
        block = match.group(0)
        if 'id="speakIcon"' in block and 'id="speakBtnContent"' in block:
            print("  [SKIP] Speak button already has icon + content spans")
        else:
            # Replace the entire action-row (or the button block) with the new one
            action_pattern = re.compile(
                r'<div class="action-row">.*?</div>\s*</div>',
                re.DOTALL
            )
            action_match = action_pattern.search(src)
            if action_match:
                src = src[:action_match.start()] + NEW_ACTION_ROW + src[action_match.end():]
                changes.append("replaced action-row")
            else:
                src = src[:match.start()] + NEW_ACTION_ROW + src[match.end():]
                changes.append("replaced speak button block")

    # ---------- 2) If downloadBtn is completely missing, add it ----------
    if 'id="downloadBtn"' not in src:
        # Insert after </button> of speakBtn
        marker = '</button>'
        idx = src.find('id="speakBtn"')
        if idx != -1:
            end = src.find(marker, idx)
            if end != -1:
                end += len(marker)
                dl_html = '''
        <button class="download-btn" id="downloadBtn" title="Download WAV" disabled>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </button>'''
                src = src[:end] + dl_html + src[end:]
                changes.append("added download button")

    # ---------- 3) Replace the speak() function ----------
    speak_pattern = re.compile(
        r'async function speak\(\)\s*\{.*?\n\}\n',
        re.DOTALL
    )
    match = speak_pattern.search(src)
    if match:
        src = src[:match.start()] + NEW_SPEAK_JS + '\n' + src[match.end():]
        changes.append("rewrote speak()")

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
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" Or hard-refresh: Ctrl + Shift + R")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()