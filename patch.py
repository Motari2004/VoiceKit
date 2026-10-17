"""
Update /stats to read from the 'history' table instead of 'visits'.
This means stats are driven by actual generations (real value),
and we can see exactly which devices are generating audio.
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
    """Return aggregate statistics based on actual generations (history)."""
    device_id = (request.args.get("device") or "").strip()
    if device_id not in ADMIN_DEVICES:
        return jsonify({"error": "forbidden"}), 403

    if not DATABASE_URL:
        return jsonify({"error": "no-db"}), 500

    try:
        init_db()

        # 1. Overall totals from history
        total_gens = db_execute("SELECT COUNT(*) AS n FROM history", fetch_one=True)
        unique_devs = db_execute("SELECT COUNT(DISTINCT device_id) AS n FROM history", fetch_one=True)
        
        today_gens = db_execute(
            "SELECT COUNT(*) AS n FROM history WHERE created_at > NOW() - INTERVAL '1 day'",
            fetch_one=True,
        )
        
        new_today = db_execute(
            "SELECT COUNT(*) AS n FROM history "
            "WHERE created_at > NOW() - INTERVAL '1 day' "
            "AND device_id NOT IN ("
            "  SELECT device_id FROM history WHERE created_at < NOW() - INTERVAL '1 day'"
            ")",
            fetch_one=True,
        )

        # 2. Top Voices used
        voices = db_execute(
            "SELECT voice, COUNT(*) AS n FROM history "
            "GROUP BY voice ORDER BY n DESC LIMIT 10",
            fetch=True,
        )

        # 3. Daily activity
        daily = db_execute(
            "SELECT DATE(created_at) AS day, COUNT(*) AS gens, "
            "COUNT(DISTINCT device_id) AS uniques "
            "FROM history WHERE created_at > NOW() - INTERVAL '14 days' "
            "GROUP BY DATE(created_at) ORDER BY day DESC",
            fetch=True,
        )

        # 4. Recent Generations (The real proof of life)
        recent = db_execute(
            "SELECT device_id, text, voice, created_at FROM history "
            "ORDER BY created_at DESC LIMIT 20",
            fetch=True,
        )

        return jsonify({
            "total": total_gens["n"] if total_gens else 0,
            "unique_devices": unique_devs["n"] if unique_devs else 0,
            "today": today_gens["n"] if today_gens else 0,
            "new_today": new_today["n"] if new_today else 0,
            "pages": [{"page": r["voice"], "count": r["n"]} for r in (voices or [])], # Now shows top voices
            "daily": [
                {"day": str(r["day"]), "visits": r["gens"], "uniques": r["uniques"]}
                for r in (daily or [])
            ],
            "recent": [
                {
                    "full_device_id": r["device_id"],
                    "page": "Generate",
                    "country": "—", 
                    "device_type": r["voice"],  # Show which voice they used
                    "user_agent": r["text"][:30] + "...", # Show the text they typed
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
    print(" VoiceKit — Real Stats from History")
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
        print("  [OK] Replaced /stats route to read from history table")
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
    print(" Test with curl:")
    print('   curl -s "https://voicekit-prod.vercel.app/stats?device=dev_tw41yvzz4kpmvb8ktba"')
    print()
    print(" What changed:")
    print("   • Stats now count actual voice generations")
    print("   • 'Top Pages' will now show 'Top Voices' (e.g. am_adam, af_heart)")
    print("   • 'Recent Visits' will show the device ID and the text they typed")
    print("=" * 60)


if __name__ == "__main__":
    patch()