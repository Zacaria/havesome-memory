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
    styles = (ROOT/'src/story-design.css').read_text() + '\n' + (ROOT/'src/story-timeline.css').read_text()
    page = once(page,'</head>',f'<style id="story-design-styles">{styles}</style></head>','head close')
    page = once(page,'<body data-beat="intro">','<body class="story-design" data-beat="intro">','story body')
    old_header = '<header><span class="mark" aria-hidden="true">▰</span> MEMORY ENGINEERING <span class="chapter-name">THE BEGINNING</span></header>'
    header = f'<header class="story-site-header"><a class="story-brand" href="index.html">{emblem()}<span>HAVESOME MEMORY</span></a><span class="chapter-name">THE BEGINNING</span></header>'
    page = once(page,old_header,header,'story brand')

    # Edit static reading markup; evidence stays intact and UI literals are handled below.
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
        new=f'<header class="system-card__header"><div class="story-system-identity">{mark}<div><p class="system-number">{number}</p>{external(url,name,name)}</div></div>'
        main=once(main,old,new,ident+' identity')

    # Reader-facing copy: leave all source passages and embedded fixtures intact.
    copy_edits = [
        ('<p class="aside">This is an authored illustration, not a live AI response. Including evidence still does not guarantee that a real model will use it correctly.</p>', ''),
        ('This saved summary is an authored example, not a real stored record or a claim about how a provider updates memory. The received decision remains S03.', 'The received decision remains S03.'),
        (' The illustrated correction is authored, not an executed provider update.', ''),
        (' Public teaching illustration, not a real access-control system; no waiver payload is included in this version.', ''),
        ('Authored failure example, not a live retrieval or model run. ', ''),
        (' This is an authored context packet, not an actual provider integration.', ''),
        ('Illustrated answer and checks, not measured model performance. ', ''),
        ('In this authored diagram, the instruction has also reached an extracted fact, an overview and an answer cache. Those copies are illustrative—not observed records in a running system. They make the maintenance question visible: which owned representations depend on this source?', 'The instruction has also reached an extracted fact, an overview and an answer cache. Which of these copies depend on the source?'),
        (' Source inspection throughout this page is a public authoring reference, not a simulated user’s live retrieval.', ''),
        ('That is the obligation illustrated here, not proof of an executed purge. The public teaching page and authoring corpus retain the invented fixture for inspection. Hiding or changing a diagram is neither physical deletion nor real authorization. ', ''),
        ('The limit is the modeled owned stores, not every copy in the world. No live storage, access enforcement or deletion operation runs here.', 'The deletion rule covers stores owned by the team.'),
        ('SUPPORTED EXAMPLE · NOT A MODEL RUN', 'SUPPORTED ANSWER'),
        ('<div id="trust-model-label">AUTHORED ILLUSTRATION · NOT LIVE ENFORCEMENT</div>', ''),
        ('Illustrated copies · not live storage', 'Source and dependent copies'),
        ('documented center of gravity—not an end-to-end guarantee', 'main responsibilities'),
        ('<p>These are current vendor documents. We did not reproduce Hindsight benchmark claims or test a hosted or self-hosted deployment.</p>', ''),
        ('Published benchmark scores are vendor-produced. This guide does not rank Mem0 from those results or transfer Platform claims to OSS.', 'Platform and OSS are different products; their results are not interchangeable.'),
        ('<p>Provider benchmark and pricing claims remain vendor-authored and mutable. This guide did not reproduce them.</p>', ''),
        ('This guide does not generalize research results into production guarantees or treat community summaries as corpus completeness proofs.', 'Community summaries can omit source details.'),
        ('Sources and prototype boundaries', 'About the examples'),
        ('All company material is fictional. Literal searches run locally. The diagrams of authority, scope and context are authored illustrations—not a model response or provider demonstration. The exploration maps, classifications, identity distinctions and overview are authored teaching illustrations, not automated clustering, retrieval or provider output. The changing-knowledge snapshots, revisions and audit history are authored illustrations, not actual stored memories, provider updates or deletion operations. The access boundaries, context packets and owned-copy states are authored illustrations, not live enforcement, retrieval or deletion. Source inspection is the public authoring reference: it retains the invented temporary instruction even when the diagram illustrates a required purge. No data is sent or saved.', 'Morrow Works and its documents are fictional. Search runs locally; answers, memory updates, access rules and deletions are simulated. The source viewer retains all example passages, including expired or deleted ones. Nothing is sent or saved.'),
        ('This public guide requires no account and sends no data. <strong>havesome-context</strong> is a planned optional companion about what an AI sees for a task—not a prerequisite.', 'No account required. Nothing leaves your browser.'),
    ]
    for old, new in copy_edits:
        main = once(main, old, new, 'reader copy: '+old[:48])
    main = main.replace('Primary sources and evidence boundary', 'Sources')

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
    from story_timeline import add_timeline
    remainder = once(remainder, 'Original fictional teaching passages. The illustration is not a live provider or AI response.', 'All source passages from the fictional company, including those outside the current scene.', 'source viewer note')
    # Only these UI literals change; source data and executable logic stay intact.
    for old, new in [('Modeled obligation · not proof of deletion', 'Source cleared · deletion receipt retained'),
                     ('Illustrated copies · not live storage', 'Source and dependent copies')]:
        remainder = once(remainder, old, new, 'lifecycle label')
    return add_timeline(main+'</main>'+remainder)
