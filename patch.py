"""
VoiceKit — Neon Postgres Tuning
Neon-specific improvements:
  - Explicit SSL enforcement
  - TCP keepalives (Neon drops idle serverless connections)
  - Automatic reconnect on stale connections
  - Connection pooler compatibility
  - Better error messages
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


NEW_DB_SECTION = '''# ============================================================
# DATABASE — Neon Postgres
# ============================================================
import urllib.parse

def _normalize_db_url(url):
    """Strip psycopg-incompatible query params (channel_binding, etc.)."""
    if not url:
        return url
    # Remove channel_binding — psycopg doesn't support it
    url = re.sub(r'[?&]channel_binding=[^&]*', '', url)
    # Ensure sslmode=require for Neon
    if 'sslmode=' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}sslmode=require"
    # Clean up doubled separators
    url = re.sub(r'[?&]+$', '', url)
    url = re.sub(r'[?&]{2,}', '&', url)
    return url


def get_db():
    """Open a new connection to Neon with keepalives enabled."""
    if not DATABASE_URL:
        return None
    url = _normalize_db_url(DATABASE_URL)
    return psycopg.connect(
        url,
        row_factory=dict_row,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
        connect_timeout=10,
    )


def init_db():
    global _db_initialized
    if _db_initialized:
        return
    with _db_lock:
        if _db_initialized:
            return
        if not DATABASE_URL:
            print("[db] DATABASE_URL not set — persistence disabled")
            _db_initialized = True
            return
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS favorites (
                            device_id  TEXT NOT NULL,
                            voice_id   TEXT NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            PRIMARY KEY (device_id, voice_id)
                        );
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS history (
                            id         SERIAL PRIMARY KEY,
                            device_id  TEXT NOT NULL,
                            text       TEXT NOT NULL,
                            voice      TEXT NOT NULL,
                            speed      REAL NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_history_device
                        ON history (device_id, created_at DESC);
                    """)
                conn.commit()
            print("[db] Tables ready")
        except Exception as e:
            print(f"[db] init failed: {e}")
        finally:
            _db_initialized = True


def db_execute(query, params=None, fetch=False, fetch_one=False):
    """
    Execute a query with automatic retry on stale connection.
    Neon's serverless pooler may close idle connections.
    """
    for attempt in range(2):
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    if fetch:
                        result = cur.fetchall()
                    elif fetch_one:
                        result = cur.fetchone()
                    else:
                        result = None
                conn.commit()
                return result
        except psycopg.OperationalError as e:
            # Connection dropped — retry once
            print(f"[db] connection error (attempt {attempt+1}): {e}")
            if attempt == 0:
                continue
            raise
        except Exception:
            raise
    return None


'''


# The updated routes that use db_execute
NEW_ROUTES = '''# ---------- FAVORITES ----------
@app.route("/favorites", methods=["GET"])
def get_favorites():
    device_id = (request.args.get("device") or "").strip()
    if not device_id or not DATABASE_URL:
        return jsonify({"favorites": []})

    try:
        init_db()
        rows = db_execute(
            "SELECT voice_id FROM favorites WHERE device_id = %s ORDER BY created_at",
            (device_id,),
            fetch=True,
        )
        return jsonify({"favorites": [r["voice_id"] for r in rows]})
    except Exception as e:
        print(f"[db] get favorites failed: {e}")
        return jsonify({"favorites": [], "error": str(e)[:200]})


@app.route("/favorites", methods=["POST", "OPTIONS"])
def save_favorites():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data = request.get_json() or {}
        device_id = (data.get("device") or "").strip()
        voice_ids = data.get("favorites") or []

        if not device_id:
            return jsonify({"error": "Missing 'device'"}), 400
        if not isinstance(voice_ids, list):
            return jsonify({"error": "'favorites' must be a list"}), 400

        if not DATABASE_URL:
            return jsonify({"status": "no-db", "favorites": voice_ids})

        init_db()

        with get_db() as conn:
            with conn.cursor() as cur:
                if voice_ids:
                    cur.execute(
                        "DELETE FROM favorites WHERE device_id = %s AND voice_id != ALL(%s)",
                        (device_id, voice_ids),
                    )
                else:
                    cur.execute("DELETE FROM favorites WHERE device_id = %s", (device_id,))

                for vid in voice_ids:
                    cur.execute(
                        "INSERT INTO favorites (device_id, voice_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (device_id, vid),
                    )
            conn.commit()

        return jsonify({"status": "saved", "favorites": voice_ids})
    except Exception as e:
        print(f"[db] save favorites failed: {e}")
        return jsonify({"error": str(e)[:250]}), 500


# ---------- HISTORY ----------
@app.route("/history", methods=["GET"])
def get_history():
    device_id = (request.args.get("device") or "").strip()
    limit = int(request.args.get("limit", 30))
    if not device_id or not DATABASE_URL:
        return jsonify({"history": []})

    try:
        init_db()
        rows = db_execute(
            "SELECT id, text, voice, speed, created_at FROM history "
            "WHERE device_id = %s ORDER BY created_at DESC LIMIT %s",
            (device_id, limit),
            fetch=True,
        )

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "text": r["text"],
                "voice": r["voice"],
                "speed": r["speed"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            })
        return jsonify({"history": result})
    except Exception as e:
        print(f"[db] get history failed: {e}")
        return jsonify({"history": [], "error": str(e)[:200]})


@app.route("/history", methods=["DELETE", "OPTIONS"])
def delete_history():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data = request.get_json() or {}
        device_id = (data.get("device") or "").strip()

        if not device_id:
            return jsonify({"error": "Missing 'device'"}), 400
        if not DATABASE_URL:
            return jsonify({"status": "no-db"})

        init_db()
        db_execute("DELETE FROM history WHERE device_id = %s", (device_id,))
        return jsonify({"status": "cleared"})
    except Exception as e:
        return jsonify({"error": str(e)[:250]}), 500
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Neon Postgres Tuning")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace the DB section ----------
    # Match from "# DATABASE" to the line before "# UPSTREAM"
    db_pattern = re.compile(
        r'# =+\s*\n# DATABASE[^\n]*\n# =+\n.*?(?=\n# =+\s*\n# UPSTREAM)',
        re.DOTALL
    )

    if db_pattern.search(src):
        src = db_pattern.sub(NEW_DB_SECTION, src, count=1)
        changes.append("DB section (Neon-tuned)")
    else:
        print("  WARN: could not find DB section")

    # ---------- 2) Replace the favorites + history routes ----------
    fav_hist_pattern = re.compile(
        r'# -+ FAVORITES -+.*?(?=\n# =+\s*\n# NO app\.run)',
        re.DOTALL
    )

    if fav_hist_pattern.search(src):
        src = fav_hist_pattern.sub(NEW_ROUTES + "\n\n", src, count=1)
        changes.append("favorites + history routes")

    if src == original:
        print("  No changes made.")
        return

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Neon-specific changes:")
    print("   • SSL enforced (sslmode=require)")
    print("   • channel_binding stripped (psycopg-incompatible)")
    print("   • TCP keepalives enabled (serverless-friendly)")
    print("   • Auto-retry on stale connections")
    print("   • 10s connect timeout")
    print("   • Connection pooler compatible")
    print()
    print(" Deploy:")
    print("   pip install \"psycopg[binary]\"")
    print("   vercel --prod")
    print()
    print(" Verify:")
    print("   curl https://voicekit-prod.vercel.app/health")
    print("   Should show \"db\": true")
    print()
    print(f" Backup: {os.path.relpath(APP, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()