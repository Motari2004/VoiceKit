"""
Update /stats to return FULL data:
- Complete device_id (no truncation)
- Raw user_agent string
- Parsed device_type (iPhone, Android, etc.)
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP  = os.path.join(BASE, "app.py")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


NEW_STATS_ROUTE = '''@app.route("/stats")
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
            "SELECT device_id, page, country, user_agent, created_at FROM visits "
            "ORDER BY created_at DESC LIMIT 20",
            fetch=True,
        )

        def detect_device(ua):
            if not ua: return "unknown"
            ua = ua.lower()
            if "iphone" in ua: return "iPhone"
            if "ipad" in ua: return "iPad"
            if "android" in ua: return "Android"
            if "mac os" in ua or "macintosh" in ua: return "Mac"
            if "windows" in ua: return "Windows"
            if "linux" in ua: return "Linux"
            return "Other"

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
                    "full_device_id": r["device_id"],       # UNTRUNCATED
                    "page": r["page"],
                    "country": r["country"],
                    "device_type": detect_device(r["user_agent"]),  # Parsed
                    "user_agent": r["user_agent"],           # Raw string
                    "at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in (recent or [])
            ],
        })
    except Exception as e:
        print(f"[stats] failed: {e}")
        return jsonify({"error": str(e)[:200]}), 500

'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Full Stats Data")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Match the entire /stats route
    pattern = re.compile(
        r'@app\.route\("/stats"\)\s*\ndef stats\(\):.*?(?=\n# =+|\n@app\.route|\Z)',
        re.DOTALL
    )

    if pattern.search(src):
        src = pattern.sub(NEW_STATS_ROUTE + "\n", src, count=1)
        print("  [OK] Replaced /stats route with full data version")
    else:
        print("  ERROR: Could not find /stats route")

    if src == original:
        print("  No changes made.")
        return

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" Then run your curl again:")
    print('   curl -s "https://voicekit-prod.vercel.app/stats?device=dev_tw41yvzz4kpmvb8ktba"')
    print()
    print(" You will now see:")
    print("   - full_device_id (complete string)")
    print("   - device_type (iPhone / Android / Mac / etc.)")
    print("   - user_agent (raw browser string)")
    print("=" * 60)


if __name__ == "__main__":
    patch()