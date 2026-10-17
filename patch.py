"""
Update the API Reference examples to use a realistic, professional script.
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


NEW_CURL = '''<code class="api-code">curl -X POST https://voicekit-prod.vercel.app/speak \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Welcome to the show. Today we are exploring the future of AI voice synthesis.",
    "voice": "am_michael",
    "speed": 1.1
  }' \\
  -o podcast_intro.wav</code>'''

NEW_PYTHON = '''<code class="api-code">import requests

response = requests.post(
    "https://voicekit-prod.vercel.app/speak",
    json={
        "text": "Welcome to the show. Today we are exploring the future of AI voice synthesis.",
        "voice": "am_michael",
        "speed": 1.1,
    },
)

with open("podcast_intro.wav", "wb") as f:
    f.write(response.content)</code>'''

NEW_JS = '''<code class="api-code">const response = await fetch(
  "https://voicekit-prod.vercel.app/speak",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: "Welcome to the show. Today we are exploring the future of AI voice synthesis.",
      voice: "am_michael",
      speed: 1.1,
    }),
  }
);

const blob = await response.blob();
const url = URL.createObjectURL(blob);
new Audio(url).play();</code>'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Professional API Examples")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace curl ----------
    old_curl = '''<code class="api-code">curl -X POST https://voicekit-prod.vercel.app/speak \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Hello world","voice":"am_adam","speed":1.0}' \\
  -o voice.wav</code>'''
    
    if old_curl in src:
        src = src.replace(old_curl, NEW_CURL, 1)
        changes.append("curl")
    else:
        # Regex fallback
        pattern = re.compile(r'<code class="api-code">curl -X POST https://voicekit-prod\.vercel\.app/speak.*?-o voice\.wav</code>', re.DOTALL)
        if pattern.search(src):
            src = pattern.sub(NEW_CURL, src, count=1)
            changes.append("curl (regex)")
        else:
            print("  WARN: Could not find curl example")

    # ---------- 2) Replace Python ----------
    old_python = '''<code class="api-code">import requests

response = requests.post(
    "https://voicekit-prod.vercel.app/speak",
    json={
        "text": "Hello world",
        "voice": "am_adam",
        "speed": 1.0,
    },
)

with open("voice.wav", "wb") as f:
    f.write(response.content)</code>'''
    
    if old_python in src:
        src = src.replace(old_python, NEW_PYTHON, 1)
        changes.append("python")
    else:
        # Regex fallback
        pattern = re.compile(r'<code class="api-code">import requests.*?f\.write\(response\.content\)</code>', re.DOTALL)
        if pattern.search(src):
            src = pattern.sub(NEW_PYTHON, src, count=1)
            changes.append("python (regex)")
        else:
            print("  WARN: Could not find Python example")

    # ---------- 3) Replace JavaScript ----------
    old_js = '''<code class="api-code">const response = await fetch(
  "https://voicekit-prod.vercel.app/speak",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: "Hello world",
      voice: "am_adam",
      speed: 1.0,
    }),
  }
);

const blob = await response.blob();
new Audio(URL.createObjectURL(blob)).play();</code>'''
    
    if old_js in src:
        src = src.replace(old_js, NEW_JS, 1)
        changes.append("javascript")
    else:
        # Regex fallback
        pattern = re.compile(r'<code class="api-code">const response = await fetch\(.*?new Audio\(URL\.createObjectURL\(blob\)\)\.play\(\);</code>', re.DOTALL)
        if pattern.search(src):
            src = pattern.sub(NEW_JS, src, count=1)
            changes.append("javascript (regex)")
        else:
            print("  WARN: Could not find JavaScript example")

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
    print(" New examples use:")
    print('   text: "Welcome to the show. Today we are exploring the future of AI voice synthesis."')
    print("   voice: am_michael")
    print("   speed: 1.1")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()