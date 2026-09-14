#!/usr/bin/env python3
"""Real-data comparison acceptance matrix. Imported by the default browser gate."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT/'src/comparison.json').read_text())
SCORES = json.loads((ROOT/'src/assessment.json').read_text())
IDS = [a['id'] for a in DATA['approaches']]
WIDTHS = [(1440,900),(1280,720),(1001,720),(1000,720),(851,800),(850,800),(768,1024),(390,844),(320,640)]


def verify_radar_geometry(chart):
    """Measure actual SVG text AND each wrapped line, not just the SVG box."""
    geometry = chart.evaluate('''svg=>{
      const v=svg.viewBox.baseVal;
      const labels=[...svg.querySelectorAll('.radar-label')];
      const text=[...svg.querySelectorAll('.radar-label,.radar-label tspan,.radar-scale')];
      const clipped=text.filter(e=>{const b=e.getBBox();return b.x<v.x || b.y<v.y || b.x+b.width>v.x+v.width || b.y+b.height>v.y+v.height}).map(e=>e.textContent);
      const sizes=text.map(e=>parseFloat(getComputedStyle(e).fontSize)*Math.hypot(e.getScreenCTM().a,e.getScreenCTM().b));
      const overlap=[];
      labels.forEach((a,i)=>labels.slice(i+1).forEach(b=>{
        const x=a.getBBox(),y=b.getBBox();
        if(x.x<y.x+y.width && x.x+x.width>y.x && x.y<y.y+y.height && x.y+x.height>y.y)overlap.push([a.textContent,b.textContent]);
      }));
      return {width:svg.getBoundingClientRect().width,labels:labels.length,lines:svg.querySelectorAll('.radar-label tspan').length,minFont:Math.min(...sizes),clipped,overlap};
    }''')
    assert geometry['labels']==len(SCORES['criteria']), geometry
    assert not geometry['clipped'] and not geometry['overlap'], geometry
    assert geometry['minFont']>=13, geometry
    return geometry


def verify_interactions(browser, base, output):
    site_sha = hashlib.sha256((ROOT/'_site/index.html').read_bytes()).hexdigest()
    results, errors, remote = [], [], []
    for width, height in WIDTHS:
        print('Interaction viewport', width, height, flush=True)
        ctx = browser.new_context(viewport={'width':width,'height':height}, reduced_motion='reduce', has_touch=width<=1000)
        page = ctx.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:remote.append(request.url) if request.url.startswith(('http:','https:')) and not request.url.startswith(base) else None)
        page.goto(base)
        pins = page.locator('#pinned-rows')
        normal = page.locator('#comparison-rows')
        header = page.locator('#memory-comparison-table thead')
        table = page.locator('#memory-comparison-table')
        page.evaluate('window.originalRows=[...document.querySelectorAll("tbody tr")];window.originalControls=[...document.querySelectorAll(".pin-checkbox")]')
        def integrity(selected):
            assert page.locator('tbody tr').count()==13
            assert page.locator('.pin-checkbox').count()==13
            assert page.locator('.pin-checkbox:checked').count()==len(selected)
            assert page.locator('#shared-radar .comparison-series:not([hidden])').count()==len(selected)
            assert page.locator('.series-legend li:not([hidden])').count()==len(selected)
            assert pins.locator('tr').evaluate_all('els=>els.map(e=>e.dataset.approach)')==[i for i in IDS if i in selected]
            assert normal.locator('tr').evaluate_all('els=>els.map(e=>e.dataset.approach)')==[i for i in IDS if i not in selected]
            assert page.evaluate('originalRows.every(r=>r.isConnected) && originalControls.every(c=>c.isConnected)')
            assert page.evaluate('(()=>{const ids=[...document.querySelectorAll("[id]")].map(n=>n.id);return ids.length===new Set(ids).size})()')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        def bring(ident):
            # Explicitly position a real unselected control below both sticky regions.
            page.locator('#pin-'+ident).evaluate('el=>{const p=document.querySelector("#pinned-rows"),h=document.querySelector("thead");if(p.contains(el)){p.scrollTop=el.closest("tr").offsetTop-p.offsetTop;document.querySelector("#memory-comparison-table").scrollIntoView()}else{scrollTo(0,scrollY+el.getBoundingClientRect().top-h.offsetHeight-(p.hidden?0:p.offsetHeight)-35)}}')
        def select(ident, checked=True):
            bring(ident)
            page.locator('#pin-'+ident).set_checked(checked)
        integrity(set())
        assert not pins.is_visible()
        expect(page.locator('#clear-selection')).to_be_disabled()
        bring(IDS[0]);page.locator('#pin-'+IDS[0]).focus();page.keyboard.press('Space');integrity({IDS[0]})
        page.keyboard.press('Space');integrity(set())
        # None, 1, several; intentionally choose a non-catalogue order.
        selected=set()
        for ident in (IDS[5], IDS[0], IDS[10]):
            select(ident); selected.add(ident); integrity(selected)
            expect(page.locator('#pin-'+ident)).to_be_focused()
        # Explicit filter retention and honest counts. No selected row is hidden.
        page.locator('#search').fill('no-such-approach')
        assert page.locator('tbody tr:visible').count()==3
        assert '0 of 13 approaches match · 3 selected (3 outside filter, kept visible)' in page.locator('#filter-status').inner_text()
        assert pins.locator('tr[hidden]').count()==0
        select(IDS[0],False);selected.remove(IDS[0]);integrity(selected)
        assert page.locator(f'tr[data-approach="{IDS[0]}"]').get_attribute('hidden') is not None
        page.locator('[data-filter="basic"]').click()
        assert pins.locator('tr:visible').count()==2
        page.locator('#search').fill('')
        page.locator('[data-filter="all"]').click()
        # Row/header alignment and sticky boundary while unpinned rows keep flowing.
        page.evaluate('scrollTo(0,scrollY+document.querySelector("#memory-comparison-table").getBoundingClientRect().top+200)')
        page.wait_for_timeout(40)
        hb, pb, tb = header.bounding_box(), pins.bounding_box(), table.bounding_box()
        assert abs(hb['y'])<2, (width,hb)
        assert abs(pb['y']-(hb['y']+hb['height']))<2,(width,hb,pb)
        assert pb['height']<=height*.36+3,(width,pb)
        assert hb['height']+pb['height']<=height*.68,(width,hb,pb)

        if width>1000:
            geometry=page.evaluate('''()=>{const cells=s=>[...document.querySelector(s).children].map(e=>{const r=e.getBoundingClientRect();return [r.x,r.width]});return [cells('.comparison-columns'),cells('#pinned-rows tr'),cells('#comparison-rows tr:not([hidden])')]}''')
            for row in geometry[1:]:
                assert len(row)==6
                for actual,expected in zip(row,geometry[0]):
                    assert abs(actual[0]-expected[0])<2 and abs(actual[1]-expected[1])<2,(width,geometry)
        # Independent scrolling doesn't move the page.
        pins.evaluate('e=>e.scrollTop=e.scrollHeight')
        scroll_before=page.evaluate('scrollY')
        pins.focus();page.keyboard.press('Home');page.keyboard.press('ArrowDown')
        assert page.evaluate('scrollY')==scroll_before
        # The sticky rowgroups cannot follow into the rubric or benchmarks.
        page.locator('#comparison-end').scroll_into_view_if_needed()
        page.evaluate('scrollTo(0,scrollY+document.querySelector("#comparison-end").getBoundingClientRect().top-10)')
        assert header.bounding_box()['y']+header.bounding_box()['height']<=12
        assert pins.bounding_box()['y']+pins.bounding_box()['height']<=12
        page.locator('#clear-selection').evaluate('e=>e.click()')
        integrity(set())
        # Any selection count, up to all thirteen. No clones, arbitrary cap, or dead ends.
        for ident in IDS:select(ident)
        integrity(set(IDS))
        assert normal.locator('tr').count()==0
        assert pins.evaluate('e=>e.scrollHeight>e.clientHeight')
        page.locator('#search').fill('still-no-match')
        assert '13 selected (13 outside filter, kept visible)' in page.locator('#filter-status').inner_text()
        assert pins.locator('tr:visible').count()==13
        assert pins.bounding_box()['height']<=height*.36+3
        page.locator('#search').fill('')
        # Resize selected rows through both desktop and card layouts.
        for new_width in (390,1280,width):
            page.set_viewport_size({'width':new_width,'height':height})
            page.wait_for_timeout(40)
            integrity(set(IDS))
            assert pins.bounding_box()['height']<=height*.36+3
        bring(IDS[-1]);page.locator('#pin-'+IDS[-1]).uncheck()
        integrity(set(IDS[:-1]))
        page.locator('#clear-selection').click();integrity(set())
        expect(page.locator('#pinned-rows')).to_be_hidden()
        # Shared chart has one stable, uniquely named/color-keyed series per actual approach.
        for ident in IDS: select(ident)
        integrity(set(IDS))
        page.evaluate('document.querySelector("#memory-comparison-table").scrollIntoView()')
        disclosure=page.locator('#shared-radar-disclosure')
        if disclosure.get_attribute('open') is None: disclosure.locator('summary').click()
        page.wait_for_timeout(50)
        assert page.locator('.axis-buttons,.axis-button').count()==0
        assert page.locator('.radar-axis-target[role="button"][tabindex="0"]').count()==len(SCORES['criteria'])
        radar_geometry = verify_radar_geometry(page.locator('#shared-radar'))
        for criterion in SCORES['criteria']:
            button=page.locator(f'.radar-axis-target[data-axis="{criterion["id"]}"]')
            assert ' '.join(button.locator('tspan').all_text_contents())==criterion['label']
            expect(button).to_have_accessible_name(criterion['label'])
            button.scroll_into_view_if_needed();button.focus();page.keyboard.press('Enter')
            expect(page.locator('#radar-tooltip')).to_be_visible()
            assert page.locator('#radar-tooltip').evaluate('e=>e.matches(":popover-open")')
            assert page.locator('#radar-tooltip strong').inner_text()==criterion['label']
            assert criterion['question'] in page.locator('#radar-tooltip').inner_text()
            expected={a['id']: 'unknown' if a['scores'][criterion['id']]['value'] is None else str(a['scores'][criterion['id']]['value']) for a in SCORES['approaches']}
            assert page.locator('#radar-tooltip li').evaluate_all('els=>Object.fromEntries(els.map(e=>[e.dataset.series,e.dataset.score]))')==expected
            tip=page.locator('#radar-tooltip').bounding_box()
            assert tip['x']>=0 and tip['y']>=0 and tip['x']+tip['width']<=width+1 and tip['y']+tip['height']<=height+1
            if width > 1200:
                panel_box=page.locator('#shared-radar-panel').bounding_box()
                assert tip['x']+tip['width']<=panel_box['x']-10, 'Desktop axis popup must not obscure the shared radar or legend'
            assert page.locator('#radar-tooltip').evaluate('e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+5,r.y+5))}')
            if width in (1440,390) and criterion==SCORES['criteria'][-1]:page.screenshot(path=str(output/f'{width}-shared-radar-tooltip.png'))
            page.keyboard.press('Escape');expect(page.locator('#radar-tooltip')).to_be_hidden()
            page.keyboard.press('Space');expect(page.locator('#radar-tooltip')).to_be_visible()
            page.keyboard.press('Escape')
        # Native Tab traversal reaches each SVG control, not a duplicated HTML key.
        page.locator('.radar-axis-target').first.focus()
        for criterion in SCORES['criteria'][1:]:
            page.keyboard.press('Tab')
            expect(page.locator(f'.radar-axis-target[data-axis="{criterion["id"]}"]')).to_be_focused()
            expect(page.locator('#radar-tooltip')).to_be_visible()
        page.keyboard.press('Escape')
        for assessment in SCORES['approaches']:
            series=page.locator('#shared-radar [data-series="'+assessment['id']+'"]')
            profile=page.locator('#provider-'+assessment['id'])
            read='els=>els.map(e=>[e.dataset.axis,e.dataset.score,e.getAttribute("cx"),e.getAttribute("cy")])'
            assert series.locator('.radar-point').evaluate_all(read)==profile.locator('.radar-point').evaluate_all(read)
            assert series.locator('.radar-shape').count()==int(all(s['value'] is not None for s in assessment['scores'].values()))
        palette=page.locator('#shared-radar [data-series]').evaluate_all('els=>els.map(e=>[e.dataset.name,e.style.getPropertyValue("--series-color")])')
        assert len({x[0] for x in palette})==13 and len({x[1] for x in palette})==13
        legend=page.locator('[data-highlight="'+IDS[-1]+'"]')
        legend.scroll_into_view_if_needed();legend.focus()
        expect(legend).to_have_attribute('aria-pressed','true')
        assert page.locator('.comparison-series.is-muted').count()==12
        assert page.locator('.comparison-series.is-highlighted .series-letter').text_content()=='M'
        if width<=1000:legend.tap()
        else:legend.click()
        expect(legend).to_have_attribute('aria-pressed','true')
        page.locator('#reset-series').click()
        assert page.locator('.comparison-series.is-muted').count()==0
        page.locator('[data-remove="'+IDS[-1]+'"]').click();integrity(set(IDS[:-1]))
        # Hover/focus/touch, blur/Escape, filtering, and scrolling away all dismiss cleanly.
        target=page.locator('.radar-axis-target').first

        target.scroll_into_view_if_needed()
        if width<=1000:target.tap()
        else:target.hover()

        expect(page.locator('#radar-tooltip')).to_be_visible()
        target.focus()
        disclosure.locator('summary').focus();expect(page.locator('#radar-tooltip')).to_be_hidden()
        target.focus();expect(page.locator('#radar-tooltip')).to_be_visible()
        page.keyboard.press('End')
        if page.locator('#radar-tooltip').evaluate('e=>e.scrollHeight>e.clientHeight'):
            assert page.locator('#radar-tooltip').evaluate('e=>e.scrollTop>0')
        page.locator('#search').fill('not-in-table');expect(page.locator('#radar-tooltip')).to_be_hidden()
        assert page.locator('#shared-radar .comparison-series:not([hidden])').count()==12
        page.locator('#search').fill('')
        spoke=page.locator('.radar-axis-target').first
        spoke.scroll_into_view_if_needed();spoke.focus();page.keyboard.press('Enter')
        expect(page.locator('#radar-tooltip')).to_be_visible()
        page.locator('.shared-radar-body').evaluate('e=>e.scrollTop=e.scrollHeight')
        if width>1200:
            page.locator('#comparison-end').evaluate('e=>scrollTo(0,scrollY+e.getBoundingClientRect().top)')
        expect(page.locator('#radar-tooltip')).to_be_hidden()
        if width in (1440,390):
            page.locator('.shared-radar-body').evaluate('e=>e.scrollTop=0')
            page.evaluate('document.querySelector("#memory-comparison-table").scrollIntoView()')
            page.screenshot(path=str(output/f'{width}-shared-radar-pinned.png'))
        if width<=1200:disclosure.locator('summary').click()
        page.locator('#clear-selection').click();integrity(set())
        if width in (1440,390):page.screenshot(path=str(output/f'{width}-descriptive-table.png'))
        results.append({'viewport':[width,height],'selection_counts':[0,1,2,3,12,13],'axis_inspections':sum(len(a['scores']) for a in SCORES['approaches']),'radar_geometry':radar_geometry,'same_nodes':True,'bounded_pins':True,'sticky_end':True,'aligned_columns':width>1000,'retained_filter':True})
        ctx.close()
    # No-JS: native sources/details and disabled pins, without a dead toolbar.
    ctx=browser.new_context(java_script_enabled=False,viewport={'width':320,'height':640})
    p=ctx.new_page();p.goto(base)
    assert p.locator('.pin-checkbox:disabled').count()==13
    assert not p.locator('#shared-radar-panel').is_visible()
    assert p.locator('.radar-chart').count()==13
    assert not p.locator('.selection-toolbar').is_visible()
    p.locator('#provider-supermemory > summary').click()
    assert not p.locator('#provider-supermemory .claim:visible').count()
    p.locator('#provider-supermemory .citations > summary').click()
    p.locator('#provider-supermemory .historical > summary').click()
    assert p.locator('#provider-supermemory .historical .claim:visible').count()==3
    ctx.close()
    assert not errors,errors
    assert not remote,remote
    assert hashlib.sha256((ROOT/'_site/index.html').read_bytes()).hexdigest()==site_sha, 'Site changed during browser verification; rebuild and rerun against a stable artifact'
    report={'status':'pass','matrix':results,'errors':errors,'remote_requests':remote,'no_js':True,'sha256':site_sha}
    (output/'comparison-interactions-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    from playwright.sync_api import sync_playwright
    from test_site_browser import serve_site
    with serve_site(ROOT/'_site') as base,sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True, executable_path=os.environ.get('BROWSER_EXECUTABLE') or None)
        try:print(json.dumps(verify_interactions(browser,base,ROOT/'_verification'),indent=2))
        finally:browser.close()
