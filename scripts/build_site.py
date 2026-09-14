#!/usr/bin/env python3
"""Build the public, self-contained Havesome Memory site."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "src" / "story.html"
STORY_SHA256 = "ee3ed7550bbaaa0e7c68d9c8d257c051dc268ac32ad40dd95967d5e11897c012"


def replace_once(page: str, old: str, new: str, label: str) -> str:
    count = page.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label}; found {count}")
    return page.replace(old, new, 1)


def build(output: Path) -> Path:
    raw = STORY.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != STORY_SHA256:
        raise RuntimeError(f"Pinned four-chapter story drifted: {actual}")

    page = raw.decode("utf-8")
    chapter = (ROOT / "src" / "chapter-five.html").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "chapter-five.css").read_text(encoding="utf-8")
    script = (ROOT / "src" / "chapter-five.js").read_text(encoding="utf-8")

    old_title = "<title>Memory Engineering · Trust and control</title>"
    metadata = """<title>Memory Engineering · Why AI needs more than retrieval</title><meta name=\"description\" content=\"A source-backed, scrollable story about why memory engineering matters and how Hindsight, Mem0, OpenViking, Supermemory, and GraphRAG divide the work.\"><link rel=\"canonical\" href=\"https://zacaria.github.io risetime havesome-memory/\"><meta property=\"og:type\" content=\"website\"><meta property=\"og:title\" content=\"Memory Engineering · Why AI needs more than retrieval\"><meta property=\"og:description\" content=\"Follow one fictional company from scattered files to scoped, inspectable memory—then compare five current technical approaches.\"><meta property=\"og:url\" content=\"https://zacaria.github.io/havesome-memory/\"><meta name=\"twitter:card\" content=\"summary\">""".replace(" risetime ", "/")
    page = replace_once(page, old_title, metadata, "document title")
    page = replace_once(page, "</style></head>", styles + "</style></head>", "style close")

    header = '<header><span class="mark" aria-hidden="true">▰</span> MEMORY ENGINEERING <span class="chapter-name">THE BEGINNING</span></header>'
    nav = header + """<nav class=\"site-index\" aria-label=\"Chapter index\"><a href=\"#meet\">Story</a><a href=\"#chapter-two\">Explore</a><a href=\"#chapter-three\">Change</a><a href=\"#chapter-four\">Control</a><a href=\"#chapter-five\">Systems</a></nav>"""
    page = replace_once(page, header, nav, "site header")

    old_close = '<section id="closing" class="prologue closing"><div><p class="eyebrow">END OF CHAPTER FOUR</p><h2>Ask where the responsibility lives.</h2><p>Who enforces access? Who chooses context? Who checks the answer? Who follows a correction or deletion through the copies?</p><p>These are now concrete questions to take to a system—not checkmarks to accept on a feature page.</p><p>Next: compare what a simple setup, a memory product and an application actually take responsibility for, and what evidence would justify a choice.</p><p class="boundary">Four local teaching chapters. Real-provider comparison and the final selection exercise are not built here yet. No provider connected; nothing deployed.</p></div></section>'
    bridge = '<section id="closing" class="prologue closing"><div><p class="eyebrow">END OF THE MORROW WORKS STORY</p><h2>Ask where the responsibility lives.</h2><p>Who keeps the source? Who chooses the representation? Who enforces access? Who selects context? Who checks the answer? Who follows correction and forgetting through every derived copy?</p><p>The fictional story has turned those abstractions into concrete failure cases. Now compare how real systems divide the work.</p><a class="scroll-cue" href="#chapter-five">Continue to current technologies <span aria-hidden="true">↓</span></a></div></section>'
    page = replace_once(page, old_close, bridge, "chapter-four closing")

    old_footer = '<footer><p>No prior reading is required. <strong>havesome-context</strong> is a planned, optional companion about what an AI sees for a task—not a prerequisite or an available course.</p>'
    new_footer = '<footer><p>This public guide requires no account and sends no data. <strong>havesome-context</strong> is a planned optional companion about what an AI sees for a task—not a prerequisite.</p>'
    page = replace_once(page, old_footer, chapter + new_footer, "public chapter insertion")

    page = replace_once(page, "</body></html>", f"<script>{script}</script></body></html>", "body close")

    forbidden_copy = [
        "Four local teaching chapters",
        "Real-provider comparison and the final selection exercise are not built",
        "nothing deployed",
    ]
    for phrase in forbidden_copy:
        if phrase.lower() in page.lower():
            raise RuntimeError(f"Obsolete production copy remains: {phrase}")

    output.mkdir(parents=True, exist_ok=True)
    index = output / "index.html"
    (output / "story.html").write_text(
        page.replace('href="https://zacaria.github.io/havesome-memory/"', 'href="https://zacaria.github.io/havesome-memory/story.html"')
            .replace('content="https://zacaria.github.io/havesome-memory/"', 'content="https://zacaria.github.io/havesome-memory/story.html"')
            .replace('<nav class="site-index" aria-label="Chapter index">', '<nav class="site-index" aria-label="Chapter index"><a href="index.html">Compare</a>'),
        encoding="utf-8",
    )
    from build_comparison import render
    index.write_text(render(), encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "404.html").write_text(
        """<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta name=\"robots\" content=\"noindex\"><link rel=\"canonical\" href=\"https://zacaria.github.io/havesome-memory/\"><title>Page not found · Memory Engineering</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;min-height:100svh;display:grid;place-items:center;padding:8vw;background:#0a1930;color:#edf1fa;font:18px/1.6 Arial,sans-serif}main{max-width:760px;border-top:1px solid #ffaf83;padding-top:28px}p:first-child{color:#ffaf83;font-size:12px;letter-spacing:.12em}h1{font-size:clamp(44px,9vw,94px);line-height:.95;letter-spacing:-.055em;font-weight:500}a{color:#ffaf83;text-underline-offset:4px}</style></head><body><main><p>404 / OUTSIDE THE COLLECTION</p><h1>This page was not retained.</h1><p>The Memory Engineering story still starts in one place.</p><p><a href=\"https://zacaria.github.io/havesome-memory/\">Return to Havesome Memory →</a></p></main></body></html>""",
        encoding="utf-8",
    )
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    index = build(args.output.resolve())
    print(f"Built {index} ({index.stat().st_size} bytes, sha256={hashlib.sha256(index.read_bytes()).hexdigest()})")


if __name__ == "__main__":
    main()
