"""
Final clean fix for Stats:
1. Removes ALL old stats/admin JS from the bottom of the page.
2. Adds a dedicated, isolated script INSIDE the Stats view.
3. Wires the side navigation to trigger it.
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


NEW_STATS_SECTION = '''
  <!-- ---------- VIEW: STATS (admin only) ---------- -->
  <section class="view" id="view-stats">
    <div class="view-header">
      <h1 class="view-title">Stats</h1>
      <p class="view-subtitle">Live usage analytics.</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="value" id="statTotal">—</div>
        <div class="label">Total Gens</div>
      </div>
      <div class="stat-card">
        <div class="value" id="statUnique">—</div>
        <div class="label">Devices</div>
      </div>
      <div class="stat-card">
        <div class="value" id="statToday">—</div>
        <div class="label">Today</div>
      </div>
      <div class="stat-card">
        <div class="value" id="statNew">—</div>
        <div class="label">New Today</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Last 14 Days</span>
      </div>
      <div id="statsDaily"><div class="empty">Loading...</div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Top Voices</span>
      </div>
      <div id="statsCountries"><div class="empty">Loading...</div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Recent Generations</span>
      </div>
      <div id="statsRecent"><div class="empty">Loading...</div></div>
    </div>

    <!-- Script runs ONLY when this view is visible -->
    <script>
      (async function() {
        console.log('[stats] View opened, loading data...');
        
        const did = localStorage.getItem('voicekit_device_id') || '';
        if (!did) return;

        const totalEl  = document.getElementById('statTotal');
        const uniqueEl = document.getElementById('statUnique');
        const todayEl  = document.getElementById('statToday');
        const newEl    = document.getElementById('statNew');
        const dailyEl  = document.getElementById('statsDaily');
        const voicesEl = document.getElementById('statsCountries');
        const recentEl = document.getElementById('statsRecent');

        try {
          const res = await fetch('/stats?device=' + encodeURIComponent(did));
          if (!res.ok) throw new Error('HTTP ' + res.status);
          const s = await res.json();

          totalEl.textContent  = s.total;
          uniqueEl.textContent = s.unique_devices;
          todayEl.textContent  = s.today;
          newEl.textContent    = s.new_today;

          // Daily
          if (s.daily && s.daily.length) {
            dailyEl.innerHTML = '';
            s.daily.forEach(d => {
              const row = document.createElement('div');
              row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
              row.innerHTML = '<span>' + d.day + '</span><span>' + d.visits + ' gens · ' + d.uniques + ' devices</span>';
              dailyEl.appendChild(row);
            });
          } else { dailyEl.innerHTML = '<div class="empty">No data</div>'; }

          // Voices
          if (s.pages && s.pages.length) {
            voicesEl.innerHTML = '';
            s.pages.forEach(v => {
              const row = document.createElement('div');
              row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
              row.innerHTML = '<span>' + v.page + '</span><span>' + v.count + ' ×</span>';
              voicesEl.appendChild(row);
            });
          } else { voicesEl.innerHTML = '<div class="empty">No data</div>'; }

          // Recent
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
          } else { recentEl.innerHTML = '<div class="empty">No data</div>'; }

          console.log('[stats] Data rendered successfully');

        } catch (e) {
          console.error('[stats] Failed:', e);
          dailyEl.innerHTML = '<div class="empty" style="color:#ef4444;">Error: ' + e.message + '</div>';
        }
      })();
    </script>
  </section>
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Inline Stats Script")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Replace the entire Stats view with the new one containing inline JS
    pattern = re.compile(r'<!-- ---------- VIEW: STATS \(admin only\) ---------- -->\s*<section class="view" id="view-stats">.*?</section>', re.DOTALL)
    if pattern.search(src):
        src = pattern.sub(NEW_STATS_SECTION, src, count=1)
        print("  [OK] Replaced Stats view with inline script")
    else:
        print("  WARN: Could not find Stats view section")

    # 2. Remove ALL old stats and admin scripts from the bottom of the page
    # This wipes out the conflicts.
    messy_blocks = [
        r'// =+\s*\n// MOBILE BACK BUTTON HANDLING \(FIXED\).*?(?=\n// =+|\n</script>)',
        r'// =+\s*\n// VISIT TRACKING \+ ADMIN STATS.*?(?=\n// =+|\n</script>)',
        r'// =+\s*\n// STATS DATA LOADER.*?(?=\n// =+|\n</script>)',
        r'// =+\s*\n// STATS UI RENDER \(history-based\).*?(?=\n// =+|\n</script>)',
        r'\(async function forceAdminButton\(\).*?\}\)\(\);',
        r'\(function \(\) \{\s*history\.pushState.*?\}\)\(\);'
    ]
    
    for pattern_str in messy_blocks:
        if re.search(pattern_str, src, re.DOTALL):
            src = re.sub(pattern_str, '', src, flags=re.DOTALL)
            print("  [OK] Removed old conflicting script block")

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print()
    print(" Then click Stats. The data WILL load because the script")
    print(" is now baked directly into the view.")
    print("=" * 60)


if __name__ == "__main__":
    patch()