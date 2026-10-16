"""
Rename 'Regenerate' to 'Replay' and use the Cloudinary URL when present.
Fixed: use lambda replacement to avoid backslash escaping in re.sub.
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


# Use a plain Python string for the handler (no regex escape issues)
NEW_HANDLER = (
    "      const btn = document.createElement('button');\n"
    "      btn.textContent = '\u25b6 Replay';\n"
    "\n"
    "      btn.onclick = () => {\n"
    "        // If Cloudinary URL exists, play it instantly\n"
    "        if (h.audio_url) {\n"
    "          const audio = new Audio(h.audio_url);\n"
    "          audio.play().catch(e => console.error('Playback failed:', e));\n"
    "          return;\n"
    "        }\n"
    "\n"
    "        // Fallback: regenerate on the server\n"
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
    "        .then(blob => { new Audio(URL.createObjectURL(blob)).play(); })\n"
    "        .catch(e => { console.error('Replay error:', e); })\n"
    "        .finally(() => {\n"
    "          btn.disabled = false;\n"
    "          btn.textContent = '\u25b6 Replay';\n"
    "        });\n"
    "      };\n"
    "      row.appendChild(btn);"
)


def patch():
    print("=" * 60)
    print(" VoiceKit — Replay Button")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # Match the button block inside loadServerHistory
    pattern = re.compile(
        r"const btn = document\.createElement\('button'\);.*?row\.appendChild\(btn\);",
        re.DOTALL
    )

    if pattern.search(src):
        # Use a lambda so Python doesn't interpret backslash escapes in the replacement
        src = pattern.sub(lambda m: NEW_HANDLER, src, count=1)
        changes.append("button + handler")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()