"""
Fix: loadServerHistory is not defined error.
The init call runs before the function definition exists.
This patch wraps the init call to run after the script loads.
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


def patch():
    print("=" * 60)
    print(" VoiceKit — History Fix #2")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Guard the init call with typeof ----------
    old_init = """loadVoices();
loadServerHistory();
setStatus('Ready."""

    new_init = """loadVoices();
if (typeof loadServerHistory === 'function') {
  loadServerHistory();
}
setStatus('Ready."""

    if old_init in src:
        src = src.replace(old_init, new_init, 1)
        changes.append("guarded init call")
    elif 'loadServerHistory();' in src:
        # More general: guard any standalone loadServerHistory() call
        src = re.sub(
            r'^loadServerHistory\(\);$',
            "if (typeof loadServerHistory === 'function') { loadServerHistory(); }",
            src,
            flags=re.MULTILINE
        )
        changes.append("guarded init call (regex)")

    # ---------- 2) Move the history JS block BEFORE the init calls ----------
    # Find the history JS block
    history_block_pattern = re.compile(
        r'// =+\n// SERVER HISTORY\n// =+\n.*?(?=\n// =+\n// KEYBOARD)',
        re.DOTALL
    )

    history_match = history_block_pattern.search(src)

    if history_match:
        block = history_match.group(0)

        # Remove it from its current position
        src = src[:history_match.start()] + src[history_match.end():]

        # Find the init section and insert the block right before it
        init_marker = "// ============================================================\n// INIT"
        if init_marker in src:
            src = src.replace(init_marker, block + "\n" + init_marker, 1)
            changes.append("moved history block before init")
        else:
            # Fallback: insert before the last </script>
            idx = src.rfind('</script>')
            if idx != -1:
                src = src[:idx] + block + "\n" + src[idx:]
                changes.append("moved history block to end")

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied: {', '.join(changes)}")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" What was wrong:")
    print("   The init code called loadServerHistory() BEFORE the")
    print("   function was defined. JavaScript's hoisting only works")
    print("   for `function foo(){}` declarations in the same scope.")
    print()
    print(" The fix:")
    print("   • Guarded the call with typeof check")
    print("   • Moved the SERVER HISTORY block earlier in the script")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()