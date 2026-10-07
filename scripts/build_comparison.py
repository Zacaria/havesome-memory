#!/usr/bin/env python3
"""Render the comparison from explicit, attributed editorial data."""
from html import escape
import json
from pathlib import Path
from visual_assets import badge, emblem, icon, load_assets, load_ui_icons, retained_art

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = [
    ('Approach', 'A basic pattern or memory provider.', 'approach'),
    ('Saved information', 'What is kept for future tasks.', 'memory'),
    ('Recall method', 'How the agent finds it again.', 'search'),
    ('Published tests', 'Each maker’s own result. Tests differ, so do not compare numbers across rows.', 'chart'),
    ('Runs on', 'Device, server, or cloud service.', 'hosting'),

]


def e(value):
    return escape(str(value), quote=True)

def link(source, label=None):
    return f'<a href="{e(source["url"])}" rel="noreferrer">{e(label or source["title"])} ↗</a>'

def render():
    data = json.loads((ROOT / 'src/comparison.json').read_text())
    assessment_data = json.loads((ROOT / 'src/assessment.json').read_text())
    from approach_assessment import validate_assessment, render_comparison_radar, render_methodology, render_profile
    validate_assessment(assessment_data, data)
    assessments = {entry['id']:entry for entry in assessment_data['approaches']}
    criteria = assessment_data['criteria']
    css = (ROOT / 'src/comparison.css').read_text() + '\n' + (ROOT / 'src/assessment.css').read_text()
    css += '\n' + (ROOT / 'src/comparison-interactions.css').read_text()
    interactions = (ROOT / 'src/comparison-interactions.js').read_text()
    assets = load_assets()
    ui_library = load_ui_icons()
    column_headers = '<th scope="col" class="pin-heading"><span class="column-title">Compare</span></th>' + ''.join(f'<th scope="col"><span class="column-title">{icon(symbol)}{e(title)}</span><span class="column-help">{e(help_text)}</span></th>' for title,help_text,symbol in COLUMNS)
    rows, dossiers = [], []
    for item in data['approaches']:
        ident = item['id']
        website = item.get('website')
        direct_link = f'<a class="provider-site" href="{e(website["url"])}" target="_blank" rel="noopener noreferrer" aria-label="{e(item["name"])} (official site, opens in a new tab)">{e(item.get("short_name",item["name"]))}{icon("external","external-icon")}</a>' if website else ''
        name_link = direct_link or f'<a href="#provider-{e(ident)}">{e(item.get("short_name",item["name"]))}</a>'
        summary_name = direct_link or f'<strong>{e(item["name"])}</strong>'
        rows.append(f'''<tr data-kind="{e(item['kind'])}" data-approach="{e(ident)}" data-search="{e((item['name']+' '+item['focus']+' '+item['retrieval']+' '+item['storage']).lower())}">
<td class="pin-cell"><label class="pin-label"><input type="checkbox" class="pin-checkbox" id="pin-{e(ident)}" aria-label="Compare {e(item['name'])}" disabled><span aria-hidden="true">Compare</span></label></td>
<th scope="row"><div class="identity-heading">{badge(ident,"row",assets)}<div>{name_link}<small>{e(item['category'])} · {e(assessments[ident]['scope_label'])}</small><a class="approach-details" href="#provider-{e(ident)}">Scores &amp; details <span aria-hidden="true">↓</span></a></div></div></th>
<td data-label="Saved information">{e(item['focus'])}</td><td data-label="Recall method">{e(item['retrieval'])}</td>
<td data-label="Published tests"><span class="evidence-label">{e(item.get('evidence_label') or item['evidence_gap'])}</span></td>
<td data-label="Runs on">{e(item['storage'])}</td></tr>''')
        steps = ''.join(f'<li><span class="step-number">0{n}</span><strong>{e(step[0])}</strong><span>{e(step[1])}</span></li>' for n, step in enumerate(item['flow'], 1))
        claims, historical = '', ''
        for claim in item.get('claims', []):
            rendered = f'''<article class="claim"><div class="claim-top"><span>{e(claim['benchmark'])}</span><b>{e(claim['value'])}</b></div><p>{e(claim['metric'])}</p><p class="small">{e(claim['conditions'])}</p><p class="small">Published by {e(claim['publisher'])}. {link({'url':claim['url'],'title':'Original report (now redirects)' if claim.get('historical') else 'Read the result'})}</p></article>'''
            if claim.get('historical'):
                historical += rendered
            else:
                claims += rendered
        if historical:
            claims += '<details class="historical"><summary>Historical report · mixed/ambiguous metric labeling</summary><p class="small">The original report URL now redirects. Its metric labels conflict; current SMFS results above concern a different product and benchmark.</p>' + historical + '</details>'
        if not claims:
            claims = f'<p class="gap"><strong>No comparable benchmark result shown.</strong> {e(item["evidence_gap"])}</p>'
        sources = ''.join(f'<li>{link(s)}<small>{e(s["publisher"])}</small></li>' for s in item['sources'])
        hermes_note = '' if item['hermes'] == item['mechanism'] else f'<h3>In Hermes</h3><p>{e(item["hermes"])}</p>'
        voice = 'Why use this pattern' if item['kind'] == 'basic' else 'Why choose it'
        dossiers.append(f'''<details class="dossier" id="provider-{e(ident)}"><summary><span class="dossier-identity">{badge(ident,"detail",assets)}<span><small>{e(item['category'])}</small>{summary_name}</span></span><span class="dossier-teaser">{e(item['thesis'])}</span><span class="expand" aria-hidden="true">+</span></summary>
<div class="dossier-body"><p class="eyebrow">{voice}</p><p class="thesis">{e(item['thesis'])}</p>
<p class="approach-context"><strong>Keeps:</strong> {e(item['focus'])} · <strong>Finds it through:</strong> {e(item['retrieval'])} · <strong>Runs on:</strong> {e(item['storage'])}</p>
{render_profile(assessments[ident],criteria,item.get('short_name',item['name']))}
<ol class="flow" aria-label="Conceptual {e(item['name'])} memory flow">{steps}</ol>
<div class="detail-grid"><div><h3>How it works</h3><p>{e(item['mechanism'])}</p></div><div><h3>What you still own</h3><p>{e(item['tradeoff'])}</p>{hermes_note}</div></div>
<details class="citations"><summary>Evidence and sources</summary><h3>Published results</h3>{claims}<h3>Primary sources</h3><ul>{sources}</ul><p class="small"><strong>Test caveat:</strong> {e(item['evidence_note'])}</p><p class="small">{e(item['evidence_gap'])}</p></details>
<a class="back" href="#comparison">↑ Back to comparison</a></div></details>''')
    credits = ''.join(f'<article id="credit-{e(ident)}"><h3>{e(asset["name"])}</h3><p>{link({"url":asset["source_url"],"title":"Original asset"})} · {link({"url":asset["license_url"],"title":asset["license"]})}</p><p>{e(asset["modifications"])}</p><pre>{e(asset["license_notice"])}</pre></article>' for ident,asset in assets.items())
    cohorts = []
    for cohort in data.get('cohorts', []):
        bars = ''.join(f'<div class="bar-row"><span>{e(row["name"])}</span><div class="track"><div class="bar" style="width:{float(row["score"])}%"></div></div><b>{float(row["score"]):.1f}</b></div>' for row in cohort['rows'])
        graphic = f'<div class="bars" role="img" aria-label="{e(cohort["metric_label"])}: {e("; ".join(row["name"]+" "+str(row["score"]) for row in cohort["rows"]))}">{bars}</div>' if cohort['rows'] else '<div class="unscored-flow" aria-label="Conceptual plugin flow, not performance data"><span>Local records</span><b aria-hidden="true">→</b><span>SQLite / FTS5</span><b aria-hidden="true">→</b><span>Recall</span></div>'
        cohorts.append(f'''<article class="cohort" data-cohort-provider="{e(cohort['provider_id'])}"><div class="cohort-identity">{badge(cohort["provider_id"],"chart",assets)}<p class="eyebrow">{e(cohort['publisher'])} · {e(cohort['date'])}</p></div><h3>{e(cohort['title'])}</h3><p>{e(cohort['description'])}</p><p class="metric-label">{e(cohort['metric_label'])}</p>{graphic}<p class="small">{e(cohort['conditions'])}</p><p>{link(cohort['source'], 'Read the plugin source' if not cohort['rows'] else 'Read this publisher’s evaluation')}</p></article>''')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Havesome Memory · Compare agent memory approaches</title><meta name="description" content="Compare basic memory patterns and every documented Hermes memory provider. Each provider’s own case, published benchmark evidence, and limits—without a universal leaderboard."><link rel="canonical" href="https://zacaria.github.io/havesome-memory/"><meta property="og:title" content="Havesome Memory · Choose how your agent remembers"><meta property="og:description" content="Basic patterns, specialized providers, and the evidence behind their claims."><meta name="twitter:card" content="summary"><style>{css}</style></head><body>
<a class="skip" href="#comparison">Skip to comparison</a>
<header><a class="brand" href="index.html">{emblem()} HAVESOME MEMORY</a><nav aria-label="Main navigation"><a href="#comparison">Compare</a><a href="#benchmarks">Benchmarks</a><a href="story.html">Read the story ↗</a></nav></header>
<main><section class="opening" id="memory-introduction" aria-labelledby="memory-title"><div class="hero-copy"><p class="eyebrow"><span class="section-emoji" data-visual="memory" aria-hidden="true">{icon("brain")}</span> INDEPENDENT GUIDE · AGENT MEMORY</p><h1 id="memory-title">You told your AI yesterday. Will it know today?</h1><p class="intro">An AI agent only knows what it is given for the task in front of it. Yesterday’s conversation is not included by default.</p><p class="memory-definition">Memory is how it keeps useful things between conversations and gets them back when they matter.</p><p class="hero-guide">You can do that with plain files or with a memory service. This page compares 13 options: what each keeps, how it finds things again, and what happens when a fact changes.</p><div class="hero-actions"><a class="hero-story" href="story.html"><span class="hero-step-num">1</span> See the problem <small>a short story</small> <span aria-hidden="true">↗</span></a><a class="hero-compare" href="#comparison"><span class="hero-step-num">2</span> Compare the options <span aria-hidden="true">↓</span></a></div></div><figure class="hero-example" aria-labelledby="hero-example-title"><figcaption id="hero-example-title">What memory does</figcaption><ol class="hero-sequence"><li class="hero-day"><span class="hero-step-label">Monday · you</span><p class="bubble you">“Use a 30-second timeout.”</p></li><li class="hero-retention">{retained_art()}<span class="hero-step-label">Saved between conversations</span><p>timeout = 30 s<small>decided Monday, in chat</small></p></li><li class="hero-day"><span class="hero-step-label">Tuesday · you</span><p class="bubble you">“Which timeout should I use?”</p><span class="hero-step-label agent">Agent</span><p class="bubble agent">“30 seconds. You set that on Monday.”</p></li></ol><p class="hero-example-note">Saving it is half the job. If you change it to 60 on Friday, memory has to answer 60 from then on.</p></figure></section>
<section id="comparison" aria-labelledby="comparison-title"><div class="section-heading"><div><p class="eyebrow"><span class="section-emoji" aria-hidden="true">{icon("search")}</span> 01 / COMPARE</p><h2 id="comparison-title">Which approach fits you?</h2></div><span class="review-date">Evidence reviewed {e(data['reviewed'])}</span></div>

<div class="how-to-choose"><h3>Start here: what do you need most?</h3><ul>
<li><strong>Something you can read and edit by hand.</strong> Built-in notes, or files + skills. Both score 3 for portability.</li>
<li><strong>A trail of what changed and where it came from.</strong> Hindsight and Supermemory are the only two scoring 3 for both change history and traceability.</li>
<li><strong>Less to run yourself.</strong> Managed services (Honcho, Mem0, Supermemory, RetainDB, Memori) score 2 for simplicity. Self-hosted Hindsight and OpenViking score 1.</li>
<li><strong>Not sure yet.</strong> Start with built-in notes. They are the simplest, and you can add any other option later.</li></ul>
<p class="small">Scores come from each project’s own documentation. We did not run the tools ourselves.</p></div>
<p class="small tab-help"><strong>Simple building blocks</strong> are do-it-yourself patterns. <strong>Memory add-ons</strong> are ready-made services for <a href="https://hermes-agent.nousresearch.com/" target="_blank" rel="noopener noreferrer">Hermes Agent</a>, an open-source AI agent.</p>
<div class="controls" hidden><div class="filters" role="group" aria-label="Filter approaches"><button type="button" data-filter="all" aria-pressed="true">All approaches</button><button type="button" data-filter="basic" aria-pressed="false">Simple building blocks</button><button type="button" data-filter="provider" aria-pressed="false">Memory add-ons for Hermes</button></div><label>Find an approach <input type="search" id="search" placeholder="Name, mechanism, hosting…"></label></div>
<p id="filter-status" class="small" role="status" aria-live="polite" hidden></p>
<p class="small">Each approach gets six scores from 0 to 3, based on its documentation. <a href="#score-rubric">How scoring works ↓</a></p>
<p id="pin-help" class="small" hidden>Tick “Compare” on a few rows to see them side by side on one chart.</p>
<noscript><p class="small">Selecting and filtering need JavaScript; checkboxes are disabled. Descriptions, static radars, Scores &amp; details and source disclosures remain available.</p></noscript>
<div class="comparison-workspace"><table id="memory-comparison-table" class="descriptive-comparison" role="table" aria-describedby="pin-help"><caption class="table-caption">Names open the official site in a new tab. “Scores &amp; details” opens the full profile.</caption><thead role="rowgroup"><tr class="selection-toolbar" role="row" hidden><th colspan="6" role="cell"><div><strong class="mobile-comparison-title">Memory comparison</strong><span id="pin-status" role="status" aria-live="polite">0 selected</span><button type="button" id="clear-selection" disabled>Clear selection</button><a href="#comparison-end" class="leave-comparison">Skip the table ↓</a></div></th></tr><tr class="comparison-columns" role="row">{column_headers}</tr></thead><tbody id="pinned-rows" role="rowgroup" aria-label="Selected approaches" tabindex="-1" hidden></tbody><tbody id="comparison-rows" role="rowgroup">{''.join(rows)}</tbody></table>{render_comparison_radar(assessment_data, data)}</div><p id="comparison-end" class="scope" tabindex="-1">Four do-it-yourself patterns, eight memory plugins that ship with Hermes, and Memori, installed separately. Hermes keeps its built-in notes on by default, next to one external provider. {link(data['hermes_source'], 'Hermes integration scope')}</p>
{render_methodology(assessment_data, {a['id']: a.get('short_name', a['name']) for a in data['approaches']})}
</section>
<section id="benchmarks"><div class="section-heading"><div><p class="eyebrow"><span class="section-emoji" aria-hidden="true">{icon("chart")}</span> 02 / READ THE TEST, NOT JUST THE NUMBER</p><h2>Same benchmark name, different experiments.</h2></div></div><p class="section-intro">Each provider ran its own tests. Here are their numbers, with the setup and caveats next to them.</p><div class="cohort-grid">{''.join(cohorts)}</div><div class="rule"><strong>Compare like with like.</strong><span>Check the dataset version, history size, system version, answering model, judge model, retrieval budget, speed and cost. If a detail is not published, treat it as unknown. A recall score says nothing about permissions, deletion, reliability or your own workflow.</span></div></section>
<section id="approaches"><div class="section-heading"><div><p class="eyebrow"><span class="section-emoji" aria-hidden="true">{icon("puzzle")}</span> 03 / EACH APPROACH, ON ITS OWN TERMS</p><h2>What is each one trying to solve?</h2></div></div><p class="section-intro">What each one does well, where it falls short, and how information moves through it.</p>{''.join(dossiers)}</section>
<section id="how-memory-works"><p class="eyebrow"><span class="section-emoji" aria-hidden="true">{icon("files")}</span> 04 / THE MECHANISM, IN ONE EXAMPLE</p><h2>Three ways to remember<br>one decision.</h2><p class="section-intro">Monday: “We changed the API timeout to 30 seconds.” Tuesday: “Which timeout should the client use?” Here are three ways to get from one to the other.</p>
<div class="example-grid"><article>{icon("chat","example-icon")}<span class="example-number">01 / KEEP IN CONTEXT</span><h3>Keep the conversation</h3><div class="context-gauge"><span>Earlier messages</span><span class="fact">timeout = 30 seconds</span><span>More conversation</span><span>Today’s question</span></div><p>The fact is right there as long as it stays in the conversation. But the conversation keeps growing, and space runs out.</p><p class="annotation">Catch → space is limited, and a summary can drop the detail.</p></article>
<article>{icon("files","example-icon")}<span class="example-number">02 / WRITE IT DOWN</span><h3>Save a file. Read it back.</h3><div class="example-flow"><span class="fact">timeout = 30 seconds</span><span class="arrow">↓ write</span><span class="file-node">api-decisions.md</span><span class="arrow">↓ find + read</span><span class="context-node">Fact + today’s question</span></div><p>Often a file is enough. The agent needs a habit of writing things down and a way to find the right line later.</p><p class="annotation">Your job → keep the file tidy and tell the agent where to look.</p></article>
<article>{icon("memory","example-icon")}<span class="example-number">03 / USE A MEMORY LAYER</span><h3>Store it. Fetch it. Check it.</h3><div class="example-flow"><span class="fact">timeout = 30 seconds</span><span class="arrow">↓ retain</span><span class="memory-node">Fact · source · project · time</span><span class="arrow">↓ retrieve for this question</span><span class="context-node">Selected fact + question</span></div><p>A memory service might pull out facts, build a profile, organise files or link related things. Each method suits different questions.</p><p class="annotation">Your job → check that what comes back is in scope, current, and backed by a source.</p></article></div>
<p class="small">When the timeout changes again, update the saved note and check which version applies.</p></section>
<section class="story-invitation"><div><p class="eyebrow">WHY IT IS HARD</p><h2>See what breaks<br>when knowledge changes.</h2><p>Follow Morrow Works, a made-up company, through scattered files, conflicting rules, private records and deletion. Then see how five memory systems deal with each problem.</p></div><a class="story-link" href="story.html">Read the story <span aria-hidden="true">↗</span></a></section>
<details class="asset-credits"><summary>Logo &amp; icon sources</summary><p>Logos are used for editorial identification only. Source and license notices are preserved below. These copyright terms do not imply general trademark rights or endorsement.</p>{credits}<article id="credit-lucide"><h3>Lucide interface icons</h3><p>{link({"url":ui_library["website"],"title":"Lucide icon library"})} · {link({"url":ui_library["license_url"],"title":"Pinned ISC / MIT notices"})}</p><p>{e(ui_library["usage"])}</p><pre>{e(ui_library["license_notice"])}</pre></article></details></main><footer><span>HAVESOME MEMORY</span><p>No analytics or accounts. Sources reviewed {e(data['reviewed'])}.</p><a href="#comparison">Back to comparison ↑</a></footer>
<script>{interactions}</script></body></html>'''
