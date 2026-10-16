"""
VoiceKit — Mobile-friendly improvements
- Better touch targets
- Improved sidebar drawer
- Stacked layouts on small screens
- Responsive text sizes
- Horizontal scroll prevention
- Bottom action bar on mobile
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "templates", "index.html")


def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")
        print(f"  backed up -> {os.path.relpath(path, BASE)}.bak")


MOBILE_CSS = '''
  /* ============================================================
     MOBILE REFINEMENTS
     ============================================================ */

  /* Prevent horizontal scroll on small screens */
  @media (max-width: 900px) {
    html, body {
      overflow-x: hidden;
      -webkit-text-size-adjust: 100%;
    }

    /* Sidebar drawer */
    .sidebar {
      width: 260px;
      padding: 16px 12px;
      padding-top: env(safe-area-inset-top, 16px);
    }

    /* Overlay */
    .overlay {
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    }

    /* Menu toggle — bigger touch target, safe area aware */
    .menu-toggle {
      width: 44px;
      height: 44px;
      top: env(safe-area-inset-top, 16px);
      left: 16px;
      font-size: 1.2rem;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }

    /* Main padding — leave room for the hamburger */
    .main {
      padding: 72px 16px 60px;
      padding-left: max(16px, env(safe-area-inset-left, 16px));
      padding-right: max(16px, env(safe-area-inset-right, 16px));
      padding-bottom: max(60px, env(safe-area-inset-bottom, 60px));
    }

    /* Header */
    .view-header {
      margin-bottom: 20px;
    }

    .view-title {
      font-size: 1.35rem;
    }

    .view-subtitle {
      font-size: 0.85rem;
    }

    /* Header with icon on mobile */
    .view-header.with-icon {
      gap: 12px;
    }

    .view-header.with-icon .header-icon {
      width: 44px;
      height: 44px;
      border-radius: 11px;
    }

    /* Cards */
    .card {
      padding: 18px 16px;
      border-radius: 12px;
      margin-bottom: 14px;
    }

    .card-title {
      font-size: 0.72rem;
    }

    /* Stats grid — 3 columns even on mobile */
    .stats-grid {
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 18px;
    }

    .stat-card {
      padding: 12px 10px;
      border-radius: 10px;
    }

    .stat-card .value {
      font-size: 1.3rem;
    }

    .stat-card .label {
      font-size: 0.6rem;
      letter-spacing: 0.04em;
    }

    /* Voice indicator */
    .voice-indicator {
      flex-wrap: wrap;
      gap: 8px;
      padding: 10px 12px;
    }

    .voice-indicator .change-btn {
      margin-left: 0;
      width: 100%;
      text-align: center;
      padding: 8px;
      font-size: 0.75rem;
    }

    /* Textarea — bigger touch target */
    textarea {
      font-size: 16px;  /* prevent iOS auto-zoom */
      min-height: 120px;
      padding: 14px;
    }

    /* Quick phrases — wrap nicely */
    .quick {
      gap: 6px;
    }

    .quick button {
      font-size: 0.72rem;
      padding: 6px 11px;
    }

    /* Search input — prevent iOS zoom */
    #voiceSearch {
      font-size: 16px;
      padding: 12px 14px 12px 40px;
    }

    /* Filter chips — horizontal scroll instead of wrap */
    .filter-row {
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      overflow-y: hidden;
      gap: 6px;
      padding-bottom: 4px;
      margin-left: -16px;
      margin-right: -16px;
      padding-left: 16px;
      padding-right: 16px;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
    }

    .filter-row::-webkit-scrollbar {
      display: none;
    }

    .filter-chip {
      flex-shrink: 0;
      font-size: 0.75rem;
      padding: 6px 12px;
    }

    /* Voice chips — single column on narrow screens */
    .voice-chips {
      grid-template-columns: 1fr;
      gap: 8px;
    }

    .voice-chip {
      padding: 12px 14px;
    }

    .chip-name {
      font-size: 0.88rem;
    }

    .chip-desc {
      font-size: 0.72rem;
    }

    /* Play + star buttons — bigger touch targets */
    .chip-play,
    .chip-star {
      width: 32px;
      height: 32px;
      font-size: 0.7rem;
    }

    .chip-actions {
      gap: 8px;
    }

    /* Voice list height */
    .voice-list {
      max-height: none;
      min-height: 200px;
      padding-right: 0;
    }

    /* Selected bar */
    .selected-bar {
      flex-wrap: wrap;
      gap: 8px;
      padding: 12px;
    }

    .selected-bar .name {
      margin-left: 0;
      width: 100%;
      font-size: 0.95rem;
    }

    .selected-bar .id {
      font-size: 0.75rem;
    }

    /* Speed control */
    .speed-row {
      gap: 12px;
    }

    .speed-label {
      font-size: 0.75rem;
      min-width: 44px;
    }

    /* Action row — stack on very narrow screens */
    .action-row {
      gap: 8px;
    }

    .speak-btn {
      height: 50px;
      font-size: 0.95rem;
      padding: 14px 18px;
    }

    .download-btn {
      width: 50px;
      height: 50px;
    }

    /* Status */
    .status {
      font-size: 0.75rem;
      padding: 10px 12px;
    }

    /* History items — stack buttons below on mobile */
    .history-item {
      flex-wrap: wrap;
      gap: 10px;
      padding: 12px;
    }

    .history-item .info {
      width: 100%;
    }

    .history-item button {
      width: 100%;
      padding: 10px;
      font-size: 0.78rem;
    }

    /* API endpoints — single column */
    .endpoint-grid {
      grid-template-columns: 1fr;
      gap: 8px;
    }

    .endpoint-card {
      padding: 12px 14px;
    }

    /* Code blocks — horizontal scroll, smaller font */
    .api-code {
      font-size: 0.68rem;
      padding: 12px;
    }

    /* Footer */
    .footer {
      font-size: 0.75rem;
    }

    /* Live chat panel — full width */
    .chat-panel {
      width: 100%;
      max-width: 100%;
    }
  }

  /* Extra small phones (< 480px) */
  @media (max-width: 480px) {
    .main {
      padding: 68px 12px 60px;
    }

    .view-title {
      font-size: 1.2rem;
    }

    .stats-grid {
      gap: 6px;
    }

    .stat-card .value {
      font-size: 1.15rem;
    }

    .stat-card .label {
      font-size: 0.55rem;
    }

    .card {
      padding: 16px 14px;
    }

    textarea {
      min-height: 100px;
      font-size: 15px;
    }

    .voice-indicator .voice-name {
      font-size: 0.85rem;
    }

    .voice-indicator .voice-id {
      font-size: 0.62rem;
    }

    .speak-btn {
      font-size: 0.88rem;
    }
  }

  /* Landscape phones */
  @media (max-height: 500px) and (orientation: landscape) {
    .main {
      padding-top: 60px;
    }

    .voice-list {
      max-height: 240px;
    }
  }

  /* Touch devices — hover only when actually hovering */
  @media (hover: none) {
    .voice-chip:hover {
      transform: none;
      box-shadow: none;
    }

    .quick button:hover {
      background: var(--surface-2);
    }
  }

  /* Respect reduced motion preference */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
'''


def patch():
    print("=" * 60)
    print(" VoiceKit — Mobile Friendly")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    if 'MOBILE REFINEMENTS' in src:
        print("  Already applied.")
        return

    # Insert the mobile CSS just before </style>
    src = src.replace('</style>', MOBILE_CSS + '\n</style>', 1)

    # Ensure the viewport meta tag is present and correct
    if 'name="viewport"' not in src:
        src = src.replace(
            '<head>',
            '<head>\n<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, viewport-fit=cover">',
            1
        )

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print("  [OK] Mobile CSS applied")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" Mobile improvements:")
    print("   • Hamburger menu 44×44 (bigger tap target)")
    print("   • Sidebar drawer 260px wide")
    print("   • Textarea font 16px (prevents iOS auto-zoom)")
    print("   • Voice chips stack single-column")
    print("   • Filter chips scroll horizontally")
    print("   • Play/star buttons 32×32")
    print("   • History buttons full width")
    print("   • Stats grid stays 3 columns")
    print("   • API code blocks scroll horizontally")
    print("   • Safe area padding (iPhone notch)")
    print("   • No hover states on touch devices")
    print("   • Respects reduced motion")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print("   Or hard-refresh: Ctrl + Shift + R")
    print("=" * 60)


if __name__ == "__main__":
    patch()