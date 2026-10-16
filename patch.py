"""
VoiceKit — Speak Button Redesign
Replaces the full-width white button with a clean, compact action row.
- Round play icon on the left
- "Generate" text in the middle
- Subtle, not shouting
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


NEW_CSS = '''
  /* ---------- ACTION ROW ---------- */
  .action-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 18px;
  }

  .speak-btn {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 13px 20px;
    background: var(--bg-input);
    border: 1px solid var(--border-hi);
    border-radius: var(--radius-md);
    color: var(--text);
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    cursor: pointer;
    transition: all 0.15s var(--ease);
    height: 46px;
  }

  .speak-btn:hover:not(:disabled) {
    background: var(--bg-hover);
    border-color: rgba(255, 255, 255, 0.22);
  }

  .speak-btn:active:not(:disabled) {
    transform: scale(0.99);
  }

  .speak-btn:disabled {
    opacity: 0.5;
    cursor: wait;
  }

  .speak-btn .play-icon {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .speak-btn .play-icon svg {
    width: 100%;
    height: 100%;
    fill: currentColor;
  }

  .speak-btn.primary {
    background: #ffffff;
    color: #0a0a0a;
    border-color: #ffffff;
  }

  .speak-btn.primary:hover:not(:disabled) {
    background: #e8e8e8;
    border-color: #e8e8e8;
  }

  .speak-btn.primary:disabled {
    background: #ffffff;
    color: #0a0a0a;
    opacity: 0.7;
  }

  /* Download button (icon-only) */
  .download-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 46px;
    height: 46px;
    background: var(--bg-input);
    border: 1px solid var(--border-hi);
    border-radius: var(--radius-md);
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.15s var(--ease);
    flex-shrink: 0;
  }

  .download-btn:hover:not(:disabled) {
    background: var(--bg-hover);
    color: var(--text);
    border-color: rgba(255, 255, 255, 0.22);
  }

  .download-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .download-btn svg {
    width: 16px;
    height: 16px;
  }

  /* Spinner inside button */
  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(10, 10, 10, 0.2);
    border-top-color: #0a0a0a;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Audio player */
  audio {
    width: 100%;
    margin-top: 12px;
    display: none;
    border-radius: var(--radius-sm);
    filter: invert(0.9) hue-rotate(180deg);
  }

  audio.show { display: block; }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Speak Button Redesign")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- 1) Replace the old speak-btn CSS ----------
    # Find the old block from ".speak-btn {" to end of "}" for it
    # Since there are several .speak-btn rules, remove them all and add new CSS.

    # Simplest approach: inject the new CSS right before </style>
    if '/* ---------- ACTION ROW ---------- */' not in src:
        src = src.replace('</style>', NEW_CSS + '\n</style>', 1)
        changes.append("action row CSS")

    # ---------- 2) Replace the speak button HTML ----------
    old_btn_pattern = '<button class="speak-btn" id="speakBtn">'

    if old_btn_pattern in src and 'action-row' not in src:
        # Find the full button block
        start = src.find(old_btn_pattern)
        if start != -1:
            # Find the closing </button>
            end = src.find('</button>', start)
            if end != -1:
                end += len('</button>')

                new_btn_html = '''<div class="action-row">
        <button class="speak-btn primary" id="speakBtn">
          <span class="play-icon" id="speakIcon">
            <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          </span>
          <span id="speakBtnContent">Generate</span>
        </button>
        <button class="download-btn" id="downloadBtn" title="Download WAV" disabled>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </button>
      </div>'''

                src = src[:start] + new_btn_html + src[end:]
                changes.append("button HTML")

    # ---------- 3) Update the JS ----------
    # Update speak() to use the new button content id
    old_content = "speakBtnContent.innerHTML = '<span class=\"spinner\"></span> Generating...';"
    new_content = '''speakBtnContent.textContent = 'Generating...';
    document.getElementById('speakIcon').innerHTML = '<div class="spinner"></div>';'''

    if old_content in src:
        src = src.replace(old_content, new_content)
        changes.append("loading state")

    old_reset = "speakBtnContent.textContent = '🔊 Speak';"
    new_reset = '''speakBtnContent.textContent = 'Generate';
    document.getElementById('speakIcon').innerHTML = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';'''

    if old_reset in src:
        src = src.replace(old_reset, new_reset)
        changes.append("reset state")

    # ---------- 4) Enable download button after generation ----------
    # Insert after the "player.classList.add('show');"
    download_wire = '''
    // Enable download button
    const dlBtn = document.getElementById('downloadBtn');
    if (dlBtn) {
      dlBtn.disabled = false;
      dlBtn.onclick = () => {
        const a = document.createElement('a');
        a.href = url;
        a.download = `voicekit_${Date.now()}.wav`;
        a.click();
      };
    }
'''
    marker = "player.classList.add('show');"
    if marker in src and 'dlBtn.onclick' not in src:
        # Insert after the first occurrence
        idx = src.find(marker)
        if idx != -1:
            insert_at = idx + len(marker)
            src = src[:insert_at] + download_wire + src[insert_at:]
            changes.append("download wiring")

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
    print(" What changed:")
    print("   • Speak button: solid white, 'Generate' label, play icon")
    print("   • No shimmer, no glow, no gradient")
    print("   • Hover: subtle grey shift")
    print("   • Download button (icon-only) appears next to it")
    print("   • Disabled until audio is generated")
    print("   • Loading spinner replaces the play icon")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()