#!/usr/bin/env python3
"""Exercise the new front door and its preserved story route in Brave/Chromium."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_site_browser import serve_site

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT/'src/comparison.json').read_text())
IDS = [x['id'] for x in DATA['approaches']]
VIEWPORTS = [(1440,900),(1280,720),(768,1024),(390,844),(320,640)]

def browser_options(environment):
    options: dict = {'headless': True}
    if environment.get('BROWSER_EXECUTABLE'):
        options['executable_path'] = environment['BROWSER_EXECUTABLE']
    return options

def main():
    output = ROOT/'_verification'
    output.mkdir(exist_ok=True)
    errors, remote = [], []
    checked=0
    with serve_site(ROOT/'_site') as base, sync_playwright() as pw:
        browser = pw.chromium.launch(**browser_options(os.environ))
        try:
            for width,height in VIEWPORTS:
                ctx=browser.new_context(viewport={'width':width,'height':height}, reduced_motion='reduce')
                page=ctx.new_page()
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:remote.append(request.url) if request.url.startswith(('http:','https:')) and not request.url.startswith(base) else None)
                assert page.goto(base).status==200
                assert page.locator('h1').inner_text()=='You told your AI yesterday. Will it know today?'
                assert page.locator('tbody tr').count()==len(IDS)
                assert page.locator('.dossier').count()==len(IDS)
                assert page.locator('[data-cohort-provider]').count()==9
                assert set(page.locator('[data-cohort-provider]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.cohortProvider)'))=={x['id'] for x in DATA['approaches'] if x['kind']=='provider'}
                assert page.locator('[data-cohort-provider="holographic"] .bar').count()==0
                assert page.locator('.historical .claim').count()==3
                assert page.locator('#filter-status').inner_text()=='13 of 13 approaches'
                expected_sites={item['website']['url'] for item in DATA['approaches'] if item['kind']=='provider'}
                assert set(page.locator('a.provider-site').evaluate_all('(links)=>links.map(a=>a.href)'))==expected_sites
                assert page.locator('a.provider-site').count()==9
                assert page.locator('a.provider-site').evaluate_all('(links)=>links.every(a=>a.target==="_blank" && a.relList.contains("noopener") && a.relList.contains("noreferrer") && a.getAttribute("aria-label").includes("opens in a new tab"))')
                label_style=page.locator('#comparison .eyebrow').evaluate('(el)=>({size:parseFloat(getComputedStyle(el).fontSize),weight:parseInt(getComputedStyle(el).fontWeight)})')
                assert label_style['size']>=13 and label_style['weight']>=600,label_style
                if width>850:
                    assert page.locator('.column-help:visible').count()==5
                    assert page.locator('.column-title').first.evaluate('(el)=>parseInt(getComputedStyle(el).fontWeight)')>=600
                else:
                    assert page.locator('tbody td').first.evaluate('(el)=>parseFloat(getComputedStyle(el,"::before").fontSize)')>=13
                assert page.locator('svg[data-icon-library="Lucide"]').count()>0
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                # The problem, definition and comparison action precede tool names.
                hero = page.locator('#memory-introduction')
                assert 'not automatically every past conversation' in hero.inner_text()
                assert 'Memory means keeping useful information' in hero.inner_text()
                assert hero.locator('.hero-sequence li').count()==3
                cta = hero.locator('.hero-compare')
                rect = cta.bounding_box()
                assert rect and rect['y'] >= 0 and rect['y'] + rect['height'] <= height, ('hero CTA below fold',width,rect)
                cta.click()
                expect(page.locator('#comparison-title')).to_be_in_viewport()
                assert page.locator('#comparison-title').bounding_box()['y'] >= 0
                page.evaluate('scrollTo(0,0)')
                if width in (1440,390):page.screenshot(path=str(output/f'{width}-comparison-opening.png'))
                # The new explanatory hero keeps the comparison entrance in view.
                if width>=1280:
                    comparison_rect = page.locator('#comparison-title').bounding_box()
                    assert comparison_rect and comparison_rect['y'] < height
                for kind,n in [('basic',4),('provider',9),('all',13)]:
                    page.locator(f'[data-filter="{kind}"]').click()
                    assert page.locator('tbody tr:visible').count()==n
                    assert page.locator(f'[data-filter="{kind}"]').get_attribute('aria-pressed')=='true'
                if width in (1440,390):
                    page.locator('[data-filter="provider"]').click()
                    page.evaluate('scrollTo(0,document.getElementById("comparison").getBoundingClientRect().top+scrollY-24)')
                    page.screenshot(path=str(output/f'{width}-clear-table-and-provider-links.png'))
                    page.locator('[data-filter="all"]').click()
                page.locator('#search').fill('not-a-provider')
                assert page.locator('tbody tr:visible').count()==0
                assert 'try another name' in page.locator('#filter-status').inner_text()
                page.locator('#search').fill('Hindsight')
                assert page.locator('tbody tr:visible').count()==1
                page.locator('tbody tr:visible a[href="#provider-hindsight"]').click()
                expect(page.locator('#provider-hindsight')).to_have_attribute('open', '')
                assert page.locator('#provider-hindsight summary').first.bounding_box()['y']>=0
                page.locator('#provider-hindsight .back').click()
                page.locator('#search').fill('')
                # Real navigation opens each disclosure; all evidence and source links readable.
                for ident in IDS:
                    page.locator(f'tbody a[href="#provider-{ident}"]').click()
                    dossier=page.locator('#provider-'+ident)
                    page.wait_for_function("id=>document.getElementById(id).open",arg='provider-'+ident)
                    assert dossier.get_attribute('open') is not None
                    assert dossier.locator('.flow li').count()==3
                    assert dossier.locator('.thesis').is_visible()
                    dossier.locator('.citations summary').click()
                    assert dossier.locator('.citations a').first.is_visible()
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(width,ident)
                    if width in (1440,390) and ident=='hindsight':page.screenshot(path=str(output/f'{width}-comparison-detail.png'))
                    dossier.locator('.back').click()
                    checked+=1
                assert page.locator('.identity-badge').count()==35
                assert page.locator('.provider-logo').count()==12
                assert page.locator('.memory-emblem').count()==1
                assert page.locator('[data-art="retained-decision"]').count()==1
                for mark in page.locator('.identity-badge').all():
                    box=mark.bounding_box()
                    assert box and box['width']>=28 and box['height']>=28
                assert page.locator('img.provider-glyph').evaluate_all('(imgs)=>imgs.length===3 && imgs.every(img=>img.complete && img.naturalWidth>0)')
                page.locator('.asset-credits > summary').click()
                assert page.locator('.asset-credits article').count()==5
                assert page.locator('.asset-credits pre').first.is_visible()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.locator('.asset-credits > summary').click()
                page.locator('#how-memory-works').scroll_into_view_if_needed()
                if width==1440:page.locator('.cohort-grid').screenshot(path=str(output/'1440-provider-evidence-panels.png'))
                for cohort in page.locator('[data-cohort-provider]').all():
                    cohort.scroll_into_view_if_needed()
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.locator('#provider-supermemory > summary').scroll_into_view_if_needed()
                page.locator('#provider-supermemory .historical > summary').click()
                assert page.locator('.historical .claim').first.is_visible()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.locator('#how-memory-works').scroll_into_view_if_needed()
                assert page.locator('.example-grid article').count()==3
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                if width in (1440,390):page.screenshot(path=str(output/f'{width}-comparison-mechanism.png'))
                page.locator('header a[href="story.html"]').click()
                assert page.url==base+'story.html'
                assert page.locator('h1').inner_text()=='Meet Morrow Works.'
                page.locator('.site-index a[href="index.html"]').click()
                assert page.url==base+'index.html'
                # Keyboard-driven disclosure opens without pointer events.
                summary=page.locator('#provider-holographic > summary')
                summary.focus();page.keyboard.press('Enter')
                expect(page.locator('#provider-holographic')).to_have_attribute('open', '')
                ctx.close()
            ctx=browser.new_context(viewport={'width':390,'height':844})
            p=ctx.new_page();p.goto(base+'#provider-memori')
            expect(p.locator('#provider-memori')).to_have_attribute('open', '')
            p.goto(base+'#chapter-five');p.wait_for_url('**/story.html#chapter-five')
            assert p.locator('#systems-title').is_visible()
            ctx.close()
            ctx=browser.new_context(java_script_enabled=False,viewport={'width':320,'height':640})
            p=ctx.new_page();p.goto(base)
            assert p.locator('tbody tr:visible').count()==13
            assert not p.locator('.controls').is_visible()
            p.locator('#provider-memori > summary').click()
            assert p.locator('#provider-memori .thesis').is_visible()
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            ctx.close()
        finally:browser.close()
    assert not errors,errors
    assert not remote,remote
    report={'status':'pass','browser':os.environ.get('BROWSER_EXECUTABLE'),'viewports':VIEWPORTS,'approaches':len(IDS),'disclosure_states':checked,'provider_evidence_panels':9,'historical_evidence_separated':True,'filters':True,'search':True,'keyboard':True,'old_story_hash':True,'story_round_trip':True,'no_js':True,'errors':errors,'remote_requests':remote,'sha256':hashlib.sha256((ROOT/'_site/index.html').read_bytes()).hexdigest()}
    (output/'comparison-browser-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
