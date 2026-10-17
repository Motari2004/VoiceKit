"""
Clean up the bottom of index.html.
1. Removes all duplicate/old JS blocks.
2. Removes JS that tries to 'force' the admin button (Jinja handles it now).
3. Leaves only one clean loadStats function.
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


CLEAN_JS = '''
// ============================================================
// STATS LOADER (clean)
// ============================================================
async function loadStats() {
  console.log('[stats] Loading...');

  const totalEl     = document.getElementById('statTotal');
  const uniqueEl    = document.getElementById('statUnique');
  const todayEl     = document.getElementById('statToday');
  const newEl       = document.getElementById('statNew');
  const dailyEl     = document.getElementById('statsDaily');
  const voicesEl    = document.getElementById('statsCountries');
  const recentEl    = document.getElementById('statsRecent');

  if (!totalEl) return;

  try {
    const did = localStorage.getItem('voicekit_device_id') || '';
    const res = await fetch('/stats?device=' + encodeURIComponent(did));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const s = await res.json();

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
        row.innerHTML = '<span>' + d.day + '</span><span>' + d.visits + ' gens · ' + d.uniques + ' devices</span>';
        dailyEl.appendChild(row);
      });
    } else {
      dailyEl.innerHTML = '<div class="empty">No activity yet</div>';
    }

    // Top voices
    if (s.pages && s.pages.length) {
      voicesEl.innerHTML = '';
      s.pages.forEach(v => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.82rem;';
        row.innerHTML = '<span>' + v.page + '</span><span>' + v.count + ' ×</span>';
        voicesEl.appendChild(row);
      });
    } else {
      voicesEl.innerHTML = '<div class="empty">No voices yet</div>';
    }

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
    } else {
      recentEl.innerHTML = '<div class="empty">No generations yet</div>';
    }

    console.log('[stats] UI updated');
  } catch (e) {
    console.error('[stats] error:', e);
    if (dailyEl) dailyEl.innerHTML = '<div class="empty" style="color:#ef4444;">Error: ' + e.message + '</div>';
  }
}

// Wire buttons
document.addEventListener('DOMContentLoaded', () => {
  const statsBtn = document.getElementById('statsNavBtn');
  if (statsBtn) {
    statsBtn.addEventListener('click', () => setTimeout(loadStats, 100));
  }
  const refreshBtn = document.getElementById('refreshStats');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadStats);
  }
});
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Clean Up Stats JS")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Locate the final </script> tag
    last_script_idx = src.rfind('</script>')
    if last_script_idx == -1:
        print("  ERROR: no closing </script> found")
        return

    # 2. Find the start of the messy area
    # We'll cut out everything from the "MOBILE BACK BUTTON HANDLING (FIXED)" block
    # up to the end of the script, then re-add only the back-button fix and stats loader.
    start_idx = src.find('// ============================================================\n// MOBILE BACK BUTTON HANDLING (FIXED)')
    
    # If not found, look for the admin detection
    if start_idx == -1:
        start_idx = src.find('// ============================================================\n// VISIT TRACKING + ADMIN STATS')

    if start_idx == -1:
        print("  WARN: Could not find the start of the messy JS. Appending only.")
        src = src[:last_script_idx] + CLEAN_JS + '\n' + src[last_script_idx:]
    else:
        print("  [OK] Found messy JS start — removing it")
        # We want to keep the back button logic, but it's also in the mess.
        # Actually, let's just replace everything from start_idx to the end with:
        # 1. Back button logic (simplified, so it doesn't break)
        # 2. The clean stats loader.
        
        back_button_js = '''
// ============================================================
// MOBILE BACK BUTTON HANDLING (simple)
// ============================================================
(function () {
  history.pushState({ view: 'generate', base: true }, '', '#generate');
  
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const view = btn.dataset.view;
      if (view && view !== 'generate') {
        history.pushState({ view: view }, '', '#' + view);
      }
    });
  });

  window.addEventListener('popstate', (e) => {
    if (e.state && e.state.view) {
      switchToView(e.state.view);
    } else {
      switchToView('generate');
      history.pushState({ view: 'generate', base: true }, '', '#generate');
    }
  });

  function switchToView(viewName) {
    document.querySelectorAll('.nav-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.view === viewName);
    });
    document.querySelectorAll('.view').forEach(v => {
      v.classList.toggle('active', v.id === 'view-' + viewName);
    });
    if (viewName === 'history' && typeof window.loadServerHistory === 'function') {
      window.loadServerHistory();
    }
  }
})();
'''
        src = src[:start_idx] + back_button_js + '\n' + CLEAN_JS + '\n' + src[last_script_idx:]
        print("  [OK] Replaced messy JS with clean stats loader + back button")

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print(" Deploy:")
    print("   vercel --prod")
    print("   Hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()