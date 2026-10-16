"""
Patch templates/index.html to:
  - point at voicekit-prod.vercel.app
  - call /speak instead of the old Gradio endpoints
  - use relative URLs (same origin)
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")

# Since the API and UI share the same domain, use an empty string.
API_URL = ""


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


def patch():
    print("=" * 60)
    print(" VoiceKit index.html Patch")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    print(f"  target: {os.path.relpath(HTML, BASE)}")
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace URL constant ----------
    # Anything that was a SPACE_URL or an old Vercel URL becomes API_URL = ""
    for old in [
        'const SPACE_URL = "https://motari-txt2speech.hf.space";',
        'const API_URL = "https://voicekit-api.vercel.app";',
        'const API_URL = "https://voicekit-two.vercel.app";',
    ]:
        if old in src:
            src = src.replace(old, 'const API_URL = "";')
            changes.append("URL constant")
            break

    # If no constant matched, insert one before the first const
    if 'const API_URL' not in src and 'const SPACE_URL' not in src:
        # Try to find a good insertion point
        marker = "// ============================================================\n// ELEMENTS"
        if marker in src:
            src = src.replace(
                marker,
                '// ============================================================\n'
                '// CONFIG\n'
                '// ============================================================\n'
                'const API_URL = "";\n\n'
                + marker,
                1
            )
            changes.append("URL constant inserted")

    # ---------- 2) Replace the entire speak() function ----------
    new_speak = '''async function speak() {
  const text = textEl.value.trim();
  if (!text) {
    setStatus('Type something first.', 'err');
    return;
  }

  const voice = (typeof selectedVoiceId !== 'undefined' && selectedVoiceId)
                || voiceEl.value
                || 'am_adam';
  const speed = parseFloat(speedEl.value);

  speakBtn.disabled = true;
  speakBtn.textContent = '⏳ Generating...';
  speakBtn.classList.add('pulse');
  setStatus('Sending to VoiceKit...', 'busy');

  const t0 = performance.now();

  try {
    const res = await fetch(`${API_URL}/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice, speed })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }

    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);

    player.src = blobUrl;
    player.classList.add('show');
    await player.play().catch(() => {});

    const ms = Math.round(performance.now() - t0);
    setStatus(`✓ Ready in ${ms} ms — ${(blob.size / 1024).toFixed(1)} KB`, 'ok');

    history.unshift({ text, voice, speed, blobUrl, ts: Date.now(), ms, size: blob.size });
    if (history.length > 20) history.pop();
    renderHistory();

  } catch (e) {
    console.error(e);
    setStatus('Error: ' + e.message, 'err');
  } finally {
    speakBtn.disabled = false;
    speakBtn.textContent = '🔊 Speak';
    speakBtn.classList.remove('pulse');
  }
}
'''

    speak_pattern = re.compile(
        r'async function speak\(\)\s*\{.*?\n\}\n',
        re.DOTALL
    )
    match = speak_pattern.search(src)
    if match:
        src = src[:match.start()] + new_speak + src[match.end():]
        changes.append("speak() rewritten")

    # ---------- 3) Replace previewVoice() to use /speak ----------
    new_preview = '''async function previewVoice(voiceId, btn) {
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
'''
    preview_pattern = re.compile(
        r'async function previewVoice\(.*?\n\}\n',
        re.DOTALL
    )
    match = preview_pattern.search(src)
    if match:
        src = src[:match.start()] + new_preview + src[match.end():]
        changes.append("previewVoice() rewritten")

    # ---------- 4) Update API docs section ----------
    new_api_section = '''<div class="api-section">
  <h3>API — Use it in your app</h3>

  <div class="api-label"><strong>POST /speak</strong> — generate speech</div>
  <code>curl -X POST https://voicekit-prod.vercel.app/speak \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Listen closely. You can barely tell this is not me talking.","voice":"am_adam","speed":1.0}' \\
  -o voice.wav</code>

  <div class="api-label"><strong>Python</strong></div>
  <code>import requests

r = requests.post("https://voicekit-prod.vercel.app/speak", json={
    "text": "Listen closely. You can barely tell this is not me talking.",
    "voice": "am_adam",
    "speed": 1.0,
})
open("voice.wav", "wb").write(r.content)</code>

  <div class="api-label"><strong>JavaScript</strong></div>
  <code>const res = await fetch("https://voicekit-prod.vercel.app/speak", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: "Listen closely. You can barely tell this is not me talking.",
    voice: "am_adam",
    speed: 1.0
  })
});
const blob = await res.blob();
new Audio(URL.createObjectURL(blob)).play();</code>

  <div class="api-label"><strong>PowerShell</strong></div>
  <code>$body = @{
  text  = "Listen closely. You can barely tell this is not me talking."
  voice = "am_adam"
  speed = 1.0
} | ConvertTo-Json

Invoke-WebRequest -Method Post `
  -Uri "https://voicekit-prod.vercel.app/speak" `
  -ContentType "application/json" `
  -Body $body `
  -OutFile "voice.wav"

Start-Process "voice.wav"</code>

  <div class="api-label" style="margin-top:16px;">
    <strong>Endpoints:</strong>
    <span style="color:#22d3ee;">POST /speak</span> ·
    <span style="color:#22d3ee;">GET /voices</span> ·
    <span style="color:#22d3ee;">GET /health</span>
  </div>
</div>'''

    if '<div class="api-section">' in src:
        start = src.find('<div class="api-section">')
        depth = 0
        i = start
        end = -1
        while i < len(src):
            if src[i:i+4] == '<div':
                depth += 1
            elif src[i:i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    end = i + 6
                    break
            i += 1
        if end > start:
            src = src[:start] + new_api_section + src[end:]
            changes.append("api-section rewritten")

    # ---------- 5) Default text (if still the old one) ----------
    if 'I am the real ninja. Reggae in the valley, one drop at a time.' in src:
        src = src.replace(
            'I am the real ninja. Reggae in the valley, one drop at a time.',
            'Listen closely. You can barely tell this is not me talking.'
        )
        changes.append("default text")

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
    print(f" API_URL = \"\" (same origin — voicekit-prod.vercel.app)")
    print()
    print(" Next:")
    print("   cd C:\\Users\\PC\\Desktop\\voicekit")
    print("   vercel --prod")
    print()
    print(f" Backup saved: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()