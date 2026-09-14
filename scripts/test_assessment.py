#!/usr/bin/env python3
"""Standalone tests. ALL assessment fixtures are SYNTHETIC, not provider claims."""
import copy
import importlib.util
from pathlib import Path
from typing import Any
import unittest
import xml.etree.ElementTree as ET

AXES = ('retrieval', 'organization', 'change', 'traceability', 'portability', 'simplicity')


def fixture_browser_options(environment):
    """Use Playwright's installed browser unless explicitly overridden."""
    options = {'headless': True}
    override = environment.get('BROWSER_EXECUTABLE')
    if override:
        options['executable_path'] = override
    return options


def synthetic_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    """Deliberately invented names/evidence on reserved example.invalid hosts."""
    criteria = [dict(id=axis, label=axis.title(), question=f'Synthetic {axis} question?',
                     levels={str(n): f'Synthetic {axis} level {n} anchor.' for n in range(4)})
                for axis in AXES]
    approaches = [dict(id=f'synthetic-{i}', scope='SYNTHETIC test scope only.',
                       scores={axis: dict(value=n % 4, rationale=f'SYNTHETIC {axis} rationale.',
                                          sources=['https://example.invalid/docs'])
                               for n, axis in enumerate(AXES)},
                       strengths=['SYNTHETIC upside.'], limits=['SYNTHETIC limitation.'])
                  for i in range(13)]
    return dict(criteria=criteria, methodology=dict(title='SYNTHETIC rubric',
                summary='SYNTHETIC feature assessment.', scale_note='SYNTHETIC ordinal scale.',
                scope_note='SYNTHETIC documented scope only.'), approaches=approaches), {
                    'approaches': [{'id': a['id']} for a in approaches]}


class AssessmentTests(unittest.TestCase):
    def test_fixture_uses_managed_browser_unless_explicitly_overridden(self):
        self.assertEqual(fixture_browser_options({}), {'headless': True})
        self.assertEqual(fixture_browser_options({'BROWSER_EXECUTABLE': ''}), {'headless': True})
        self.assertEqual(fixture_browser_options({'BROWSER_EXECUTABLE': '/explicit/brave'}),
                         {'headless': True, 'executable_path': '/explicit/brave'})

    def api(self):
        path = Path(__file__).with_name('approach_assessment.py')
        self.assertTrue(path.exists(), 'Standalone assessment renderer must exist')
        spec = importlib.util.spec_from_file_location('assessment_under_test', path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_valid_synthetic_contract_is_pure(self):
        data, catalogue = synthetic_fixture()
        before = copy.deepcopy((data, catalogue))
        self.assertIsNone(self.api().validate_assessment(data, catalogue))
        self.assertEqual((data, catalogue), before)

    def test_validation_rejects_malformed_contracts(self):
        cases = [
            (('criteria',), []),
            (('criteria', 0, 'id'), 'accuracy'),
            (('criteria', 1, 'id'), 'retrieval'),
            (('criteria', 0, 'label'), ' '),
            (('criteria', 0, 'question'), None),
            (('criteria', 0, 'levels'), {'0': 'Missing anchors'}),
            (('criteria', 0, 'levels', '2'), ''),
            (('methodology',), {}),
            (('methodology', 'scope_note'), ''),
            (('approaches',), []),
            (('approaches', 1, 'id'), 'synthetic-0'),
            (('approaches', 0, 'id'), 'different-id'),
            (('approaches', 0, 'id'), 'bad\" onload=\"x'),
            (('approaches', 0, 'scope'), ''),
            (('approaches', 0, 'strengths'), []),
            (('approaches', 0, 'limits'), ['']),
            (('approaches', 0, 'scores'), {}),
            (('approaches', 0, 'scores', 'retrieval', 'rationale'), ' '),
            (('approaches', 0, 'scores', 'retrieval', 'sources'), []),
        ]
        for value in (True, False, 1.0, '2', -1, 4, [], {}):
            cases.append((('approaches', 0, 'scores', 'retrieval', 'value'), value))
        for source in ('http://example.invalid/', 'javascript:alert(1)', 'https:///path',
                       'https://user:password@example.invalid', 'https://example.invalid\\evil',
                       'https://example.invalid/\npath', 'https://example.invalid:bad/',
                       'https://@example.invalid', 'https://<bad>/', 'https://bad..invalid/', 42):
            cases.append((('approaches', 0, 'scores', 'retrieval', 'sources'), [source]))
        for path, value in cases:
            with self.subTest(path=path, value=value):
                data, catalogue = synthetic_fixture()
                target = data
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(ValueError):
                    self.api().validate_assessment(data, catalogue)

    def test_catalogue_ids_are_dynamic_and_exactly_thirteen(self):
        data, catalogue = synthetic_fixture()
        data['approaches'][0]['id'] = catalogue['approaches'][0]['id'] = 'new-synthetic-id'
        self.api().validate_assessment(data, catalogue)
        for records in (catalogue['approaches'][:-1], catalogue['approaches'] + [{'id': 'extra'}],
                        catalogue['approaches'][:-1] + [catalogue['approaches'][0]]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.api().validate_assessment(data, {'approaches': records})

    def test_unknown_is_not_zero_and_can_lack_sources(self):
        data, catalogue = synthetic_fixture()
        data['approaches'][0]['scores']['retrieval'].update(value=None, sources=[])
        self.api().validate_assessment(data, catalogue)
        self.assertIsNone(data['approaches'][0]['scores']['retrieval']['value'])

    def test_six_headers_and_shared_table_chart_values_in_fixed_order(self):
        api = self.api()
        data, _ = synthetic_fixture()
        criteria = list(reversed(data['criteria']))  # Input order must not change axes.
        assessment = data['approaches'][0]
        before = copy.deepcopy((assessment, criteria))
        headers = ET.fromstring('<tr>' + api.render_headers(criteria) + '</tr>')
        cells = ET.fromstring('<tr>' + api.render_cells(assessment, criteria) + '</tr>')
        profile = ET.fromstring(api.render_profile(assessment, criteria))
        self.assertEqual([h.tag for h in headers], ['th'] * 6)
        self.assertEqual([h.get('scope') for h in headers], ['col'] * 6)
        self.assertEqual([c.tag for c in cells], ['td'] * 6)
        self.assertEqual([c.get('data-label') for c in cells], [a.title() for a in AXES])
        points = profile.findall('.//{*}circle[@class="radar-point"]')
        self.assertEqual([p.get('data-axis') for p in points], list(AXES))
        self.assertEqual([p.get('data-score') for p in points], [c.get('data-score') for c in cells])
        self.assertEqual(profile.get('class'), 'assessment-profile')
        self.assertEqual(profile.get('data-assessment-id'), assessment['id'])
        legend=profile.findall('.//ol[@class="radar-legend"]/li')
        self.assertEqual([item.get('data-axis') for item in legend],list(AXES))
        self.assertEqual([item.get('data-score') for item in legend],[c.get('data-score') for c in cells])
        for n, (axis, cell, header) in enumerate(zip(AXES, cells, headers)):
            value = assessment['scores'][axis]['value']
            self.assertEqual(cell.get('data-score'), str(value))
            self.assertIn(f'{value}/3', ''.join(cell.itertext()))
            self.assertEqual(cell.findall('a')[0].get('href'), '#provider-' + assessment['id'])
            self.assertIn(axis.title(), ''.join(header.itertext()))
            self.assertIn(data['criteria'][n]['question'], ''.join(header.itertext()))
        items = profile.findall('.//ol[@class="assessment-criteria"]/li')
        self.assertEqual([i.get('data-axis') for i in items], list(AXES))
        for item, axis in zip(items, AXES):
            self.assertIn(f"{assessment['scores'][axis]['value']}/3", ''.join(item.itertext()))
            self.assertIn(assessment['scores'][axis]['rationale'], ''.join(item.itertext()))
            self.assertIn('https://example.invalid/docs', [a.get('href') for a in item.iter('a')])
        shape = profile.find('.//{*}polygon[@class="radar-shape"]')
        self.assertIsNotNone(shape)
        assert shape is not None
        self.assertEqual(len(shape.attrib['points'].split()), 6)
        self.assertEqual((assessment, criteria), before)

    def test_radar_coordinates_use_same_ordinal_scale_on_every_axis(self):
        import math
        api = self.api()
        data, _ = synthetic_fixture()
        sample = data['approaches'][0]
        grid_reference = None
        for value in range(4):
            for score in sample['scores'].values():
                score['value'] = value
            root = ET.fromstring(api.render_profile(sample, data['criteria']))
            grid = [p.attrib['points'] for p in root.findall('.//{*}polygon[@class="radar-grid"]')]
            if grid_reference is None:
                grid_reference = grid
            self.assertEqual(grid, grid_reference)
            self.assertEqual(len(grid), 3)
            for index, point in enumerate(root.findall('.//{*}circle[@class="radar-point"]')):
                angle = math.radians(-90 + index * 60)
                self.assertAlmostEqual(float(point.attrib['cx']), 130 + 22 * value * math.cos(angle), places=2)
                self.assertAlmostEqual(float(point.attrib['cy']), 130 + 22 * value * math.sin(angle), places=2)

    def test_unknown_never_draws_zero_or_connects_a_shape(self):
        api = self.api()
        data, _ = synthetic_fixture()
        assessment = data['approaches'][0]
        for unknown in ({'organization'}, {'retrieval', 'simplicity'}, set(AXES)):
            with self.subTest(unknown=unknown):
                sample = copy.deepcopy(assessment)
                for axis in unknown:
                    sample['scores'][axis].update(value=None, sources=[])
                profile = ET.fromstring(api.render_profile(sample, data['criteria']))
                points = profile.findall('.//{*}circle[@class="radar-point"]')
                self.assertEqual([p.get('data-axis') for p in points], [a for a in AXES if a not in unknown])
                self.assertIsNone(profile.find('.//{*}polygon[@class="radar-shape"]'))
                self.assertIsNone(profile.find('.//{*}path'))
                self.assertIsNone(profile.find('.//{*}polyline'))
                self.assertTrue(all(p.get('fill') == 'none' for p in profile.findall('.//{*}polygon')))
                cells = ET.fromstring('<tr>' + api.render_cells(sample, data['criteria']) + '</tr>')
                for axis, cell in zip(AXES, cells):
                    if axis in unknown:
                        self.assertEqual(cell.get('data-score'), 'unknown')
                        self.assertIn('Unknown', ''.join(cell.itertext()))
                        self.assertNotIn('0/3', ''.join(cell.itertext()))
                if 'retrieval' not in unknown:
                    zero = next(p for p in points if p.get('data-axis') == 'retrieval')
                    self.assertEqual((float(zero.attrib['cx']), float(zero.attrib['cy'])), (130, 130))

    def test_accessible_escaped_text_and_urls(self):
        api = self.api()
        data, catalogue = synthetic_fixture()
        attack = '<script>alert("x")</script> & \'quoted\''
        url = 'https://example.invalid/docs?q="quoted"&x=<tag>'
        criterion = data['criteria'][0]
        criterion.update(label=attack, question=attack)
        criterion['levels']['0'] = attack
        sample = data['approaches'][0]
        sample.update(scope=attack, strengths=[attack], limits=[attack])
        sample['scores']['retrieval'].update(rationale=attack, sources=[url])
        data['methodology']['summary'] = attack
        api.validate_assessment(data, catalogue)
        for fragment in (api.render_headers(data['criteria']), api.render_cells(sample, data['criteria']),
                         api.render_profile(sample, data['criteria']), api.render_methodology(data)):
            root = ET.fromstring('<root>' + fragment + '</root>')
            self.assertEqual(list(root.iter('script')), [])
            self.assertIn(attack, ''.join(root.itertext()) + ''.join(
                value for element in root.iter() for value in element.attrib.values()))
        profile = ET.fromstring(api.render_profile(sample, data['criteria']))
        svg = profile.find('.//{*}svg')
        assert svg is not None
        self.assertEqual(svg.get('role'), 'img')
        ids = {e.get('id'): e for e in profile.iter() if e.get('id')}
        self.assertEqual(len(ids), len([e for e in profile.iter() if e.get('id')]))
        for ref in (svg.attrib['aria-labelledby'] + ' ' + svg.attrib['aria-describedby']).split():
            self.assertIn(ref, ids)
            self.assertTrue(''.join(ids[ref].itertext()).strip())
        self.assertIn(attack, ''.join(svg.findall('{*}title')[0].itertext()))
        self.assertIn(url, [a.get('href') for a in profile.iter('a')])
        self.assertIsNotNone(profile.find('.//figure/figcaption'))

    def test_methodology_lists_all_anchors_scopes_and_caveats(self):
        data, _ = synthetic_fixture()
        root = ET.fromstring(self.api().render_methodology(data))
        self.assertEqual((root.tag, root.get('id')), ('details', 'score-rubric'))
        text = ''.join(root.itertext())
        for word in ('editorial', 'ordinal', 'not our own benchmarks', 'Unknown', 'not zero',
                     'no total', 'not a performance ranking'):
            self.assertIn(word, text)
        for criterion in data['criteria']:
            for anchor in criterion['levels'].values():
                self.assertIn(anchor, text)
        self.assertEqual(len(root.findall('.//dl/dt')), 24)
        scopes = root.findall('.//ul[@class="assessment-scopes"]/li')
        self.assertEqual(len(scopes), 13)
        self.assertTrue(all('SYNTHETIC test scope only.' in ''.join(s.itertext()) for s in scopes))

    def test_renderers_reject_invalid_input_without_prior_validation(self):
        api = self.api()
        data, _ = synthetic_fixture()
        sample = data['approaches'][0]
        sample['scores']['change']['value'] = True
        for render in (api.render_cells, api.render_profile):
            with self.subTest(render=render.__name__), self.assertRaises(ValueError):
                render(sample, data['criteria'])
        with self.assertRaises(ValueError):
            api.render_headers([])
        with self.assertRaises(ValueError):
            api.render_methodology(data)

    def test_browser_layout_with_host_css_at_320_and_desktop(self):
        """Optional real Chromium check; fixture served in memory, no generated site files."""
        from html import escape
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import json
        import re
        import os
        import threading
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest('Playwright is not installed; run with the browser-test environment for this fixture')
        css_path = Path(__file__).resolve().parents[1] / 'src' / 'assessment.css'
        self.assertTrue(css_path.exists(), 'Matching assessment CSS must exist')
        css = css_path.with_name('comparison.css').read_text() + '\n' + css_path.read_text()
        api = self.api()
        data, _ = synthetic_fixture()
        # Stress long unbroken copy without introducing real provider assertions.
        data['criteria'][0]['label'] = 'SYNTHETIC-' * 12
        data['approaches'][0]['scope'] += ' SYNTHETIC-' * 12
        data['approaches'][1]['scores']['change'].update(value=None, sources=[])
        inner = '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + css + '</style></head><body><main>'
        inner += '<table id="memory-comparison-table"><thead><tr><th>Approach</th>' + api.render_headers(data['criteria']) + '</tr></thead><tbody>'
        inner += ''.join('<tr><th scope="row">SYNTHETIC approach</th>' + api.render_cells(a, data['criteria']) + '</tr>' for a in data['approaches'])
        inner += '</tbody></table>' + api.render_methodology(data)
        inner += ''.join('<details class="dossier" open><summary>SYNTHETIC approach</summary><div class="dossier-body">' + api.render_profile(a, data['criteria']) + '</div></details>' for a in data['approaches'])
        inner += '</main></body></html>'
        frame = '<iframe style="width:{}px;height:900px;border:0" srcdoc="' + escape(inner) + '"></iframe>'
        # Test-only JS interrogates CSS/DOM. Shipped rendering itself has no JS.
        script = '''<script>onload=()=>{
          const results=[...document.querySelectorAll('iframe')].map(f=>{
            const d=f.contentDocument,w=f.contentWindow;
            d.querySelector('#score-rubric').open=true;
            const profiles=[...d.querySelectorAll('.assessment-profile')];
            const labels=[...d.querySelectorAll('.radar-label,.radar-scale,.assessment-profile p,.assessment-profile h4,.column-help,.score-number,#score-rubric dd')];
            const tiny=labels.filter(e=>parseFloat(w.getComputedStyle(e).fontSize)*(e instanceof w.SVGTextElement?e.getScreenCTM().a:1)<13).length;
            const overflow=[...d.querySelectorAll('.assessment-profile,.assessment-rubric,.assessment-cell')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.className);
            const clipped=[...d.querySelectorAll('.radar-chart text')].filter(e=>{const b=e.getBBox();return b.x<0||b.y<0||b.x+b.width>260||b.y+b.height>260}).length;
            return {width:w.innerWidth,chartWidth:d.querySelector('.radar-chart').getBoundingClientRect().width,client:d.documentElement.clientWidth,scroll:d.documentElement.scrollWidth,profiles:profiles.length,tiny,overflow,clipped,charts:d.querySelectorAll('.radar-chart').length,shapes:d.querySelectorAll('.radar-shape').length};
          });
          const out=document.createElement('pre');out.id='layout-result';out.textContent=JSON.stringify(results);document.body.append(out);
        }</script>'''
        html = ('<!doctype html><html><body>' + ''.join(frame.replace('{}', str(w), 1) for w in (320, 850, 1280)) + script + '</body></html>').encode()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**fixture_browser_options(os.environ))
                try:
                    page = browser.new_page()
                    response = page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='load')
                    self.assertIsNotNone(response)
                    self.assertEqual(response.status, 200)
                    result = page.locator('#layout-result')
                    result.wait_for(state='attached')
                    results = json.loads(result.inner_text())
                finally:
                    browser.close()
            self.assertEqual([r['width'] for r in results], [320, 850, 1280])
            for result in results:
                with self.subTest(viewport=result['width']):
                    self.assertEqual(result['scroll'], result['client'], result)
                    self.assertEqual(result['overflow'], [], result)
                    self.assertEqual(result['tiny'], 0, result)
                    self.assertEqual(result['clipped'], 0, result)
                    self.assertEqual((result['profiles'], result['charts'], result['shapes']), (13, 13, 12))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
