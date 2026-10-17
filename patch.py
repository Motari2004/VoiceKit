"""
Stats: Show full text and allow playing audio from the Stats view.
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP  = os.path.join(BASE, "app.py")
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


def patch_app():
    print("\n[1/2] Patching app.py")
    backup(APP)
    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    # Update the recent query to include audio_url
    old_query = '"SELECT device_id, text, voice, created_at FROM history "'
    new_query = '"SELECT device_id, text, voice, audio_url, created_at FROM history "'
    
    if old_query in src:
        src = src.replace(old_query, new_query, 1)
        print("  [OK] Added audio_url to recent query")
    else:
        print("  WARN: Could not find recent query")

    # Update the return jsonify to send full text + audio_url
    old_recent_block = '''"recent": [
                {
                    "full_device_id": r["device_id"],
                    "page": "Generate",
                    "country": "—", 
                    "device_type": r["voice"],  # Show which voice they used
                    "user_agent": r["text"][:30] + "...", # Show the text they typed
                    "at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in (recent or [])
            ],'''

    new_recent_block = '''"recent": [
                {
                    "full_device_id": r["device_id"],
                    "page": "Generate",
                    "country": "—", 
                    "device_type": r["voice"],
                    "user_agent": r["text"], # FULL TEXT
                    "audio_url": r.get("audio_url"),
                    "at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in (recent or [])
            ],'''

    if old_recent_block in src:
        src = src.replace(old_recent_block, new_recent_block, 1)
        print("  [OK] Updated recent block to send full text + audio_url")
    else:
        # Try a looser match
        src = re.sub(
            r'"user_agent": r\["text"\]\[:30\] \+ "\.\.\."',
            '"user_agent": r["text"]',
            src
        )
        src = re.sub(
            r'"page": "Generate",\s*"country": "—",\s*"device_type": r\["voice"\],',
            '"page": "Generate",\n                    "country": "—",\n                    "device_type": r["voice"],\n                    "audio_url": r.get("audio_url"),',
            src
        )
        print("  [OK] Updated recent block (regex)")

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)


def patch_html():
    print("\n[2/2] Patching templates/index.html")
    backup(HTML)
    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # Replace the Recent rendering JS in the Stats inline script
    old_js = '''          // Recent
          if (s.recent && s.recent.length) {
            recentEl.innerHTML = '';
            s.recent.forEach(r => {
              const row = document.createElement('div');
              row.style.cssText = 'display:flex;flex-direction:column;gap:2px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);';
              const time = r.at ? new Date(r.at).toLocaleString() : '';
              
              row.innerHTML = 
                '<div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#fff;">' +
                  '<span>' + r.device_type + ' <span style="color:#888;font-family:monospace;">(' + r.full_device_id.slice(0,8) + '...)</span></span>' +
                  '<span style="color:#666;font-family:monospace;">' + time + '</span>' +
                '</div>' +
                '<div style="font-size:0.72rem;color:#aaa;font-style:italic;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
                  '"' + r.user_agent + '"' +
                '</div>';
              recentEl.appendChild(row);
            });
          } else { recentEl.innerHTML = '<div class="empty">No data</div>'; }'''

    new_js = '''          // Recent
          if (s.recent && s.recent.length) {
            recentEl.innerHTML = '';
            s.recent.forEach(r => {
              const row = document.createElement('div');
              row.style.cssText = 'display:flex;flex-direction:column;gap:6px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.06);';
              const time = r.at ? new Date(r.at).toLocaleString() : '';
              
              // Header: Voice + Device + Time
              const header = document.createElement('div');
              header.style.cssText = 'display:flex;justify-content:space-between;font-size:0.78rem;color:#fff;';
              header.innerHTML =
                '<span>' + r.device_type + ' <span style="color:#888;font-family:monospace;">(' + r.full_device_id.slice(0,8) + '...)</span></span>' +
                '<span style="color:#666;font-family:monospace;">' + time + '</span>';
              row.appendChild(header);

              // Full text (clickable to expand if long)
              const textDiv = document.createElement('div');
              textDiv.style.cssText = 'font-size:0.8rem;color:#bbb;font-style:italic;padding:8px;background:rgba(255,255,255,0.03);border-radius:6px;cursor:pointer;';
              textDiv.title = 'Click to expand';
              
              const fullText = r.user_agent || '';
              const preview = fullText.length > 80 ? fullText.slice(0, 80) + '...' : fullText;
              textDiv.textContent = '"' + preview + '"';
              
              let expanded = false;
              textDiv.onclick = () => {
                expanded = !expanded;
                textDiv.textContent = expanded ? '"' + fullText + '"' : '"' + preview + '"';
                textDiv.style.background = expanded ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)';
              };
              row.appendChild(textDiv);

              // Play button (if audio_url exists)
              if (r.audio_url) {
                const playBtn = document.createElement('button');
                playBtn.textContent = '▶ Play Audio';
                playBtn.style.cssText = 'align-self:flex-start;padding:4px 10px;font-size:0.7rem;background:rgba(34,211,238,0.1);border:1px solid rgba(34,211,238,0.3);color:#22d3ee;border-radius:6px;cursor:pointer;font-family:inherit;';
                
                let playing = false;
                playBtn.onclick = () => {
                  if (playing) return;
                  playing = true;
                  const audio = new Audio(r.audio_url);
                  playBtn.textContent = '■ Playing...';
                  audio.play();
                  audio.onended = () => {
                    playing = false;
                    playBtn.textContent = '▶ Play Audio';
                  };
                };
                row.appendChild(playBtn);
              }

              recentEl.appendChild(row);
            });
          } else { recentEl.innerHTML = '<div class="empty">No data</div>'; }'''

    if old_js in src:
        src = src.replace(old_js, new_js, 1)
        print("  [OK] Updated recent rendering JS")
    else:
        # Regex fallback
        pattern = re.compile(
            r'// Recent\s*\n\s*if \(s\.recent && s\.recent\.length\) \{.*?\} else \{ recentEl\.innerHTML = \'<div class="empty">No data</div>\'; \}',
            re.DOTALL
        )
        if pattern.search(src):
            src = pattern.sub(new_js, src, count=1)
            print("  [OK] Updated recent rendering JS (regex)")
        else:
            print("  WARN: Could not find recent JS block")

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)


if __name__ == "__main__":
    print("=" * 60)
    print(" VoiceKit — Full Text + Audio in Stats")
    print("=" * 60)
    patch_app()
    patch_html()
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print()
    print(" What changed:")
    print("   • Full text is now sent to the frontend")
    print("   • Click any text block to expand it")
    print("   • If Cloudinary URL exists, a '▶ Play Audio' button appears")
    print("=" * 60)