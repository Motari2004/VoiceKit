"""
Frontend Patch — Point VoiceKit at the Vercel proxy.

Replaces:
  - SPACE_URL  →  API_URL (Vercel endpoint)
  - Gradio two-step /gradio_api/call/tts  →  clean POST /speak
  - All API doc examples updated

Run from the folder containing index.html:
    python patch_frontend.py
"""

import os
import re
import shutil

# ---------- CONFIG ----------
API_URL = "https://voicekit-api.vercel.app"
HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.basename(path)}.bak")


def patch():
    print("=" * 60)
    print(" VoiceKit Frontend Patch")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace SPACE_URL constant ----------
    if 'const SPACE_URL = "https://motari-txt2speech.hf.space";' in src:
        src = src.replace(
            'const SPACE_URL = "https://motari-txt2speech.hf.space";',
            f'const API_URL = "{API_URL}";'
        )
        changes.append("SPACE_URL -> API_URL")

    # ---------- 2) Replace the entire speak() function ----------
    # Match from "async function speak() {" to the closing brace of the function
    speak_pattern = re.compile(
        r'async function speak\(\)\s*\{.*?\n\}\n',
        re.DOTALL
    )

    new_speak = '''async function speak() {
  const text = textEl.value.trim();
  if (!text) {
    setStatus('Type something first.', 'err');
    return;
  }

  const voice = voiceEl.value;
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

    match = speak_pattern.search(src)
    if match:
        src = src[:match.start()] + new_speak + src[match.end():]
        changes.append("speak() rewritten")
    else:
        print("  [WARN] could not locate speak() function")

    # ---------- 3) Update all API doc URLs ----------
    old_url = "https://motari-txt2speech.hf.space/gradio_api/call/tts"
    if old_url in src:
        src = src.replace(old_url, f"{API_URL}/speak")
        changes.append("API doc URLs")

    # ---------- 4) Replace the whole .api-section block ----------
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

    api_section_pattern = re.compile(
        r'<div class="api-section">.*?</div>\s*</div>\s*</div>',
        re.DOTALL
    )

    # Try to find and replace the api-section block
    # Note: the closing tags might vary, so we look for the marker
    if '<div class="api-section">' in src:
        start = src.find('<div class="api-section">')
        # Find the matching close by counting div opens/closes
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

    # ---------- 5) Update default textarea text ----------
    if 'I am the real ninja. Reggae in the valley, one drop at a time.' in src:
        src = src.replace(
            'I am the real ninja. Reggae in the valley, one drop at a time.',
            'Listen closely. You can barely tell this is not me talking.'
        )
        changes.append("default text")

    # ---------- 6) Update quick phrase buttons ----------
    quick_pattern = re.compile(
        r'<div class="quick-phrases">.*?</div>',
        re.DOTALL
    )

    new_quick = '''<div class="quick-phrases">
      <button data-p="Listen closely. You can barely tell this is not me talking.">Natural voice</button>
      <button data-p="Hello world, this is my voice.">Hello world</button>
      <button data-p="One two three four, hit the kick and drop the snare.">Beat drop</button>
      <button data-p="Reggae in the valley, one drop at a time.">Reggae</button>
      <button data-p="The night is young and the bass is deep.">Night vibe</button>
    </div>'''

    if quick_pattern.search(src):
        src = quick_pattern.sub(new_quick, src, count=1)
        changes.append("quick phrases")

    # ---------- Done ----------
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
    print(" What changed:")
    print(f"   • SPACE_URL  →  API_URL = {API_URL}")
    print("   • Two-step Gradio API  →  single POST /speak")
    print("   • Default text updated")
    print("   • Quick phrases updated")
    print("   • API docs rewritten")
    print()
    print(" Next:")
    print("   1. Reload the page in your browser (Ctrl+Shift+R)")
    print("   2. Try the Speak button")
    print()
    print(f" Backup saved as: {os.path.basename(HTML)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()