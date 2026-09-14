#!/usr/bin/env python3
"""Regression tests for the comparison-first entry point."""
import tempfile
import unittest
from pathlib import Path
from build_site import build

class ComparisonTests(unittest.TestCase):
    def test_browser_override_and_playwright_managed_fallback(self):
        # Isolate the pure option builder without importing optional Playwright.
        import ast
        source = Path(__file__).with_name('test_comparison_browser.py').read_text()
        tree = ast.parse(source)
        functions: list[ast.stmt] = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'browser_options']
        self.assertEqual(len(functions), 1, 'A testable browser-option builder is required')
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<browser-options>', 'exec'), namespace)
        options = namespace['browser_options']
        self.assertEqual(options({'BROWSER_EXECUTABLE': ''}), {'headless': True})
        self.assertEqual(options({}), {'headless': True})
        self.assertEqual(options({'BROWSER_EXECUTABLE': '/custom/brave'}), {'headless': True, 'executable_path': '/custom/brave'})

    def test_embedded_svg_rejects_active_content_and_external_references(self):
        from visual_assets import safe_svg
        for payload in (
            '<svg viewBox="0 0 32 32"><script>alert(1)</script></svg>',
            '<svg viewBox="0 0 32 32" onload="alert(1)"><path d="M0 0"/></svg>',
            '<svg viewBox="0 0 32 32"><image href="https://example.invalid/image.svg"/></svg>',
            '<svg viewBox="0 0 32 32"><path fill="url(https://example.invalid/a.svg)"/></svg>',
            '<svg viewBox="0 0 32 32"><path fill="url(#missing)"/></svg>',
            '<!DOCTYPE svg><svg viewBox="0 0 32 32"/>',
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                safe_svg(payload, 'test')
        logo = '<svg viewBox="0 0 32 32"><defs><clipPath id="a"><rect width="32" height="32"/></clipPath></defs><path clip-path="url(#a)" d="M0 0h32v32z"/></svg>'
        first, second = safe_svg(logo,'row-mark'), safe_svg(logo,'chart-mark')
        self.assertIn('url(#row-mark-a)', first)
        self.assertIn('url(#chart-mark-a)', second)
        self.assertNotIn('id="a"', first+second)

    def test_embedded_png_is_hash_pinned_and_not_an_arbitrary_image_url(self):
        from visual_assets import load_assets, raster_data
        import base64, hashlib
        original = load_assets()['hindsight']
        self.assertTrue(raster_data(original).startswith('data:image/png;base64,'))
        altered = dict(original, asset_sha256='0'*64)
        with self.assertRaises(ValueError):
            raster_data(altered)
        for suffix in (b'<script/>', b'garbage'):
            raw = base64.b64decode(original['png_base64']) + suffix
            altered = dict(original, png_base64=base64.b64encode(raw).decode(), asset_sha256=hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ValueError):
                raster_data(altered)
        with self.assertRaises(ValueError):
            raster_data(dict(original, width=9999))

    def test_table_explains_columns_and_links_to_every_provider(self):
        from html.parser import HTMLParser
        import json
        class Headers(HTMLParser):
            def __init__(self):
                super().__init__(); self.links=[]
            def handle_starttag(self,tag,attrs):
                if tag=='a': self.links.append(dict(attrs))
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp)); home=(Path(tmp)/'index.html').read_text()
            for text in ('Saved information','What is kept for future tasks.','Recall method','How the agent finds it again.','Published tests','Reported results—not a shared ranking.','Runs on','Your device, your server, or a cloud service.'):
                self.assertIn(text,home)
            parser=Headers();parser.feed(home)
            links=[x for x in parser.links if x.get('class')=='provider-site']
            self.assertEqual(len(links),9)
            self.assertTrue(all(x.get('target')=='_blank' and set(x.get('rel','').split()) >= {'noopener','noreferrer'} for x in links))
            self.assertIn('data-icon-library="Lucide"',home)
            self.assertIn('Lucide Icons and Contributors',home)

    def test_story_uses_the_shared_design_without_changing_its_corpus(self):
        import json,re
        from build_site import STORY, STORY_SHA256
        import hashlib
        raw=STORY.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),STORY_SHA256)
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            story=(Path(tmp)/'story.html').read_text()
            self.assertIn('class="story-site-header"',story)
            self.assertIn('data-icon-library="Lucide"',story)
            self.assertEqual(story.count('class="story-provider-site"'),5)
            self.assertEqual(story.count('class="flow-reading-guide"'),5)
            self.assertIn('Lucide Icons and Contributors',story)
            for ident in ['beats-data','corpus-data']:
                pattern=rf'<script id="{ident}" type="application/json">(.*?)</script>'
                before=re.search(pattern,raw.decode(),re.S).group(1)
                after=re.search(pattern,story,re.S).group(1)
                self.assertEqual(json.loads(before),json.loads(after))

    def test_visual_identities_are_embedded_and_keep_text_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            build(output)
            home = (output / 'index.html').read_text()
            self.assertIn('class="memory-emblem"', home)
            self.assertEqual(home.count('class="identity-badge '), 35)
            self.assertIn('data-art="retained-decision"', home)
            self.assertIn('data-visual="memory"', home)
            self.assertIn('Hindsight', home)
            self.assertEqual(home.count('<img class="provider-glyph"'), 3)
            self.assertEqual(home.count('class="identity-badge provider-logo '), 12)

    def test_comparison_is_front_door_and_story_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            build(output)
            home = (output / 'index.html').read_text()
            self.assertIn('You told your AI yesterday. Will it know today?', home)
            self.assertIn('id="memory-introduction"', home)
            self.assertIn('not automatically every past conversation', home)
            self.assertIn('Memory means keeping useful information', home)
            self.assertIn('Use a 30-second timeout.', home)
            self.assertIn('Illustrative example, not a live agent response.', home)
            self.assertIn('class="hero-compare" href="#comparison"', home)
            self.assertLess(home.index('id="memory-introduction"'), home.index('id="comparison"'))
            self.assertNotIn('Meet Morrow Works.', home)
            self.assertIn('href="story.html', home)
            story = output / 'story.html'
            self.assertTrue(story.exists())
            self.assertIn('Meet Morrow Works.', story.read_text())

if __name__ == '__main__':
    unittest.main()
