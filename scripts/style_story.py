"""Apply the shared presentation without rewriting the pinned teaching corpus."""
from html import escape
from pathlib import Path
import json
import re
from visual_assets import badge, emblem, icon, load_assets, load_ui_icons

ROOT = Path(__file__).resolve().parents[1]


def once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError(f'Expected one {label}, found {text.count(old)}')
    return text.replace(old, new, 1)


def external(url, label, provider):
    return f'<a class="story-provider-site" href="{escape(url,quote=True)}" target="_blank" rel="noopener noreferrer" aria-label="Visit {escape(provider,quote=True)} — opens in a new tab">{escape(label)}{icon("external","story-link-icon")}</a>'


def apply_story_design(page):
    assets = load_assets()
    catalogue = json.loads((ROOT/'src/comparison.json').read_text())
    providers = {item['id']:item for item in catalogue['approaches'] if item['kind']=='provider'}
    styles = (ROOT/'src/story-design.css').read_text()
    page = once(page,'</head>',f'<style id="story-design-styles">{styles}</style></head>','head close')
    page = once(page,'<body data-beat="intro">','<body class="story-design" data-beat="intro">','story body')
    old_header = '<header><span class="mark" aria-hidden="true">▰</span> MEMORY ENGINEERING <span class="chapter-name">THE BEGINNING</span></header>'
    header = f'<header class="story-site-header"><a class="story-brand" href="index.html">{emblem()}<span>HAVESOME MEMORY</span></a><span class="chapter-name">THE BEGINNING</span></header>'
    page = once(page,old_header,header,'story brand')

    # Change only the static reading markup. Scripts and embedded evidence stay byte-identical.
    main, remainder = page.split('</main>',1)
    nav_items = [('index.html','Compare','approach'),('#meet','Intro','chat'),('#chapter-two','Explore','search'),('#chapter-three','Updates','retrieve'),('#chapter-four','Control','control'),('#chapter-five','Systems','hosting')]
    nav = '<nav class="site-index" aria-label="Chapter index">' + ''.join(f'<a href="{url}">{icon(symbol,"story-nav-icon")}<span>{label}</span></a>' for url,label,symbol in nav_items) + '</nav>'
    main,n = re.subn(r'<nav class="site-index" aria-label="Chapter index">.*?</nav>',lambda _:nav,main,count=1)
    if n != 1: raise ValueError('Missing story chapter index')

    def chapter_label(match):
        label = match.group(1)
        symbol = 'notes'
        if 'TWO' in label: symbol='search'
        elif 'THREE' in label: symbol='retrieve'
        elif 'FOUR' in label or 'MORROW WORKS STORY' in label: symbol='control'
        elif 'FIVE' in label: symbol='hosting'
        elif 'PLACE' in label: symbol='files'
        return f'<p class="eyebrow">{icon(symbol,"story-section-icon")}<span>{label}</span></p>'
    main = re.sub(r'<p class="eyebrow">(.*?)</p>',chapter_label,main)
    main = once(main,'<div class="visual-heading"><span>MORROW WORKS</span>',f'<div class="visual-heading"><span>{icon("notes","story-scene-icon")}MORROW WORKS</span>','scene heading')
    main = once(main,'<button id="sources-open">Source passages</button>',f'<button id="sources-open">{icon("search","story-link-icon")}Read source passages</button>','source control')

    reading = '<p class="flow-reading-guide">Follow the sequence from input to output. <strong>Boxes are information; arrows name the operation.</strong></p>'
    main,n = re.subn(r'(<div class="architecture-flow" aria-label="[^"]+">)',lambda match:reading+match.group(1),main)
    if n != 5: raise ValueError('Expected five provider architecture flows')

    system_labels = {'hindsight':'Hindsight','mem0':'Mem0 Platform + Dream','openviking':'OpenViking','supermemory':'Supermemory','graphrag':'Microsoft GraphRAG'}
    for ident,name in system_labels.items():
        number = {'hindsight':'29 / HINDSIGHT','mem0':'30 / MEM0','openviking':'31 / OPENVIKING','supermemory':'32 / SUPERMEMORY','graphrag':'33 / MICROSOFT GRAPHRAG'}[ident]
        if ident == 'graphrag':
            mark = '<span class="identity-badge concept-badge" aria-hidden="true" title="Lucide concept icon, not a Microsoft logo">'+icon('approach')+'</span>'
            url='https://microsoft.github.io/graphrag/'
            site_label='Project website'
        else:
            mark=badge(ident,'story',assets)
            url=providers[ident]['website']['url']
            site_label='Provider website'
        old=f'<header class="system-card__header"><p class="system-number">{number}</p>'
        new=f'<header class="system-card__header"><div class="story-system-identity">{mark}<div><p class="system-number">{number}</p><strong>{escape(name)}</strong></div></div>{external(url,site_label,name)}'
        main=once(main,old,new,ident+' identity')

    # Pair each representation with its source system, not a nameless strip of jargon.
    objects=[('facts → observations','Hindsight'),('memories → entity graph','Mem0'),('L0 → L1 → L2','OpenViking'),('documents → evolving facts','Supermemory'),('text units → communities','GraphRAG')]
    for representation,name in objects:
        old=f'<span>{representation}</span>'
        new=f'<span><b class="object-system-name">{name}</b>{representation}</span>'
        main=once(main,old,new,name+' representation label')
    responsibility_icons={'sources':'notes','representation':'memory','retrieval':'search','change':'retrieve','control':'control','context':'chat','operation':'hosting'}
    for key,symbol in responsibility_icons.items():
        pattern=rf'(<li data-responsibility="{key}"><span>)(\d+)(</span>)'
        main,n=re.subn(pattern,lambda m:m.group(1)+icon(symbol,'story-rail-icon')+'<b>'+m.group(2)+'</b>'+m.group(3),main)
        if n!=1:raise ValueError('Missing responsibility '+key)

    library=load_ui_icons()
    credits=[]
    for ident in ['hindsight','mem0','supermemory']:
        asset=assets[ident]
        credits.append(f'<article><h3>{escape(asset["name"])}</h3><p><a href="{escape(asset["source_url"],quote=True)}" rel="noreferrer">Original provider asset</a> · <a href="{escape(asset["license_url"],quote=True)}" rel="noreferrer">License source</a></p><p>{escape(asset["modifications"])}</p><pre>{escape(asset["license_notice"])}</pre></article>')
    credits.append(f'<article><h3>Lucide interface icons</h3><p><a href="{escape(library["website"],quote=True)}" rel="noreferrer">Lucide</a> · <a href="{escape(library["license_url"],quote=True)}" rel="noreferrer">Pinned license notices</a></p><pre>{escape(library["license_notice"])}</pre></article>')
    credits_html='<details class="story-asset-credits"><summary>Logo &amp; icon sources</summary><p>Provider marks identify their products; name tiles and concept icons are not replacement logos. No affiliation or endorsement. Original story illustrations are retained; interface icons use Lucide.</p>'+''.join(credits)+'</details>'
    main=once(main,'<footer>',credits_html+'<footer>','story credits placement')
    return main+'</main>'+remainder
