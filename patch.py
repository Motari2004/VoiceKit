"""
VoiceKit — Visit Tracking + Admin Stats
- Logs every visit to a `visits` table in Neon
- Adds a /stats endpoint that returns aggregate numbers
- Only devices listed in ADMIN_DEVICES can see the Stats nav button
- The whole Stats view is hidden by default
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, "app.py")
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


# ============================================================
# Backend additions to app.py
# ============================================================
VISITS_SQL = '''
                    # ---------- visits ----------
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS visits (
                            id          SERIAL PRIMARY KEY,
                            device_id   TEXT NOT NULL,
                            page        TEXT,
                            referrer    TEXT,
                            user_agent  TEXT,
                            country     TEXT,
                            created_at  TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)

                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_visits_device
                        ON visits (device_id, created_at DESC);
                    """)

                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_visits_date
                        ON visits (created_at DESC);
                    """)
'''


TRACK_ROUTE = '''

# ============================================================
# VISIT TRACKING
# ============================================================
ADMIN_DEVICES = set(
    d.strip() for d in os.environ.get("ADMIN_DEVICES", "").split(",") if d.strip()
)


@app.route("/track", methods=["POST", "OPTIONS"])
def track_visit():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data = request.get_json() or {}
        device_id  = (data.get("device") or "").strip()
        page       = (data.get("page") or "generate").strip()[:50]
        referrer   = (data.get("referrer") or "")[:200]
        user_agent = (request.headers.get("User-Agent") or "")[:200]
        country    = (request.headers.get("x-vercel-ip-country") or "unknown")[:3]

        if not device_id:
            return jsonify({"error": "Missing device"}), 400
        if not DATABASE_URL:
            return jsonify({"status": "no-db"})

        init_db()
        db_execute(
            "INSERT INTO visits (device_id, page, referrer, user_agent, country) "
            "VALUES (%s, %s, %s, %s, %s)",
            (device_id, page, referrer, user_agent, country),
        )
        return jsonify({"status": "tracked"})
    except Exception as e:
        print(f"[db] track failed: {e}")
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/is-admin")
def is_admin():
    device_id = (request.args.get("device") or "").strip()
    return jsonify({"admin": device_id in ADMIN_DEVICES})


@app.route("/stats")
def stats():
    """Return aggregate visit statistics. Admin only."""
    device_id = (request.args.get("device") or "").strip()
    if device_id not in ADMIN_DEVICES:
        return jsonify({"error": "forbidden"}), 403

    if not DATABASE_URL:
        return jsonify({"error": "no-db"}), 500

    try:
        init_db()

        total = db_execute("SELECT COUNT(*) AS n FROM visits", fetch_one=True)
        unique = db_execute("SELECT COUNT(DISTINCT device_id) AS n FROM visits", fetch_one=True)
        today = db_execute(
            "SELECT COUNT(*) AS n FROM visits WHERE created_at > NOW() - INTERVAL '1 day'",
            fetch_one=True,
        )
        new_today = db_execute(
            "SELECT COUNT(*) AS n FROM visits "
            "WHERE created_at > NOW() - INTERVAL '1 day' "
            "AND device_id NOT IN ("
            "  SELECT device_id FROM visits WHERE created_at < NOW() - INTERVAL '1 day'"
            ")",
            fetch_one=True,
        )
        countries = db_execute(
            "SELECT country, COUNT(*) AS n FROM visits "
            "WHERE country IS NOT NULL AND country != 'unknown' "
            "GROUP BY country ORDER BY n DESC LIMIT 10",
            fetch=True,
        )
        pages = db_execute(
            "SELECT page, COUNT(*) AS n FROM visits "
            "GROUP BY page ORDER BY n DESC LIMIT 10",
            fetch=True,
        )
        daily = db_execute(
            "SELECT DATE(created_at) AS day, COUNT(*) AS visits, "
            "COUNT(DISTINCT device_id) AS uniques "
            "FROM visits WHERE created_at > NOW() - INTERVAL '14 days' "
            "GROUP BY DATE(created_at) ORDER BY day DESC",
            fetch=True,
        )
        recent = db_execute(
            "SELECT device_id, page, country, created_at FROM visits "
            "ORDER BY created_at DESC LIMIT 20",
            fetch=True,
        )

        return jsonify({
            "total": total["n"] if total else 0,
            "unique_devices": unique["n"] if unique else 0,
            "today": today["n"] if today else 0,
            "new_today": new_today["n"] if new_today else 0,
            "countries": [{"country": r["country"], "count": r["n"]} for r in (countries or [])],
            "pages": [{"page": r["page"], "count": r["n"]} for r in (pages or [])],
            "daily": [
                {"day": str(r["day"]), "visits": r["visits"], "uniques": r["uniques"]}
                for r in (daily or [])
            ],
            "recent": [
                {
                    "device": r["device_id"][:10] + "...",
                    "page": r["page"],
                    "country": r["country"],
                    "at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in (recent or [])
            ],
        })
    except Exception as e:
        print(f"[stats] failed: {e}")
        return jsonify({"error": str(e)[:200]}), 500

'''


def patch_app():
    print("\n[1/2] Patching app.py")
    if not os.path.exists(APP):
        print(f"  ERROR: {APP} not found")
        return False
    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # 1) Add visits table to init_db
    if 'CREATE TABLE IF NOT EXISTS visits' not in src:
        anchor = 'cur.execute("""\n                        CREATE INDEX IF NOT EXISTS idx_history_device'
        if anchor in src:
            # Insert before the closing of the try in init_db
            insertion_point = src.find('conn.commit()', src.find('def init_db'))
            if insertion_point != -1:
                src = src[:insertion_point] + VISITS_SQL + '\n                ' + src[insertion_point:]
                changes.append("visits table")

    # 2) Add routes before "NO app.run()"
    if '/track' not in src:
        anchor = "# ============================================================\n# NO app.run()"
        if anchor in src:
            src = src.replace(anchor, TRACK_ROUTE + "\n" + anchor, 1)
            changes.append("track + stats routes")

    if src == original:
        print("  No changes to app.py")
        return True

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"  [OK] Applied: {', '.join(changes)}")
    return True


# ============================================================
# Frontend additions
# ============================================================
NEW_NAV_BTN = '''
    <button class="nav-btn admin-only" data-view="stats" style="display: none;">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="20" x2="12" y2="10"></line>
        <line x1="18" y1="20" x2="18" y2="4"></line>
        <line x1="6" y1="20" x2="6" y2="16"></line>
      </svg>
      Stats
    </button>
'''


NEW_STATS_VIEW = '''
  <!-- ---------- VIEW: STATS (admin only) ---------- -->
  <section class="view" id="view-stats">
    <div class="view-header">
      <h1 class="view-title">Stats</h1>
      <p class="view-subtitle">Live visitor and usage analytics. Admin only.</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="value" id="statTotal">—</div>
        <div class="label">Total Visits</div>
      </div>
      <div class="stat-card">
        <div class="value" id="statUnique">—</div>
        <div class="label">Unique Devices</div>
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
        <button id="refreshStats" style="
          padding: 6px 12px;
          background: transparent;
          border: 1px solid rgba(255,255,255,0.15);
          border-radius: 6px;
          color: #b0b0b8;
          font-family: inherit;
          font-size: 0.72rem;
          cursor: pointer;
        ">↻ Refresh</button>
      </div>
      <div id="statsDaily"><div class="empty">Loading...</div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Top Countries</span>
      </div>
      <div id="statsCountries"><div class="empty">Loading...</div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Top Pages</span>
      </div>
      <div id="statsPages"><div class="empty">Loading...</div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Recent Visits</span>
      </div>
      <div id="statsRecent"><div class="empty">Loading...</div></div>
    </div>
  </section>
'''


NEW_JS = '''
// ============================================================
// VISIT TRACKING + ADMIN STATS
// ============================================================
async function trackVisit(page) {
  try {
    await fetch('/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device: DEVICE_ID,
        page: page || 'generate',
        referrer: document.referrer || ''
      })
    });
  } catch (e) {
    // silent
  }
}

// Track every view switch
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const view = btn.dataset.view;
    if (view) trackVisit(view);
  });
});

// Track initial load
trackVisit('generate');

// ---------- Admin detection ----------
async function checkAdmin() {
  try {
    const res = await fetch('/is-admin?device=' + encodeURIComponent(DEVICE_ID));
    const data = await res.json();
    if (data.admin) {
      document.querySelectorAll('.admin-only').forEach(el => {
        el.style.display = '';
      });
      console.log('[admin] mode enabled');
    }
  } catch (e) {
    console.warn('[admin] check failed:', e);
  }
}
checkAdmin();

// ---------- Stats loading ----------
async function loadStats() {
  const totalEl     = document.getElementById('statTotal');
  const uniqueEl    = document.getElementById('statUnique');
  const todayEl     = document.getElementById('statToday');
  const newEl       = document.getElementById('statNew');
  const dailyEl     = document.getElementById('statsDaily');
  const countriesEl = document.getElementById('statsCountries');
  const pagesEl     = document.getElementById('statsPages');
  const recentEl    = document.getElementById('statsRecent');

  if (!totalEl) return; // Stats view not on page

  try {
    const res = await fetch('/stats?device=' + encodeURIComponent(DEVICE_ID));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const s = await res.json();

    totalEl.textContent  = s.total;
    uniqueEl.textContent = s.unique_devices;
    todayEl.textContent  = s.today;
    newEl.textContent    = s.new_today;

    // Daily
    if (s.daily.length) {
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

    // Countries
    if (s.countries.length) {
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

    // Pages
    if (s.pages.length) {
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

    // Recent
    if (s.recent.length) {
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
    console.error('[stats] load failed:', e);
    if (dailyEl) dailyEl.innerHTML = '<div class="empty" style="color:#ef4444;">Failed to load stats</div>';
  }
}

// Load stats when the Stats view opens
document.querySelectorAll('.nav-btn[data-view="stats"]').forEach(btn => {
  btn.addEventListener('click', () => setTimeout(loadStats, 100));
});

// Refresh button
document.addEventListener('click', (e) => {
  if (e.target.id === 'refreshStats') loadStats();
});
'''


def patch_html():
    print("\n[2/2] Patching templates/index.html")
    if not os.path.exists(HTML):
        print(f"  ERROR: {HTML} not found")
        return False
    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # 1) Add Stats nav button after About
    if 'data-view="stats"' not in src:
        anchor = '''    <button class="nav-btn" data-view="about">'''
        if anchor in src:
            # Find the closing </button> for About
            idx = src.find(anchor)
            end = src.find('</button>', idx) + len('</button>')
            src = src[:end] + '\n' + NEW_NAV_BTN + src[end:]
            changes.append("stats nav button")

    # 2) Add Stats view before </main>
    if 'id="view-stats"' not in src:
        anchor = "</main>"
        if anchor in src:
            src = src.replace(anchor, NEW_STATS_VIEW + '\n' + anchor, 1)
            changes.append("stats view")

    # 3) Add JS before closing </script>
    if 'function trackVisit' not in src:
        idx = src.rfind('</script>')
        if idx != -1:
            src = src[:idx] + NEW_JS + '\n' + src[idx:]
            changes.append("tracking + stats JS")

    if src == original:
        print("  No changes to index.html")
        return True

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"  [OK] Applied: {', '.join(changes)}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print(" VoiceKit — Visit Tracking + Admin Stats")
    print("=" * 60)

    ok1 = patch_app()
    ok2 = patch_html()

    print()
    print("=" * 60)
    print(" DONE" if (ok1 and ok2) else " DONE WITH ERRORS")
    print("=" * 60)
    print()
    print(" NEXT — set your ADMIN_DEVICES env var in Vercel:")
    print()
    print("   1. Open your site on your own device")
    print("   2. Open DevTools → Console → run:")
    print("        localStorage.getItem('voicekit_device_id')")
    print("   3. Copy the value (e.g., 'dev_tw41yvzz4kpmvb8ktba')")
    print("   4. Vercel → Settings → Environment Variables")
    print("      Name:  ADMIN_DEVICES")
    print("      Value: dev_tw41yvzz4kpmvb8ktba")
    print("   5. Redeploy: vercel --prod")
    print()
    print(" After that, only your device sees the Stats nav button.")
    print("=" * 60)