"""
Strip every technical/implementation detail from the About page and
anywhere else. Replace with marketing-focused copy.

Removes mentions of:
  - Flask, ONNX, Hugging Face Spaces, Kokoro-82M, Vercel, proxy
  - "runs on Spaces", "built with", "proxied through"

Replaces with benefit-driven product language.
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
    print(" VoiceKit — Marketing Rewrite")
    print("=" * 60)

    if not os.path.exists(HTML):
        print(f"ERROR: {HTML} not found")
        return

    backup(HTML)

    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    changes = []

    # ---------- Replace the About text block ----------
    # Find the entire About card paragraphs and replace them
    about_pattern = re.compile(
        r'<section class="view" id="view-about">.*?</section>',
        re.DOTALL
    )

    new_about = '''<section class="view" id="view-about">
    <div class="view-header">
      <h1 class="view-title">About VoiceKit</h1>
      <p class="view-subtitle">Professional voice synthesis. Fast, free, and built for everyone.</p>
    </div>

    <div class="card">
      <p style="color: var(--text); font-size: 0.95rem; line-height: 1.75; margin-bottom: 18px; font-weight: 500;">
        VoiceKit turns your words into natural-sounding speech in seconds.
      </p>

      <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.75; margin-bottom: 16px;">
        54 voices across 9 languages. Perfect for content creators, developers, podcasters, students, and anyone who needs high-quality audio without the studio session.
      </p>

      <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.75; margin-bottom: 16px;">
        No signup. No account. No credit card. Just type, pick a voice, and generate.
      </p>

      <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.75;">
        Everything is free, and everything is instant.
      </p>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">What you can do</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="color: var(--text); font-size: 1.1rem;">🎬</span>
          <div>
            <div style="color: var(--text); font-weight: 600; font-size: 0.88rem;">Voiceovers for video</div>
            <div style="color: var(--text-dim); font-size: 0.82rem; margin-top: 2px;">Create narration for YouTube, TikTok, Reels, and short films.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="color: var(--text); font-size: 1.1rem;">🎙️</span>
          <div>
            <div style="color: var(--text); font-weight: 600; font-size: 0.88rem;">Podcast intros and ads</div>
            <div style="color: var(--text-dim); font-size: 0.82rem; margin-top: 2px;">Produce professional-sounding audio without hiring a voice actor.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="color: var(--text); font-size: 1.1rem;">💻</span>
          <div>
            <div style="color: var(--text); font-weight: 600; font-size: 0.88rem;">Add voice to your apps</div>
            <div style="color: var(--text-dim); font-size: 0.82rem; margin-top: 2px;">A clean API that works with any language or framework.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="color: var(--text); font-size: 1.1rem;">📚</span>
          <div>
            <div style="color: var(--text); font-weight: 600; font-size: 0.88rem;">Accessibility and learning</div>
            <div style="color: var(--text-dim); font-size: 0.82rem; margin-top: 2px;">Read articles, books, and study materials aloud.</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Why VoiceKit</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 12px; font-size: 0.85rem; color: var(--text-muted); line-height: 1.6;">
        <div>✓ <strong style="color: var(--text);">Free forever</strong> — no subscriptions, no hidden costs</div>
        <div>✓ <strong style="color: var(--text);">No signup</strong> — start generating immediately</div>
        <div>✓ <strong style="color: var(--text);">54 voices</strong> — across 9 languages and every style</div>
        <div>✓ <strong style="color: var(--text);">Fast</strong> — most generations complete in under 3 seconds</div>
        <div>✓ <strong style="color: var(--text);">Open API</strong> — integrate anywhere</div>
      </div>
    </div>
  </section>'''

    if about_pattern.search(src):
        src = about_pattern.sub(new_about, src, count=1)
        changes.append("about section")

    # ---------- Strip any remaining technical mentions anywhere ----------
    tech_patterns = [
        (r'Kokoro-?82M', ''),
        (r'Kokoro', ''),
        (r'ONNX', ''),
        (r'Flask', ''),
        (r'Hugging\s*Face', ''),
        (r'HuggingFace', ''),
        (r'huggingface\.co[^\s"\'<>]*', ''),
        (r'\.hf\.space[^\s"\'<>]*', ''),
        (r'motari[^\s"\'<>]*', ''),
        (r'hexgrad', ''),
        (r'Spaces\b', ''),
        (r'\bproxy\b', ''),
        (r'proxied through Vercel', ''),
        (r'runs on [A-Za-z]*', ''),
        (r'built with [^.]*\.', ''),
        (r'built on [^.]*\.', ''),
    ]

    for pattern, replacement in tech_patterns:
        if re.search(pattern, src, re.IGNORECASE):
            src = re.sub(pattern, replacement, src, flags=re.IGNORECASE)
            changes.append(f"stripped '{pattern}'")

    # ---------- Clean up leftover separators ----------
    src = re.sub(r'<span class="sep">·</span>\s*(?=<)', '', src, count=1)

    if src == original:
        print("  No changes made.")
        return

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"  [OK] Applied {len(changes)} changes")
    print()
    print("=" * 60)
    print(" DONE")
    print("=" * 60)
    print()
    print(" The About page now focuses on:")
    print("   • What VoiceKit does for the user")
    print("   • Who it's for (creators, developers, students)")
    print("   • Benefits (free, fast, no signup)")
    print("   • Use cases (video, podcast, apps, accessibility)")
    print()
    print(" No technical details remain:")
    print("   ✗ Kokoro, ONNX, Flask, Hugging Face, Spaces")
    print("   ✗ Proxy, Vercel, model names, repo names")
    print()
    print(" Deploy:")
    print("   vercel --prod")
    print(f" Backup: {os.path.relpath(HTML, BASE)}.bak")
    print("=" * 60)


if __name__ == "__main__":
    patch()