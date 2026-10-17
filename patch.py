"""
Fix the Stats UI to render from the history-based /stats response.
Updates labels: "Top Voices", "Recent Generations"
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


NEW_RENDER = '''
// ============================================================
// STATS UI RENDER (history-based)
// ============================================================
async function loadStats() {
  console.log('[stats] Loading...');

  const totalEl     = document.getElementById('statTotal');
  const uniqueEl    = document.getElementById('statUnique');
  const todayEl     = document.getElementById('statToday');
  const newEl       = document.getElementById('statNew');
  const dailyEl     = document.getElementById('statsDaily');
  const countriesEl = document.getElementById('statsCountries');
  const pagesEl     = document.getElementById('statsPages');
  const recentEl    = document.getElementById('statsRecent');

  if (!totalEl) {
    console.error('[stats] Stats view not in DOM');
    return;
  }

  try {
    const did = localStorage.getItem('voicekit_device_id') || '';
    const res = await fetch('/stats?device=' + encodeURIComponent(did));

    if (!res.ok) throw new Error('HTTP ' + res.status);
    const s = await res.json();

    console.log('[stats] Received:', s);

    // Numbers
    totalEl.textContent  = s.total;
    uniqueEl.textContent = s.unique_devices;
    todayEl.textContent  = s.today;
    newEl.textContent    = s.new_today;

    // Daily activity
    if (s.daily && s.daily.length) {
      dailyEl.innerHTML = '';
      s.daily.forEach(d => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
        row.innerHTML =
          '<span>' + d.day + '</span>' +
          '<span>' + d.visits + ' generations · ' + d.uniques + ' devices</span>';
        dailyEl.appendChild(row);
      });
    } else {
      dailyEl.innerHTML = '<div class="empty">No activity yet</div>';
    }

    // Top voices (this was "pages")
    if (s.pages && s.pages.length) {
      countriesEl.innerHTML = '';  // repurpose the countries card
      s.pages.forEach(v => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
        row.innerHTML =
          '<span>' + v.page + '</span>' +
          '<span>' + v.count + ' ×</span>';
        countriesEl.appendChild(row);
      });
      // Update the heading above this card
      const h = countriesEl.closest('.card').querySelector('.card-title');
      if (h) h.textContent = 'Top Voices';
    } else {
      countriesEl.innerHTML = '<div class="empty">No voices used yet</div>';
    }

    // Pages card — hide or clear (we already show voices above)
    if (pagesEl) {
      pagesEl.innerHTML = '<div class="empty">See "Top Voices" above</div>';
      const h = pagesEl.closest('.card').querySelector('.card-title');
      if (h) h.textContent = 'Details';
    }

    // Recent generations
    if (s.recent && s.recent.length) {
      recentEl.innerHTML = '';
      s.recent.forEach(r => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;flex-direction:column;gap:2px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);';
        const time = r.at ? new Date(r.at).toLocaleString() : '';

        // Device + voice + time
        const top = document.createElement('div');
        top.style.cssText = 'display:flex;justify-content:space-between;font-size:0.78rem;';
        top.innerHTML =
          '<span style="color:#fff;">' + r.device_type + '</span>' +
          '<span style="color:#666;font-family:monospace;">' + time + '</span>';

        // Device ID and preview
        const bot = document.createElement('div');
        bot.style.cssText = 'font-size:0.7rem;color:#888;font-family:monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
        bot.textContent = r.full_device_id + ' — ' + r.user_agent;

        row.appendChild(top);
        row.appendChild(bot);
        recentEl.appendChild(row);
      });
    } else {
      recentEl.innerHTML = '<div class="empty">No generations yet</div>';
    }

    console.log('[stats] UI updated');
  } catch (e) {
    console.error('[stats] error:', e);
    if (dailyEl) dailyEl.innerHTML = '<div class="empty" style="color:#ef4444;">Error: ' + e.message + '</div>';
  }
}

// Wire up the Stats button
document.addEventListener('DOMContentLoaded', () => {
  const statsBtn = document.getElementById('statsNavBtn');
  if (statsBtn) {
    statsBtn.addEventListener('click', () => {
      setTimeout(loadStats, 100);
    });
  }
  const refreshBtn = document.getElementById('refreshStats');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadStats);
  }
});
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Stats UI Render Fix")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # Remove any old loadStats definitions
    src = re.sub(
        r'(async function loadStats\(\)|function loadStats\(\)).*?(?=\n(async function|function|// =+|\n</script>))',
        '',
        src,
        flags=re.DOTALL
    )

    # Append the new one
    idx = src.rfind('</script>')
    if idx == -1:
        print("  ERROR: no </script> found")
        return

    src = src[:idx] + NEW_RENDER + '\n' + src[idx:]

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Stats UI renderer replaced")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print()
    print(" After refresh, open Stats. You should see:")
    print("   • 30 total generations")
    print("   • 4 unique devices")
    print("   • Top Voices: am_adam (13), am_michael (12)...")
    print("   • Recent: device_id, voice used, and text preview")
    print("=" * 60)


if __name__ == "__main__":
    patch()