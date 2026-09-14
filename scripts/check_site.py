#!/usr/bin/env python3
"""Fail-closed checks for the generated GitHub Pages artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SITE_FILES = {".nojekyll", "404.html", "index.html", "story.html"}
TRACKED_ALLOWLIST = {
    ".github/workflows/pages.yml",
    ".gitignore",
    "LICENSE-CODE",
    "LICENSE-CONTENT",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "scripts/build_site.py",
    "scripts/build_comparison.py",
    "scripts/test_comparison.py",
    "scripts/test_comparison_browser.py",
    "src/comparison.css",
    "src/comparison.json",
    "src/provider-logos.json",
    "src/ui-icons.json",
    "scripts/visual_assets.py",
    "scripts/style_story.py",
    "src/story-design.css",
    "src/story-timeline.css",
    "src/story-timeline.js",
    "scripts/story_timeline.py",
    "src/assessment.css",
    "src/assessment.json",
    "scripts/test_assessment.py",
    "scripts/approach_assessment.py",
    "scripts/check_site.py",
    "scripts/test_site_browser.py",
    "scripts/test_story_timeline.py",
    "src/chapter-five.css",
    "src/chapter-five.html",
    "src/chapter-five.js",
    "src/story.html",
}
FORBIDDEN_TRACKED_SUFFIXES = {
    ".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".pyc",
    ".tar", ".gz", ".7z", ".dmg", ".exe",
}
EXPECTED_ACTION_PINS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/configure-pages": "45bfe0192ca1faeb007ade9deae92b16b8254a0d",
    "actions/upload-pages-artifact": "fc324d3547104276b827a68afc52ff2a11cc49c9",
    "actions/deploy-pages": "368f82528645a54fb793d4d04e342629a3f51346",
}
REQUIRED_IDS = {
    "meet", "company", "chapter-two", "chapter-three", "chapter-four", "chapter-five",
    "systems", "hindsight", "mem0", "openviking", "supermemory", "graphrag",
    "failure-cases", "cost", "selection", "final-close",
}
REQUIRED_SOURCE_HOSTS = {
    "hindsight.vectorize.io", "docs.mem0.ai", "docs.openviking.ai",
    "github.com", "supermemory.ai", "microsoft.github.io",
}
FORBIDDEN_TEXT = {
    "four local teaching chapters",
    "real-provider comparison and the final selection exercise are not built",
    "nothing deployed",
    "/applications/brave browser.app",
    "/users/zacariachtatar",
    "/home/hermes",
    "docs/research/source-snapshots",
}
FORBIDDEN_RUNTIME = ("fetch(", "xmlhttprequest", "websocket(", "sendbeacon(", "posthog", "googletagmanager")
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{30,}\b"),
    "OpenAI key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "bearer token": re.compile(r"Bearer\s+[A-Za-z0-9._~-]{24,}", re.I),
}


class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.fragment_links: list[str] = []
        self.external_links: list[tuple[str, str]] = []
        self.subresources: list[tuple[str, str, str]] = []
        self.network_targets: list[tuple[str, str, str]] = []
        self.meta_refreshes: list[str] = []
        self.scripts_without_src = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.append(values["id"])
        href = values.get("href", "")
        if tag == "a" and href.startswith("#"):
            self.fragment_links.append(href[1:])
        if tag == "a" and href.startswith(("http://", "https://")):
            self.external_links.append((href, values.get("rel", "")))
        if tag in {"script", "img", "iframe", "audio", "video", "source"} and values.get("src"):
            self.subresources.append((tag, "src", values["src"]))
        for attribute in ("action", "formaction", "data", "srcset", "poster"):
            if values.get(attribute):
                self.network_targets.append((tag, attribute, values[attribute]))
        if tag == "meta" and values.get("http-equiv", "").lower() == "refresh":
            self.meta_refreshes.append(values.get("content", ""))
        if tag == "link" and values.get("rel") not in {"canonical"}:
            self.subresources.append((tag, "href", href))
        if tag == "script" and not values.get("src"):
            self.scripts_without_src += 1


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_json_script(text: str, element_id: str):
    match = re.search(
        rf'<script id="{re.escape(element_id)}" type="application/json">(.*?)</script>',
        text,
        re.S,
    )
    if not match:
        raise AssertionError(f"Missing JSON script: {element_id}")
    return json.loads(match.group(1))


def check_generated(site: Path) -> dict[str, object]:
    actual_files = {
        str(path.relative_to(site)) for path in site.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    assert actual_files == EXPECTED_SITE_FILES, (actual_files, EXPECTED_SITE_FILES)
    assert not any(path.is_symlink() for path in site.rglob("*")), "Site contains a symlink"

    index = site / "story.html"
    not_found = site / "404.html"
    text = index.read_text(encoding="utf-8")
    lower = text.lower()
    assert text.startswith("<!doctype html>"), "Missing HTML doctype"
    assert "DOCUMENTED, NOT TESTED" in text
    assert "Evidence reviewed 13 September 2026" in text
    assert '<link rel="canonical" href="https://zacaria.github.io/havesome-memory/story.html">' in text

    parser = AuditParser()
    parser.feed(text)
    duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    assert not duplicates, f"Duplicate IDs: {duplicates}"
    missing_ids = sorted(REQUIRED_IDS - set(parser.ids))
    assert not missing_ids, f"Missing required IDs: {missing_ids}"
    missing_fragments = sorted({target for target in parser.fragment_links if target not in parser.ids})
    assert not missing_fragments, f"Broken fragment links: {missing_fragments}"
    from visual_assets import load_assets, raster_data
    story_images = {('img', 'src', raster_data(asset)) for asset in load_assets().values() if asset['format'] == 'png'}
    assert set(parser.subresources) == story_images and len(parser.subresources) == 1, "Unexpected story subresource"
    assert text.count('class="story-provider-site"') == 5
    assert text.count('class="flow-reading-guide"') == 5
    assert 'class="story-site-header"' in text and 'data-icon-library="Lucide"' in text
    assert not parser.network_targets, f"Undeclared network-bearing attributes: {parser.network_targets}"
    assert not parser.meta_refreshes, f"Meta refresh is forbidden: {parser.meta_refreshes}"
    assert parser.scripts_without_src >= 4, "Expected embedded data and application scripts"

    for href, rel in parser.external_links:
        parsed = urlparse(href)
        assert parsed.scheme == "https", f"Non-HTTPS outbound link: {href}"
        assert "noreferrer" in rel.split(), f"External link lacks noreferrer: {href}"
    hosts = {urlparse(href).netloc for href, _ in parser.external_links}
    assert REQUIRED_SOURCE_HOSTS <= hosts, f"Missing primary-source hosts: {REQUIRED_SOURCE_HOSTS - hosts}"

    for phrase in FORBIDDEN_TEXT:
        assert phrase not in lower, f"Forbidden text present: {phrase}"
    for token in FORBIDDEN_RUNTIME:
        assert token not in lower, f"Forbidden runtime integration present: {token}"
    assert "@import" not in lower and "url(http" not in lower, "Remote CSS dependency present"
    for label, pattern in SECRET_PATTERNS.items():
        assert not pattern.search(text), f"Potential {label} present"

    beats = extract_json_script(text, "beats-data")
    corpus = extract_json_script(text, "corpus-data")
    assert len(beats) == 27, f"Expected 27 fictional story beats, got {len(beats)}"
    assert len(corpus) == 11, f"Expected 11 public fictional sources, got {len(corpus)}"
    source_refs = {
        f"{source['id']}#{section['anchor']}"
        for source in corpus for section in source["sections"]
    }
    for beat in beats:
        assert set(beat["refs"]) <= source_refs, (beat["title"], set(beat["refs"]) - source_refs)

    source_drawers = text.count('class="source-drawer"')
    assert source_drawers == 5, f"Expected one source drawer per technology, got {source_drawers}"
    assert text.count('class="morrow-test"') == 5, "Each technology needs a Morrow Works test"
    assert text.count("<textarea") == 10, "Selection exercise is incomplete"

    homepage = (site / "index.html").read_text(encoding="utf-8")
    home_parser = AuditParser()
    home_parser.feed(homepage)
    assert len(home_parser.ids) == len(set(home_parser.ids)), "Duplicate comparison IDs"
    assert all(fragment in home_parser.ids for fragment in home_parser.fragment_links), "Broken homepage fragment"
    from visual_assets import load_assets, raster_data
    logos = load_assets()
    assert set(logos) == {'hindsight','mem0','supermemory','byterover'}
    allowed_images = {('img','src',raster_data(asset)) for asset in logos.values() if asset['format'] == 'png'}
    assert set(home_parser.subresources) == allowed_images and len(home_parser.subresources) == 3
    assert not home_parser.network_targets and not home_parser.meta_refreshes
    assert homepage.count('class="identity-badge ') == 35
    assert homepage.count('class="identity-badge provider-logo ') == 12
    for ident, asset in logos.items():
        assert all(asset.get(field) for field in ('source_url','source_sha256','license_url','license_notice','modifications'))
        assert asset['source_url'].startswith('https://raw.githubusercontent.com/')
        assert 'id="credit-'+ident+'"' in homepage
    assert all(urlparse(href).scheme == "https" and "noreferrer" in rel.split() for href, rel in home_parser.external_links)
    assert '<link rel="canonical" href="https://zacaria.github.io/havesome-memory/">' in homepage
    assert '<h1 id="memory-title">You told your AI yesterday. Will it know today?</h1>' in homepage
    assert 'Evidence reviewed 14 September 2026' in homepage
    assert 'href="story.html"' in homepage and 'story.html'+chr(39)+'+location.hash' in homepage
    catalogue = json.loads((ROOT / 'src/comparison.json').read_text())
    provider_ids = {item['id'] for item in catalogue['approaches'] if item['kind'] == 'provider'}
    assert provider_ids == {'hindsight','honcho','mem0','openviking','supermemory','byterover','retaindb','holographic','memori'}
    assert len(catalogue['approaches']) == 13
    assert homepage.count('<tr data-kind="provider"') == 9 and homepage.count('<tr data-kind="basic"') == 4
    for item in catalogue['approaches']:
        assert 'provider-' + item['id'] in home_parser.ids
        assert item['sources'] and item['evidence_gap'] and len(item['flow']) == 3
        for claim in item['claims']:
            assert all(claim[k] for k in ('benchmark','metric','value','conditions','url','publisher','quote'))
    for phrase in FORBIDDEN_TEXT | set(FORBIDDEN_RUNTIME):
        assert phrase not in homepage.lower(), ('Forbidden comparison content', phrase)
    for label, pattern in SECRET_PATTERNS.items():
        assert not pattern.search(homepage), f'Potential {label} in comparison'

    nf = not_found.read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex">' in nf
    assert '<a href="https://zacaria.github.io/havesome-memory/">Return to Havesome Memory →</a>' in nf
    assert "javascript" not in nf.lower()

    return {
        "status": "pass",
        "site_files": sorted(actual_files),
        "story_bytes": index.stat().st_size,
        "index_bytes": (site / "index.html").stat().st_size,
        "story_sha256": sha(index),
        "index_sha256": sha(site / "index.html"),
        "comparison_approaches": len(catalogue["approaches"]),
        "hermes_providers": len(provider_ids),
        "story_beats": len(beats),
        "fictional_sources": len(corpus),
        "technologies": 5,
        "source_drawers": source_drawers,
        "outbound_source_hosts": sorted(hosts | {urlparse(href).netloc for href, _ in home_parser.external_links}),
        "external_subresources": 0,
    }


def check_determinism(site: Path) -> None:
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        command = ["python3", str(ROOT / "scripts" / "build_site.py"), "--output"]
        subprocess.run(command + [first], check=True, cwd=ROOT, capture_output=True, text=True)
        subprocess.run(command + [second], check=True, cwd=ROOT, capture_output=True, text=True)
        for name in EXPECTED_SITE_FILES:
            assert sha(Path(first) / name) == sha(Path(second) / name), f"Non-deterministic output: {name}"
        assert sha(Path(first) / "index.html") == sha(site / "index.html"), "Checked site differs from clean build"


def run_negative_controls(site: Path) -> list[str]:
    parser = AuditParser()
    parser.feed(
        '<form action="https://example.invalid"><button formaction="/send">x</button>'
        '<object data="/payload"><source srcset="/image.png"><video poster="/poster.png">'
        '<meta http-equiv="refresh" content="0;url=/elsewhere">'
    )
    assert len(parser.network_targets) == 5
    assert parser.meta_refreshes == ["0;url=/elsewhere"]

    forbidden_candidates = {
        "src/extra.png",
        "src/source-snapshot.txt",
        ".github/workflows/unreviewed.yml",
        "artifacts/evidence.zip",
        "credentials.env",
    }
    assert not (TRACKED_ALLOWLIST & forbidden_candidates)

    with tempfile.TemporaryDirectory() as directory:
        tampered = Path(directory) / "site"
        shutil.copytree(site, tampered)
        tampered.chmod(0o700)
        (tampered / "evidence.zip").write_bytes(b"not a deploy artifact")
        try:
            check_generated(tampered)
        except AssertionError:
            pass
        else:
            raise AssertionError("Tampered deploy artifact passed verification")
    return ["network_attributes", "tracked_allowlist", "post-check_artifact_injection"]


def check_tracked_tree(worktree: bool = False) -> None:
    result = subprocess.run(
        ["git", "ls-files"] + (["--cached", "--others", "--exclude-standard"] if worktree else []), cwd=ROOT, check=True, capture_output=True, text=True
    )
    tracked = {line for line in result.stdout.splitlines() if line}
    if not tracked:
        return
    assert tracked == TRACKED_ALLOWLIST, {
        "unexpected": sorted(tracked - TRACKED_ALLOWLIST),
        "missing": sorted(TRACKED_ALLOWLIST - tracked),
    }
    credential_name = re.compile(r"(^|/)(\.env|credentials?|secrets?|tokens?)(\.|$)", re.I)
    staged_blobs: dict[str, str] = {}
    for relative in sorted(tracked):
        path = ROOT / relative
        assert path.is_file() and not path.is_symlink(), f"Tracked path is not a regular file: {relative}"
        assert path.suffix.lower() not in FORBIDDEN_TRACKED_SUFFIXES, f"Forbidden tracked type: {relative}"
        assert not credential_name.search(relative), f"Credential-like tracked filename: {relative}"
        payload = path.read_bytes() if worktree else subprocess.run(
            ["git", "show", f":{relative}"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        assert b"\0" not in payload, f"Binary tracked blob: {relative}"
        assert len(payload) < 1_000_000, f"Unexpectedly large tracked blob: {relative}"
        decoded = payload.decode("utf-8")
        staged_blobs[relative] = decoded
        lowered = decoded.lower()
        if relative != "scripts/check_site.py":
            forbidden_snapshot_path = "docs/research/" + "source-snapshots"
            assert forbidden_snapshot_path not in lowered, f"Snapshot path leaked in {relative}"
        for label, pattern in SECRET_PATTERNS.items():
            assert not pattern.search(decoded), f"Potential {label} in tracked file {relative}"

    workflow = staged_blobs[".github/workflows/pages.yml"]
    uses = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.M)
    expected_uses = {f"{action}@{sha}" for action, sha in EXPECTED_ACTION_PINS.items()}
    assert set(uses) == expected_uses and len(uses) == len(expected_uses), {
        "invalid_action_references": sorted(set(uses) - expected_uses),
        "missing_action_references": sorted(expected_uses - set(uses)),
    }
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) for value in uses)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    parser.add_argument("--skip-determinism", action="store_true")
    parser.add_argument("--worktree", action="store_true", help="Audit explicit local source closure before staging; CI audits the Git index")
    args = parser.parse_args()
    report = check_generated(args.site.resolve())
    if not args.skip_determinism:
        check_determinism(args.site.resolve())
        report["deterministic_build"] = True
    check_tracked_tree(args.worktree)
    report["negative_controls_rejected"] = run_negative_controls(args.site.resolve())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
