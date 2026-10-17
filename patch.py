"""
Add a 'Device List' to the Stats view.
- Backend: /stats now returns a `devices` array (full IDs, count, first seen, last seen).
- Frontend: Adds a new "Devices" card to the Stats view.
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

    # Add the devices query to /stats
    if '"devices":' not in src:
        # Find the return jsonify in /stats
        return_anchor = 'return jsonify({\n            "total": total["n"] if total else 0,'
        
        devices_block = '''"devices": [
                {
                    "id": r["device_id"],
                    "count": r["n"],
                    "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
                    "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None
                }
                for r in (db_execute(
                    "SELECT device_id, COUNT(*) AS n, "
                    "MIN(created_at) AS first_seen, MAX(created_at) AS last_seen "
                    "FROM history GROUP BY device_id "
                    "ORDER BY n DESC",
                    fetch=True
                ) or [])
            ],
            '''
        
        if return_anchor in src:
            src = src.replace(return_anchor, return_anchor + '\n            ' + devices_block, 1)
            print("  [OK] Added devices list to /stats response")
        else:
            # Fallback: insert before "recent":
            src = src.replace('"recent": [', devices_block + '"recent": [', 1)
            print("  [OK] Added devices list (fallback)")

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)


def patch_html():
    print("\n[2/2] Patching templates/index.html")
    backup(HTML)
    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Add the Devices card before "Recent Generations"
    if 'id="statsDevices"' not in src:
        recent_card_anchor = '''    <div class="card">
      <div class="card-header">
        <span class="card-title">Recent Generations</span>'''
        
        devices_card = '''    <div class="card">
      <div class="card-header">
        <span class="card-title">Devices</span>
      </div>
      <div id="statsDevices"><div class="empty">Loading...</div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Recent Generations</span>'''
        
        if recent_card_anchor in src:
            src = src.replace(recent_card_anchor, devices_card, 1)
            print("  [OK] Added Devices card to HTML")
        else:
            print("  WARN: Could not find Recent Generations card to insert before")

    # 2. Add the devices rendering logic to the inline stats script
    if 'statsDevices' in src and 'devicesEl' not in src:
        # Find the end of the recent rendering (before the catch block)
        anchor = "console.log('[stats] Data rendered successfully');"
        
        devices_js = '''
          // Devices List
          const devicesEl = document.getElementById('statsDevices');
          if (s.devices && s.devices.length) {
            devicesEl.innerHTML = '';
            s.devices.forEach(d => {
              const row = document.createElement('div');
              row.style.cssText = 'padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.8rem;';
              
              const last = d.last_seen ? new Date(d.last_seen).toLocaleString() : '';
              const first = d.first_seen ? new Date(d.first_seen).toLocaleDateString() : '';
              
              row.innerHTML = 
                '<div style="display:flex;justify-content:space-between;margin-bottom:2px;">' +
                  '<span style="font-family:monospace;color:#fff;font-weight:600;">' + d.id + '</span>' +
                  '<span style="color:#4ade80;font-weight:600;">' + d.count + ' gens</span>' +
                '</div>' +
                '<div style="color:#888;font-size:0.7rem;display:flex;justify-content:space-between;">' +
                  '<span>First: ' + first + '</span>' +
                  '<span>Last: ' + last + '</span>' +
                '</div>';
              devicesEl.appendChild(row);
            });
          } else if (devicesEl) {
            devicesEl.innerHTML = '<div class="empty">No devices yet</div>';
          }

          '''
        
        if anchor in src:
            src = src.replace(anchor, devices_js + anchor, 1)
            print("  [OK] Added devices rendering logic")
        else:
            print("  WARN: Could not find anchor for devices JS")

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)


if __name__ == "__main__":
    print("=" * 60)
    print(" VoiceKit — Device List")
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
    print(" After deploy, the Stats view will show a new 'Devices' card")
    print(" with:")
    print("   • Full device ID")
    print("   • Total generations by that device")
    print("   • First seen date")
    print("   • Last seen date")
    print("=" * 60)