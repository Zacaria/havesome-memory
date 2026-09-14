"""Exercise the persistent timeline through its actual controls."""
def check_timeline(page,width,height,screenshots):
    bar=page.locator('#story-timeline')
    opener=page.locator('#timeline-overview')
    dialog=page.locator('#story-timeline-dialog')
    assert bar.evaluate('(el)=>getComputedStyle(el).position')=='fixed'
    box=bar.bounding_box()
    assert box and box['y']>=0 and box['y']+box['height']<=height+1
    assert page.locator('.timeline-chapter-link').count()==5
    assert page.locator('.timeline-step-link').count()==36
    position=page.evaluate('scrollY')
    opener.focus();page.keyboard.press('Enter')
    assert dialog.is_visible()
    assert page.locator('.timeline-close').evaluate('(el)=>el===document.activeElement')
    assert abs(page.evaluate('scrollY')-position)<2
    if width in {1440,390}:
        page.screenshot(path=str(screenshots/f'{width}-timeline-overview.png'))
    page.keyboard.press('Shift+Tab')
    assert dialog.evaluate('(el)=>el.contains(document.activeElement)')
    page.keyboard.press('Escape')
    assert not dialog.is_visible()
    assert opener.evaluate('(el)=>el===document.activeElement')
    assert abs(page.evaluate('scrollY')-position)<2
    verified=[]
    targets=page.locator('.timeline-step-link').evaluate_all('(links)=>links.map(a=>a.hash)')
    for i,target in enumerate(targets):
        opener.click()
        assert dialog.is_visible()
        # User-scrollable map, not a corrective scroll of the story destination.
        link=page.locator(f'.timeline-step-link[data-timeline-step="{i}"]')
        link.scroll_into_view_if_needed()
        link.click()
        page.wait_for_function('i=>document.querySelector("#story-timeline").dataset.activeStep===String(i)',arg=i)
        assert not dialog.is_visible()
        assert page.evaluate('location.hash')==target
        heading=page.locator(target)
        assert heading.evaluate('(el)=>el===document.activeElement')
        rect=heading.bounding_box();rail=bar.bounding_box()
        assert rect and rail and rect['y']>=0 and rect['y']<rail['y']-20,(width,i,rect,rail)
        if i<27:
            assert page.locator('body').get_attribute('data-beat')==str(i)
            if width<=800:
                figure=page.locator('#illustration').bounding_box()
                assert figure and rect['y']>=figure['y']+figure['height']
        else:
            assert page.locator('.system-card.is-active').get_attribute('data-label')==link.locator('span').last.inner_text()
        assert page.locator(f'.timeline-step-link[data-timeline-step="{i}"]').get_attribute('aria-current')=='step'
        assert page.locator('.timeline-chapter.is-current').count()==1
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        if width in {1440,390} and i in {0,14,20,27,35}:
            page.screenshot(path=str(screenshots/f'{width}-timeline-step-{i+1}.png'))
        verified.append(i)
    for group,step in [(4,27),(0,0),(3,20),(1,8),(2,14)]:
        page.locator(f'[data-timeline-chapter="{group}"] .timeline-chapter-link').click()
        page.wait_for_function('i=>document.querySelector("#story-timeline").dataset.activeStep===String(i)',arg=step)
    page.go_back()
    page.wait_for_function('document.querySelector("#story-timeline").dataset.activeStep==="8"')
    page.go_forward()
    page.wait_for_function('document.querySelector("#story-timeline").dataset.activeStep==="14"')
    opener.click()
    page.locator('[data-timeline-start]').click()
    page.wait_for_function('document.querySelector("#story-timeline").dataset.activeStep==="-1"')
    assert page.locator('#opening-title').evaluate('(el)=>el===document.activeElement')
    cue=page.locator('.scroll-cue').first.bounding_box();rail=bar.bounding_box()
    assert cue and rail and cue['y']+cue['height']<rail['y']
    if width in {1440,390}:page.screenshot(path=str(screenshots/f'{width}-timeline-opening.png'))
    return len(verified)
