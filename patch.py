"""
Fix: the ALTER TABLE migration was inserted as a Python comment
inside the SQL triple-quoted string. Postgres tried to parse the
comment as SQL and failed, so init_db() crashes every time.

This patch moves the migration to proper Python code OUTSIDE the SQL string.
"""

import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, "app.py")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


# ============================================================
# Clean init_db — migration OUTSIDE the SQL string
# ============================================================
NEW_INIT_DB = '''def init_db():
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
                    # ---------- favorites ----------
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS favorites (
                            device_id  TEXT NOT NULL,
                            voice_id   TEXT NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            PRIMARY KEY (device_id, voice_id)
                        );
                    """)

                    # ---------- history ----------
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS history (
                            id         SERIAL PRIMARY KEY,
                            device_id  TEXT NOT NULL,
                            text       TEXT NOT NULL,
                            voice      TEXT NOT NULL,
                            speed      REAL NOT NULL,
                            audio_url  TEXT,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        );
                    """)

                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_history_device
                        ON history (device_id, created_at DESC);
                    """)

                    # ---------- migration: add audio_url if missing ----------
                    # Safe for existing databases created before this column existed.
                    cur.execute("""
                        ALTER TABLE history
                        ADD COLUMN IF NOT EXISTS audio_url TEXT;
                    """)

                conn.commit()
            print("[db] Tables ready")
        except Exception as e:
            print(f"[db] init failed: {e}")
        finally:
            _db_initialized = True
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Migration Fix")
    print("=" * 60)

    if not os.path.exists(APP):
        print(f"ERROR: {APP} not found")
        return

    backup(APP)

    with open(APP, "r", encoding="utf-8") as f:
        src = f.read()

    original = src

    # Match the entire init_db function
    pattern = re.compile(
        r'def init_db\(\):.*?(?=\n\ndef |\n\n# =|\Z)',
        re.DOTALL
    )

    match = pattern.search(src)
    if not match:
        print("  ERROR: could not find init_db() function")
        return

    src = src[:match.start()] + NEW_INIT_DB + src[match.end():]

    # Also clean any leftover broken comment lines
    src = re.sub(
        r'^\s*#\s*Add column if it doesn\'t exist.*$',
        '',
        src,
        flags=re.MULTILINE
    )

    if src == original:
        print("  No changes made.")
        return

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] init_db() rewritten — migration is now proper Python")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" What was wrong:")
    print("   The ALTER TABLE migration was pasted INSIDE the triple-quoted")
    print("   SQL string as a Python comment (# Add column...). Postgres")
    print("   tried to parse the comment as SQL and crashed.")
    print()
    print(" The fix:")
    print("   init_db() now uses a proper Python-level `cur.execute()`")
    print("   for the ALTER TABLE migration, outside any SQL string.")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print()
    print(" After deploy, the first /history or /speak request will:")
    print("   1. Create the tables (if missing)")
    print("   2. Add the audio_url column (if missing)")
    print("   3. Print '[db] Tables ready' to the logs")
    print()
    print("=" * 60)


if __name__ == "__main__":
    patch()