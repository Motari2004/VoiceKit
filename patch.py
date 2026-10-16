"""
Frontend Patch — Point VoiceKit at the Vercel API.
Rewrites index.html to call voicekit-api.vercel.app/speak instead of
going straight to Hugging Face.
"""

import os
import re
import shutil

# ---------- CONFIG ----------
API_URL = "https://voicekit-api.vercel.app"

BASE = os.path.dirname(os.path.abspath(__file__))

# Try both possible locations
HTML_CANDIDATES = [
    os.path.join(BASE, "templates", "index.html"),
    os.path.join(BASE, "index.html"),
]

HTML = None
for path in HTML_CANDIDATES:
    if os.path.exists(path):
        HTML = path
        break


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


def patch():
    print("=" * 60)
    print(" VoiceKit Frontend Patch")
    print("=" * 60)

    if not HTML:
        print("ERROR: index.html not found.")
        print("Looked in:")
        for p in HTML_CANDIDATES:
            print(f"  - {p}")
        return

    print(f"  target: {os.path.relpath(HTML, BASE)}")
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace URL constants ----------
    # Old Space URL used directly
    if "https://motari-txt2speech.hf.space" in src:
        src = src.replace(
            "https://motari-txt2speech.hf.space",
            API_URL
        )
        changes.append("SPACE URL -> API URL")

    if 'const SPACE_URL =' in src:
        src = src.replace(
            'const SPACE_URL = "' + API_URL + '"',
            'const API_URL = "' + API_URL + '"'
        )
        changes.append("SPACE_URL -> API_URL")

    # ---------- 2) Replace speak() with clean single-POST version ----------
    new_speak = '''async function speak() {
  const text = textEl.value.trim();
  if (!text) {
    setStatus('Type something first.', 'err');
    return;
  }

  const voice = selectedVoiceId || voiceEl.value || 'am_adam';
  const speed = parseFloat(speedEl.value);

  speakBtn.disabled = true;
  speakBtn.textContent = 'Generating...';
  speakBtn.classList.add('pulse');
  setStatus('Sending to VoiceKit API...', 'busy');

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
    setStatus(`Ready in ${ms} ms — ${(blob.size / 1024).toFixed(1)} KB`, 'ok');

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

    # ---------- 3) Replace the whole .api-section ----------
    new_api_section = f'''<div class="api-section">
  <h3>API — Use it in your app</h3>

  <div class="api-label"><strong>POST /speak</strong> — generate speech</div>
  <code>curl -X POST {API_URL}/speak \\
  -H "Content-Type: application/json" \\
  -d '{{"text":"Listen closely. You can barely tell this is not me talking.","voice":"am_adam","speed":1.0}}' \\
  -o voice.wav</code>

  <div class="api-label"><strong>Python</strong></div>
  <code>import requests

r = requests.post("{API_URL}/speak", json={{
    "text": "Listen closely. You can barely tell this is not me talking.",
    "voice": "am_adam",
    "speed": 1.0,
}})
open("voice.wav", "wb").write(r.content)</code>

  <div class="api-label"><strong>JavaScript</strong></div>
  <code>const res = await fetch("{API_URL}/speak", {{
  method: "POST",
  headers: {{ "Content-Type": "application/json" }},
  body: JSON.stringify({{
    text: "Listen closely. You can barely tell this is not me talking.",
    voice: "am_adam",
    speed: 1.0
  }})
}});
const blob = await res.blob();
new Audio(URL.createObjectURL(blob)).play();</code>

  <div class="api-label"><strong>PowerShell</strong></div>
  <code>$body = @{{
  text  = "Listen closely. You can barely tell this is not me talking."
  voice = "am_adam"
  speed = 1.0
}} | ConvertTo-Json

Invoke-WebRequest -Method Post `
  -Uri "{API_URL}/speak" `
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

    # ---------- 4) Update previewVoice() to use API ----------
    old_preview = re.search(
        r'async function previewVoice\(.*?\n\}\n',
        src,
        re.DOTALL
    )
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
    if old_preview:
        src = src[:old_preview.start()] + new_preview + src[old_preview.end():]
        changes.append("previewVoice() rewritten")

    if src == original:
        print("  No changes made — file may already be patched.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(f" API_URL is now: {API_URL}")
    print()
    print(" Reload the browser: Ctrl + Shift + R")
    print(f" Backup saved: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()