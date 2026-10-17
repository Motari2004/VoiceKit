"""
Fix: The Stats button appears, but the data doesn't load.
- Adds a dedicated click listener specifically for the Stats button.
- Includes the loadStats function directly in the patch to ensure it exists.
- Adds a refresh button inside the Stats view.
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


NEW_STATS_JS = '''
// ============================================================
// STATS DATA LOADER
// ============================================================
async function loadStats() {
  console.log('[stats] Fetching data...');
  
  const totalEl     = document.getElementById('statTotal');
  const uniqueEl    = document.getElementById('statUnique');
  const todayEl     = document.getElementById('statToday');
  const newEl       = document.getElementById('statNew');
  const dailyEl     = document.getElementById('statsDaily');
  const countriesEl = document.getElementById('statsCountries');
  const pagesEl     = document.getElementById('statsPages');
  const recentEl    = document.getElementById('statsRecent');

  if (!totalEl) {
    console.error('[stats] Stats view elements not found in DOM');
    return;
  }

  try {
    const did = localStorage.getItem('voicekit_device_id') || '';
    const res = await fetch('/stats?device=' + encodeURIComponent(did));
    
    if (!res.ok) {
      throw new Error('HTTP ' + res.status);
    }
    
    const s = await res.json();
    console.log('[stats] Data received:', s);

    // Update the numbers
    totalEl.textContent  = s.total;
    uniqueEl.textContent = s.unique_devices;
    todayEl.textContent  = s.today;
    newEl.textContent    = s.new_today;

    // Render Daily
    if (s.daily && s.daily.length) {
      dailyEl.innerHTML = '';
      s.daily.forEach(d => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
        row.innerHTML = '<span>' + d.day + '</span><span>' + d.visits + ' visits · ' + d.uniques + ' unique</span>';
        dailyEl.appendChild(row);
      });
    } else {
      dailyEl.innerHTML = '<div class="empty">No visits yet</div>';
    }

    // Render Countries
    if (s.countries && s.countries.length) {
      countriesEl.innerHTML = '';
      s.countries.forEach(c => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
        row.innerHTML = '<span>' + c.country + '</span><span>' + c.count + '</span>';
        countriesEl.appendChild(row);
      });
    } else {
      countriesEl.innerHTML = '<div class="empty">No data</div>';
    }

    // Render Pages
    if (s.pages && s.pages.length) {
      pagesEl.innerHTML = '';
      s.pages.forEach(p => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
        row.innerHTML = '<span>' + p.page + '</span><span>' + p.count + '</span>';
        pagesEl.appendChild(row);
      });
    } else {
      pagesEl.innerHTML = '<div class="empty">No data</div>';
    }

    // Render Recent
    if (s.recent && s.recent.length) {
      recentEl.innerHTML = '';
      s.recent.forEach(r => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.78rem;font-family:monospace;';
        const time = r.at ? new Date(r.at).toLocaleTimeString() : '';
        row.innerHTML = '<span>' + r.device + ' → ' + r.page + '</span><span>' + r.country + ' · ' + time + '</span>';
        recentEl.appendChild(row);
      });
    } else {
      recentEl.innerHTML = '<div class="empty">No visits yet</div>';
    }
  } catch (e) {
    console.error('[stats] Error loading data:', e);
    if (dailyEl) dailyEl.innerHTML = '<div class="empty" style="color:#ef4444;">Error: ' + e.message + '</div>';
  }
}

// Listen for clicks specifically on the Stats button
document.addEventListener('DOMContentLoaded', () => {
  const statsBtn = document.getElementById('statsNavBtn');
  if (statsBtn) {
    statsBtn.addEventListener('click', () => {
      console.log('[stats] Button clicked, loading data...');
      loadStats();
    });
  }
});
'''

def patch():
    print("=" * 60)
    print(" VoiceKit — Fix Stats Data Loading")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Add a Refresh button to the Stats header if it doesn't exist
    if 'id="refreshStats"' not in src:
        header_pattern = r'(<div class="view-header">\s*<h1 class="view-title">Stats</h1>)'
        if re.search(header_pattern, src):
            # Just add the refresh button below the title
            refresh_btn = '''
      <button id="refreshStats" style="margin-top: 10px; padding: 6px 12px; background: transparent; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; color: #b0b0b8; font-family: inherit; font-size: 0.75rem; cursor: pointer;">↻ Refresh Data</button>'''
            src = re.sub(
                r'(<p class="view-subtitle">Live visitor and usage analytics. Admin only.</p>)',
                r'\1' + refresh_btn,
                src
            )
            print("  [OK] Added Refresh button to Stats header")

    # 2. Ensure the Refresh button actually calls loadStats
    if 'refreshStats' in src and 'refreshStats.addEventListener' not in src:
        refresh_js = '''
// Wire up the refresh button
document.addEventListener('DOMContentLoaded', () => {
  const refreshBtn = document.getElementById('refreshStats');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      console.log('[stats] Refresh clicked');
      loadStats();
    });
  }
});
'''
        # Insert right before </script>
        idx = src.rfind('</script>')
        if idx != -1:
            src = src[:idx] + refresh_js + '\n' + src[idx:]
            print("  [OK] Wired up Refresh button")

    # 3. Append the new Stats JS (overwriting any old loadStats functions)
    # First, remove old loadStats definitions to avoid conflicts
    src = re.sub(
        r'async function loadStats\(\).*?(?=\nasync function|\n// =+|\n</script>)',
        '',
        src,
        flags=re.DOTALL
    )

    idx = src.rfind('</script>')
    if idx != -1:
        src = src[:idx] + NEW_STATS_JS + '\n' + src[idx:]
        print("  [OK] Injected new loadStats function")

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print()
    print(" Then:")
    print("   1. Click the Stats button.")
    print("   2. Open the browser console (F12).")
    print("   3. Look for '[stats] Data received:' — this shows the exact JSON.")
    print("   4. If there's an error, it will appear in red.")
    print("=" * 60)


if __name__ == "__main__":
    patch()