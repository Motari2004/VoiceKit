"""
Frontend retry patch.
When /speak fails with 504, wait 2 seconds and retry once.
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
      body: JSON.stringify({ text, voice: selectedVoiceId, speed })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));

      // Retry on 504 (timeout) — the Space is warming up
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
    print(" VoiceKit — Frontend Retry")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    pattern = re.compile(
        r'async function speak\(\)\s*\{.*?\n\}\n',
        re.DOTALL
    )

    match = pattern.search(src)
    if not match:
        print("  ERROR: could not find speak() function")
        return

    src = src[:match.start()] + NEW_SPEAK + '\n' + src[match.end():]

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] speak() rewritten with retry")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("=" * 60)


if __name__ == "__main__":
    patch()