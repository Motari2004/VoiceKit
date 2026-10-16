"""
VoiceKit — Replay Playing Indicator
- Replay button shows "Playing..." while audio is playing
- Only one entry plays at a time
- Reverts to "Replay" when the audio ends
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


NEW_BLOCK = (
    "      const btn = document.createElement('button');\n"
    "      btn.textContent = '\u25b6 Replay';\n"
    "      btn.dataset.playing = 'false';\n"
    "\n"
    "      btn.onclick = () => {\n"
    "        // If already playing this one, stop it\n"
    "        if (btn.dataset.playing === 'true' && btn._audio) {\n"
    "          btn._audio.pause();\n"
    "          btn._audio.currentTime = 0;\n"
    "          btn._audio = null;\n"
    "          btn.dataset.playing = 'false';\n"
    "          btn.textContent = '\u25b6 Replay';\n"
    "          btn.style.background = '';\n"
    "          btn.style.borderColor = '';\n"
    "          btn.style.color = '';\n"
    "          return;\n"
    "        }\n"
    "\n"
    "        // Stop any other playing audio first\n"
    "        document.querySelectorAll('button[data-playing=\"true\"]').forEach(other => {\n"
    "          if (other !== btn && other._audio) {\n"
    "            other._audio.pause();\n"
    "            other._audio.currentTime = 0;\n"
    "            other._audio = null;\n"
    "          }\n"
    "          other.dataset.playing = 'false';\n"
    "          other.textContent = '\u25b6 Replay';\n"
    "          other.style.background = '';\n"
    "          other.style.borderColor = '';\n"
    "          other.style.color = '';\n"
    "        });\n"
    "\n"
    "        // Mark as playing\n"
    "        btn.dataset.playing = 'true';\n"
    "        btn.textContent = '\u25b6 Playing...';\n"
    "        btn.style.background = 'rgba(255,255,255,0.12)';\n"
    "        btn.style.borderColor = 'rgba(255,255,255,0.3)';\n"
    "        btn.style.color = '#ffffff';\n"
    "\n"
    "        // If Cloudinary URL exists, play it\n"
    "        if (h.audio_url) {\n"
    "          const audio = new Audio(h.audio_url);\n"
    "          btn._audio = audio;\n"
    "          audio.onended = () => {\n"
    "            btn.dataset.playing = 'false';\n"
    "            btn.textContent = '\u25b6 Replay';\n"
    "            btn._audio = null;\n"
    "            btn.style.background = '';\n"
    "            btn.style.borderColor = '';\n"
    "            btn.style.color = '';\n"
    "          };\n"
    "          audio.play().catch(e => console.error('Playback failed:', e));\n"
    "          return;\n"
    "        }\n"
    "\n"
    "        // Fallback: regenerate\n"
    "        btn.disabled = true;\n"
    "        btn.textContent = '\u23f3 Loading...';\n"
    "        fetch('/speak', {\n"
    "          method: 'POST',\n"
    "          headers: { 'Content-Type': 'application/json' },\n"
    "          body: JSON.stringify({\n"
    "            text: h.text,\n"
    "            voice: h.voice,\n"
    "            speed: h.speed,\n"
    "            device_id: (typeof DEVICE_ID !== 'undefined') ? DEVICE_ID : ''\n"
    "          })\n"
    "        })\n"
    "        .then(r => r.ok ? r.blob() : Promise.reject(new Error('Replay failed')))\n"
    "        .then(blob => {\n"
    "          const audio = new Audio(URL.createObjectURL(blob));\n"
    "          btn._audio = audio;\n"
    "          btn.textContent = '\u25b6 Playing...';\n"
    "          audio.onended = () => {\n"
    "            btn.dataset.playing = 'false';\n"
    "            btn.textContent = '\u25b6 Replay';\n"
    "            btn._audio = null;\n"
    "            btn.style.background = '';\n"
    "            btn.style.borderColor = '';\n"
    "            btn.style.color = '';\n"
    "          };\n"
    "          audio.play();\n"
    "        })\n"
    "        .catch(e => {\n"
    "          console.error('Replay error:', e);\n"
    "          btn.dataset.playing = 'false';\n"
    "          btn.textContent = '\u25b6 Replay';\n"
    "          btn.style.background = '';\n"
    "          btn.style.borderColor = '';\n"
    "          btn.style.color = '';\n"
    "        })\n"
    "        .finally(() => {\n"
    "          btn.disabled = false;\n"
    "        });\n"
    "      };\n"
    "      row.appendChild(btn);"
)


def patch():
    print("=" * 60)
    print(" VoiceKit — Replay Indicator")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Find the button block inside loadServerHistory
    pattern = re.compile(
        r"const btn = document\.createElement\('button'\);.*?row\.appendChild\(btn\);",
        re.DOTALL
    )

    if not pattern.search(src):
        print("  ERROR: could not find replay button block")
        return

    src = pattern.sub(lambda m: NEW_BLOCK, src, count=1)

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Replay handler rewritten with playing indicator")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Behavior now:")
    print("   ▶ Replay         — idle, ready to play")
    print("   ▶ Playing...     — audio is playing (button highlights)")
    print("   Click again      — stops playback")
    print("   Auto-stops       — reverts when audio ends")
    print("   Only one plays   — starting a new one stops the old one")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()