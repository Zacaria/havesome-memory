#!/usr/bin/env python3
"""Exercise the generated site in a real browser."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [(1440, 900), (1280, 720), (768, 1024), (390, 844), (320, 640)]
SYSTEM_IDS = ["hindsight", "mem0", "openviking", "supermemory", "graphrag"]


@contextmanager
def serve_site(site: Path):
    """Serve the Pages artifact under its real project subpath."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            path = urlsplit(self.path).path
            if path in {"/havesome-memory", "/havesome-memory/", "/havesome-memory/index.html"}:
                payload = (site / "index.html").read_bytes()
                status = 200
            else:
                payload = (site / "404.html").read_bytes()
                status = 404
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            del format, args
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/havesome-memory/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    local_browser = "/usr/bin/chromium" if Path("/usr/bin/chromium").exists() else ""
    parser.add_argument("--browser", default=os.environ.get("BROWSER_EXECUTABLE", local_browser))
    parser.add_argument("--screenshots", type=Path, default=ROOT / "_verification")
    args = parser.parse_args()
    file = args.site.resolve() / "index.html"
    assert file.exists(), "Build the site first"
    if args.browser:
        assert Path(args.browser).exists(), f"Browser executable not found: {args.browser}"
    args.screenshots.mkdir(parents=True, exist_ok=True)

    all_errors: list[str] = []
    remote_requests: list[str] = []
    story_states = 0
    system_states = 0

    with serve_site(args.site.resolve()) as base_url, sync_playwright() as playwright:
        launch_options = {"headless": True}
        if args.browser:
            launch_options["executable_path"] = args.browser
        browser = playwright.chromium.launch(**launch_options)
        try:
            for width, height in VIEWPORTS:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    reduced_motion="reduce",
                )
                page = context.new_page()
                page.on("pageerror", lambda error: all_errors.append(str(error)))
                page.on(
                    "request",
                    lambda request: remote_requests.append(request.url)
                    if request.url.startswith(("http:", "https:")) and not request.url.startswith(base_url)
                    else None,
                )
                response = page.goto(base_url, wait_until="load")
                assert response and response.status == 200
                beats = json.loads(page.locator("#beats-data").text_content())
                corpus = json.loads(page.locator("#corpus-data").text_content())
                assert len(beats) == 27 and len(corpus) == 11
                assert page.locator("h1").inner_text() == "Meet Morrow Works."
                assert page.locator("#systems-title").inner_text().startswith("A feature does not remove responsibility")
                assert page.locator(".system-card").count() == 9
                assert page.locator(".source-drawer").count() == 5
                assert page.locator("textarea").count() == 10

                page.mouse.wheel(0, 300)
                page.wait_for_function("scrollY > 0")
                for index in list(range(len(beats))) + list(reversed(range(len(beats)))):
                    page.evaluate(
                        """index => {
                            const heading = document.querySelector('#heading-' + index);
                            const target = innerWidth <= 800
                                ? document.getElementById('illustration').offsetHeight + 32
                                : innerHeight * .28;
                            scrollTo(0, heading.getBoundingClientRect().top + scrollY - target);
                        }""",
                        index,
                    )
                    page.wait_for_function(
                        "index => document.body.dataset.beat === String(index)", arg=index
                    )
                    assert page.locator("#illustration").get_attribute("data-scene") == beats[index]["scene"]
                    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                    if width <= 800:
                        heading = page.locator(f"#heading-{index}").bounding_box()
                        figure = page.locator("#illustration").bounding_box()
                        assert heading and figure
                        assert heading["y"] >= figure["y"] + figure["height"]
                    story_states += 1

                page.locator("#chapter-five").scroll_into_view_if_needed()
                assert page.locator("#systems-title").is_visible()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")

                for system_id in SYSTEM_IDS:
                    card = page.locator(f"#{system_id}")
                    page.evaluate(
                        """id => {
                            const card = document.getElementById(id);
                            scrollTo(0, card.getBoundingClientRect().top + scrollY - innerHeight * .08);
                        }""",
                        system_id,
                    )
                    expected_label = card.get_attribute("data-label")
                    page.wait_for_function(
                        "label => document.querySelector('#active-system-name').textContent === label",
                        arg=expected_label,
                    )
                    assert card.is_visible()
                    assert card.locator(".architecture-flow").is_visible()
                    assert card.locator(".morrow-test").is_visible()
                    drawer = card.locator(".source-drawer")
                    drawer.locator("summary").click()
                    assert drawer.locator("a").count() >= 2
                    drawer.locator("summary").click()
                    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                    system_states += 1

                page.locator("#selection").scroll_into_view_if_needed()
                first_note = page.locator("textarea").first
                first_note.fill("Versioned policy sources and their amendments")
                page.locator("#final-close").scroll_into_view_if_needed()
                assert first_note.input_value() == "Versioned policy sources and their amendments"

                page.locator("#chapter-five").scroll_into_view_if_needed()
                if width in {1440, 390}:
                    page.screenshot(
                        path=str(args.screenshots / f"{width}-systems-opening.png"), full_page=False
                    )
                    page.evaluate("scrollTo(0, document.getElementById('hindsight').getBoundingClientRect().top + scrollY - innerHeight * .08)")
                    page.wait_for_function("document.querySelector('#active-system-name').textContent === 'Hindsight'")
                    page.screenshot(
                        path=str(args.screenshots / f"{width}-hindsight.png"), full_page=False
                    )
                context.close()

            anchor_context = browser.new_context(viewport={"width": 390, "height": 844})
            anchor_page = anchor_context.new_page()
            anchor_response = anchor_page.goto(base_url + "#chapter-five", wait_until="load")
            assert anchor_response and anchor_response.status == 200
            anchor_page.wait_for_timeout(200)
            assert anchor_page.locator("#systems-title").is_visible()
            assert anchor_page.evaluate("scrollY > 0")
            anchor_context.close()

            missing_context = browser.new_context(viewport={"width": 390, "height": 844})
            missing_page = missing_context.new_page()
            missing_response = missing_page.goto(base_url + "missing/deep/path", wait_until="load")
            assert missing_response and missing_response.status == 404
            home_link = missing_page.locator("a", has_text="Return to Havesome Memory")
            assert home_link.get_attribute("href") == "https://zacaria.github.io/havesome-memory/"
            assert missing_page.locator("h1").inner_text() == "This page was not retained."
            missing_context.close()

            no_js = browser.new_context(
                java_script_enabled=False, viewport={"width": 390, "height": 844}
            )
            page = no_js.new_page()
            response = page.goto(base_url, wait_until="load")
            assert response and response.status == 200
            assert page.locator(".beat").count() == 27
            assert page.locator(".system-card").count() == 9
            assert not page.locator("#illustration").is_visible()
            page.locator("#hindsight .source-drawer summary").click()
            assert page.locator("#hindsight .source-drawer a").first.is_visible()
            assert page.locator("#final-title").inner_text().startswith("Keep the evidence")
            no_js.close()
        finally:
            browser.close()

    assert not all_errors, all_errors
    assert not remote_requests, remote_requests
    report = {
        "status": "pass",
        "browser_executable": args.browser or "playwright-bundled-chromium",
        "artifact_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        "viewports": [f"{width}x{height}" for width, height in VIEWPORTS],
        "verified_story_scroll_states": story_states,
        "verified_system_cards": system_states,
        "direct_chapter_five_anchor": True,
        "project_subpath_http": True,
        "custom_404_status_and_home_link": True,
        "no_javascript_fallback": True,
        "page_errors": all_errors,
        "remote_requests": remote_requests,
    }
    report_path = args.screenshots / "browser-verification.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
