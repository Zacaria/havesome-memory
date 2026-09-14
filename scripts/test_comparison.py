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
