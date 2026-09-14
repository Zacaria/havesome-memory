"""Build a complete navigation index from the existing story and system cards."""
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import json
import re
from visual_assets import icon

ROOT = Path(__file__).resolve().parents[1]


def add_timeline(page):
    match = re.search(r'<script id="beats-data" type="application/json">(.*?)</script>',page,re.S)
    if match is None: raise ValueError('Missing story beat data')
    beats = json.loads(match.group(1))
    assert len(beats) == 27
    class Systems(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if 'system-card' in (a.get('class') or '').split():
                self.cards.append(a['data-label'])
    parser=Systems();parser.feed(page)
    assert len(parser.cards)==9
    steps=[{'target':f'heading-{i}','title':b['title']} for i,b in enumerate(beats)]
    steps += [{'target':f'timeline-system-{i}','title':label} for i,label in enumerate(parser.cards)]
    counter=iter(range(len(parser.cards)))
    def identify(match):
        assert 'id=' not in match.group(2), 'System heading already has an ID; reconcile explicitly'
        return match.group(1)+f' id="timeline-system-{next(counter)}"'+match.group(2)
    page,count=re.subn(r'(<(?:section|article)\b[^>]*class="system-card(?: [^"]*)?"[^>]*>[\s\S]*?<h2)([^>]*>)',identify,page)
    assert count==len(parser.cards)
    groups=[('Answer','Find an answer',0,8),('Explore','Explore connections',8,14),('Update','Handle changing knowledge',14,20),('Control','Control what gets used',20,27),('Systems','Compare real systems',27,len(steps))]
    chapters=[]; overview=[]
    for group,(short,title,start,end) in enumerate(groups):
        dots=[]; entries=[]
        for i in range(start,end):
            step=steps[i];label=escape(step['title']);target=step['target']
            dots.append(f'<a class="timeline-dot" href="#{target}" data-timeline-step="{i}" aria-label="Step {i+1}: {escape(step["title"],quote=True)}" title="{escape(step["title"],quote=True)}"><span></span></a>')
            entries.append(f'<li><a class="timeline-step-link" href="#{target}" data-timeline-step="{i}" data-timeline-group="{group}"><span class="timeline-step-number">{i+1:02}</span><span>{label}</span></a></li>')
        chapters.append(f'<div class="timeline-chapter" data-timeline-chapter="{group}" data-first="{start}" data-end="{end}"><a class="timeline-chapter-link" href="#{steps[start]["target"]}" data-timeline-step="{start}" aria-label="Chapter {group+1}: {title}"><span>{group+1:02}</span> {short}</a><div class="timeline-track" aria-hidden="true"><span></span></div><div class="timeline-dots">'+''.join(dots)+'</div></div>')
        overview.append(f'<section class="timeline-group"><h3><span>{group+1:02}</span> {title}</h3><p>Steps {start+1}–{end}</p><ol start="{start+1}">'+''.join(entries)+'</ol></section>')
    bar='<nav id="story-timeline" aria-label="Story timeline"><div class="timeline-status"><p id="timeline-current"><strong>STORY</strong><span>Five chapters, 36 steps</span></p><a id="timeline-overview" href="#story-map">All '+str(len(steps))+' steps '+icon("approach","story-link-icon")+'</a></div><div class="timeline-chapters">'+''.join(chapters)+'</div></nav>'
    # Inline without JavaScript; promoted into a native modal by the enhancement.
    roadmap='<section id="story-map" aria-labelledby="story-map-title"><div class="timeline-map-header"><div><p class="timeline-map-kicker">THE WHOLE STORY · '+str(len(steps))+' STEPS</p><h2 id="story-map-title">Choose where to go.</h2><p>Follow the chapters in order—or jump straight to a question.</p></div><button class="timeline-close" hidden>Close overview</button></div><a class="timeline-start" href="#meet" data-timeline-start>Start with Morrow Works</a><div class="timeline-map-grid">'+''.join(overview)+'</div></section>'
    assert page.count('<footer>')==1
    page=page.replace('<footer>',roadmap+'<footer>',1)
    assert page.count('</body>')==1
    script=(ROOT/'src/story-timeline.js').read_text()
    return page.replace('</body>',bar+'<script id="story-timeline-script">'+script+'</script></body>',1)
