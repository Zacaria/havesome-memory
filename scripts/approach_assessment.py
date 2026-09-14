"""Pure, standard-library editorial capability assessment helpers."""

from html import escape
import math
import re
from urllib.parse import urlsplit

AXES = ('retrieval', 'organization', 'change', 'traceability', 'portability', 'simplicity')


def _object(value, path):
    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected an object')
    return value


def _text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{path}: expected nonempty text')
    if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise ValueError(f'{path}: control characters are not allowed')
    return value


def _identifier(value, path):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
        raise ValueError(f'{path}: expected a lowercase hyphenated identifier')
    return value


def _texts(value, path):
    if not isinstance(value, list) or not value:
        raise ValueError(f'{path}: expected a nonempty list')
    for item in value:
        _text(item, path)


def _source(url, path):
    _text(url, path)
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').encode('idna').decode('ascii')
        valid_host = ':' in host or (0 < len(host) <= 253 and all(
            re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', label)
            for label in host.rstrip('.').split('.')))
        valid = (parsed.scheme == 'https' and valid_host and parsed.username is None
                 and parsed.password is None and parsed.port != 0
                 and not any(c.isspace() or ord(c) < 32 for c in url) and '\\' not in url)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f'{path}: expected an absolute HTTPS URL without credentials')


def _criteria(criteria):
    if not isinstance(criteria, list) or len(criteria) != len(AXES):
        raise ValueError('criteria: expected exactly six capability axes')
    indexed = {}
    for criterion in criteria:
        _object(criterion, 'criterion')
        axis = _identifier(criterion.get('id'), 'criterion.id')
        if axis not in AXES or axis in indexed:
            raise ValueError(f'criteria: unexpected or duplicate axis {axis}')
        for key in ('label', 'question'):
            _text(criterion.get(key), f'{axis}.{key}')
        levels = _object(criterion.get('levels'), f'{axis}.levels')
        if set(levels) != {'0', '1', '2', '3'}:
            raise ValueError(f'{axis}.levels: expected string keys 0, 1, 2, 3')
        for anchor in levels.values():
            _text(anchor, f'{axis}.levels')
        indexed[axis] = criterion
    return [indexed[axis] for axis in AXES]


def _assessment(assessment):
    _object(assessment, 'assessment')
    ident = _identifier(assessment.get('id'), 'assessment.id')
    _text(assessment.get('scope'), f'{ident}.scope')
    for key in ('strengths', 'limits'):
        _texts(assessment.get(key), f'{ident}.{key}')
    scores = _object(assessment.get('scores'), f'{ident}.scores')
    if set(scores) != set(AXES):
        raise ValueError(f'{ident}.scores: expected exactly the six capability axes')
    for axis, score in scores.items():
        path = f'{ident}.scores.{axis}'
        _object(score, path)
        if 'value' not in score:
            raise ValueError(f'{path}.value: missing (use explicit null for unknown)')
        value = score['value']
        if value is not None and (type(value) is not int or not 0 <= value <= 3):
            raise ValueError(f'{path}.value: expected integer 0–3 or null, not boolean')
        _text(score.get('rationale'), f'{path}.rationale')
        sources = score.get('sources')
        if not isinstance(sources, list) or (value is not None and not sources):
            raise ValueError(f'{path}.sources: known scores require at least one source')
        for source in sources:
            _source(source, f'{path}.sources')
    return ident


def _ids(records, path):
    if not isinstance(records, list) or len(records) != 13:
        raise ValueError(f'{path}: expected exactly 13 current approaches')
    ids = [_identifier(_object(record, path).get('id'), f'{path}.id') for record in records]
    if len(set(ids)) != len(ids):
        raise ValueError(f'{path}: duplicate approach ids')
    return set(ids)


def _data(data):
    _object(data, 'assessment data')
    _criteria(data.get('criteria'))
    methodology = _object(data.get('methodology'), 'methodology')
    for key in ('title', 'summary', 'scale_note', 'scope_note'):
        _text(methodology.get(key), f'methodology.{key}')
    ids = _ids(data.get('approaches'), 'assessment approaches')
    for assessment in data['approaches']:
        _assessment(assessment)
    return ids


def validate_assessment(data, catalogue):
    """Return None or raise ValueError; no mutation, I/O, fetching, or hardcoded IDs.

    Exactly 13 unique IDs must match catalogue['approaches']. Known scores need
    sources; null may have an empty sources list but still needs a rationale.
    HTTPS syntax is checked; official provenance must be reviewed by the author.
    Optional metadata is allowed. All renderers also validate their own inputs.
    """
    expected = _ids(_object(catalogue, 'catalogue').get('approaches'), 'catalogue approaches')
    actual = _data(data)
    if actual != expected:
        raise ValueError(f'approach ids differ: missing={sorted(expected - actual)}, '
                         f'extra={sorted(actual - expected)}')


def _score_text(value):
    return 'Unknown' if value is None else f'{value}/3'


def _score_key(value):
    return 'unknown' if value is None else str(value)


def _score(value):
    ticks = '' if value is None else ''.join(
        f'<span class="score-tick{" is-filled" if n <= value else ""}"></span>'
        for n in range(1, 4))
    return (f'<span class="capability-score" data-score="{_score_key(value)}">'
            f'<span class="score-ticks" aria-hidden="true">{ticks}</span>'
            f'<span class="score-number">{_score_text(value)}</span></span>')


def render_headers(criteria):
    """Six <th> fragments, always in AXES order; labels and questions are plain text."""
    return ''.join(
        f'<th class="assessment-header" scope="col" data-axis="{c["id"]}">'
        f'<span class="column-title">{escape(c["label"])}</span>'
        f'<span class="column-help">{escape(c["question"])}</span></th>'
        for c in _criteria(criteria))


def render_cells(assessment, criteria):
    """Six <td> fragments linking to the host page's existing provider-ID dossier."""
    ident = _assessment(assessment)
    cells = []
    for criterion in _criteria(criteria):
        axis, label = criterion['id'], criterion['label']
        value = assessment['scores'][axis]['value']
        cells.append(
            f'<td class="assessment-cell" data-axis="{axis}" data-label="{escape(label)}" '
            f'data-score="{_score_key(value)}"><a href="#provider-{ident}" '
            f'aria-label="{escape(label)}: {_score_text(value)}. Read capability rationale">'
            f'{_score(value)}</a></td>')
    return ''.join(cells)


def render_methodology(data):
    """One native details element. Validate catalogue membership separately first."""
    _data(data)
    method = data['methodology']
    parts = [f'<details id="score-rubric" class="assessment-rubric">'
             f'<summary>{escape(method["title"])}</summary>',
             '<p>These are editorial, ordinal capability feature profiles, not a performance ranking '
             'and not our own benchmarks. Scores describe documented features within each stated '
             'scope, not measured effectiveness. Higher levels are not necessarily a better fit.</p>',
             f'<p>{escape(method["summary"])}</p><p>{escape(method["scale_note"])}</p>',
             '<p>All profiles use the same six axes and 0–3 scale. Levels are ordered categories, '
             'not equal measured intervals. We calculate no total, average, or overall rank. '
             'Radar area is not a total and must not be used to compare overall quality.</p>',
             '<p>Unknown means insufficient documentation in the assessed scope; it is not zero '
             'and does not establish absence. Zero is an explicit assessment against the axis’s '
             'level-0 anchor. Unknown chart points are omitted; any unknown removes the filled '
             'shape and all connecting edges.</p>',
             f'<p><strong>Source scope:</strong> {escape(method["scope_note"])}</p>',
             '<p>Read each scope before comparing: a general approach, a provider platform, and '
             'its agent integration are not interchangeable. The linked official sources support '
             'the editorial rationale; the scores are not vendor-reported test results.</p>',
             '<h3>Per-axis level anchors</h3><div class="assessment-anchors">']
    for criterion in _criteria(data['criteria']):
        parts.append(f'<section><h4>{escape(criterion["label"])}</h4>'
                     f'<p>{escape(criterion["question"])}</p><dl>')
        for level in range(4):
            parts.append(f'<dt>{level}</dt><dd>{escape(criterion["levels"][str(level)])}</dd>')
        parts.append('</dl></section>')
    parts.append('</div><h3>Assessed scopes</h3><ul class="assessment-scopes">')
    for assessment in data['approaches']:
        ident = assessment['id']
        parts.append(f'<li><a href="#provider-{ident}">{escape(ident)}</a>: '
                     f'{escape(assessment["scope"])}</li>')
    return ''.join(parts) + '</ul></details>'


def _point(index, radius):
    angle = -math.pi / 2 + index * math.tau / len(AXES)
    return f'{130 + radius * math.cos(angle):.2f}', f'{130 + radius * math.sin(angle):.2f}'


def _radar(assessment, criteria):
    ident = assessment['id']
    values = [assessment['scores'][axis]['value'] for axis in AXES]
    summary = '; '.join(f'{c["label"]}: {_score_text(value)}' for c, value in zip(criteria, values))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" class="radar-chart" viewBox="0 0 260 260" '
             f'role="img" aria-labelledby="radar-title-{ident}" '
             f'aria-describedby="radar-desc-{ident} radar-caption-{ident}">'
             f'<title id="radar-title-{ident}">Editorial capability profile: {escape(summary)}</title>'
             f'<desc id="radar-desc-{ident}">Clockwise from the top: {escape(", ".join(c["label"] for c in criteria))}. '
             'Center is 0; rings are 1, 2, 3. Numbered spokes match the criterion list. '
             'Unknown values have no plotted point.</desc>']
    for level in range(1, 4):
        points = ' '.join(','.join(_point(i, level * 22)) for i in range(6))
        parts.append(f'<polygon class="radar-grid" points="{points}" fill="none" />')
    for i in range(6):
        x, y = _point(i, 66)
        parts.append(f'<line class="radar-axis" x1="130" y1="130" x2="{x}" y2="{y}" />')
    for level in range(4):
        parts.append(f'<text class="radar-scale" x="136" y="{134 - level * 22}">{level}</text>')
    # Never bridge missing values, even along otherwise known adjacent axes.
    if all(value is not None for value in values):
        points = ' '.join(','.join(_point(i, value * 22)) for i, value in enumerate(values))
        parts.append(f'<polygon class="radar-shape" points="{points}" />')
    for i, (criterion, value) in enumerate(zip(criteria, values)):
        if value is not None:
            x, y = _point(i, value * 22)
            parts.append(f'<circle class="radar-point" data-axis="{criterion["id"]}" '
                         f'data-score="{value}" cx="{x}" cy="{y}" r="3.5">'
                         f'<title>{escape(criterion["label"])}: {_score_text(value)}</title></circle>')
        x, y = _point(i, 99)
        # Compact numeric key avoids tiny/shrunken or clipped long labels at 320px.
        parts.append(f'<text class="radar-label" x="{x}" y="{y}" text-anchor="middle" '
                     f'dominant-baseline="middle">{i + 1}: {"?" if value is None else _score_text(value)}</text>')
    return ''.join(parts) + '</svg>'


def render_comparison_radar(data, catalogue):
    """One overlay chart; reuse the full renderer's exact grid and point geometry."""
    import json
    import xml.etree.ElementTree as ET
    validate_assessment(data, catalogue)
    criteria = _criteria(data['criteria'])
    names = {a['id']: a.get('short_name', a['name']) for a in catalogue['approaches']}
    colors = ('#8ebcff', '#ffaf83', '#a8df9a', '#d8b3ff', '#ff92bb', '#6ce0d5',
              '#f6d56f', '#c5d2e8', '#f49379', '#92c969', '#c9a0dc', '#77cce8', '#e0c3a0')
    parts = ['<aside id="shared-radar-panel" hidden aria-label="Selected capability profiles">'
             '<details id="shared-radar-disclosure"><summary>Compare profiles <span id="series-count">0 selected</span></summary>'
             '<div class="shared-radar-body"><p id="radar-empty">Select rows to overlay their capability profiles. No approach is selected by default.</p>'
             '<div class="shared-chart-display">'
             '<svg xmlns="http://www.w3.org/2000/svg" id="shared-radar" viewBox="20 20 220 220" role="group" aria-labelledby="shared-radar-title">'
             '<title id="shared-radar-title">Selected editorial capability profiles. Center 0; rings 1, 2, 3.</title>']
    legend = []
    for n, assessment in enumerate(data['approaches']):
        ident = assessment['id']
        # Parse only our own validated renderer output, never third-party SVG.
        root = ET.fromstring(_radar(assessment, criteria).replace(' xmlns="http://www.w3.org/2000/svg"', ''))
        if n == 0:
            parts.extend(ET.tostring(el, encoding='unicode') for el in root
                         if el.get('class') in ('radar-grid', 'radar-axis', 'radar-scale'))
        values = {axis: assessment['scores'][axis]['value'] for axis in AXES}
        color = colors[n]
        dash = ('none', '7 3', '2 3', '9 3 2 3')[n % 4]
        parts.append(f'<g class="comparison-series" data-series="{ident}" data-name="{escape(names[ident])}" '
                     f'data-values="{escape(json.dumps(values))}" style="--series-color:{color};--series-dash:{dash}" hidden="hidden">')
        parts.extend(ET.tostring(el, encoding='unicode') for el in root
                     if el.get('class') in ('radar-shape', 'radar-point'))
        known = next((el for el in root if el.get('class') == 'radar-point'), None)
        if known is not None:
            parts.append(f'<text class="series-letter" x="{float(known.attrib["cx"])+7:.2f}" y="{float(known.attrib["cy"])-7:.2f}">{chr(65+n)}</text>')
        parts.append('</g>')
        partial = ' · partial' if any(v is None for v in values.values()) else ''
        legend.append(f'<li data-legend="{ident}" style="--series-color:{color}" hidden>'
                      f'<button type="button" data-highlight="{ident}" aria-pressed="false">'
                      f'<span class="series-swatch" aria-hidden="true">{chr(65+n)}</span>{escape(names[ident])}{partial}</button>'
                      f'<button type="button" data-remove="{ident}" aria-label="Unpin {escape(names[ident])}">×</button></li>')
    for n, criterion in enumerate(criteria):
        x, y = _point(n, 91)
        parts.append(f'<g class="radar-axis-target" role="button" tabindex="0" data-axis="{criterion["id"]}" '
                     f'data-description="{escape(criterion["question"])}" aria-label="{escape(criterion["label"])}">'
                     f'<circle cx="{x}" cy="{y}" r="13"/><text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle">{n+1}</text></g>')
    parts.append('</svg><ul class="series-legend" aria-label="Selected series; highlight or unpin">'+''.join(legend)+'</ul></div>'
                 '<p id="series-highlight" role="status">All selected profiles</p><button type="button" id="reset-series">Clear highlight</button>'
                 '<div class="axis-buttons" role="group" aria-label="Six capability axes">')
    for n, c in enumerate(criteria, 1):
        parts.append(f'<button type="button" class="axis-button" data-axis="{c["id"]}" '
                     f'data-description="{escape(c["question"])}" aria-label="{escape(c["label"])}">{n}. {escape(c["label"])}</button>')
    parts.append('</div><p class="shared-radar-note">Editorial 0–3, not benchmarks. Unknown ≠ zero. Scroll the legend for all selected names; focus or tap one to highlight its profile. Explore axes 1–6. Letters identify series, not ranks. Arrow keys scroll the score popup. Incomplete profiles show known points only, never a connecting shape. Area is not an overall score.</p></div></details></aside>')
    return ''.join(parts)


def render_profile(assessment, criteria):
    """Render a quick trade-off profile with a compact keyed radar and sourced detail."""
    ident = _assessment(assessment)
    criteria = _criteria(criteria)
    legend = ''.join(
        f'<li data-axis="{c["id"]}" data-score="{_score_key(assessment["scores"][c["id"]]["value"])}">'
        f'<span class="radar-key">{n}</span><span>{escape(c["label"])}</span>'
        f'<strong>{_score_text(assessment["scores"][c["id"]]["value"])}</strong></li>'
        for n,c in enumerate(criteria,1))
    tradeoffs = '<div class="assessment-tradeoffs">' + ''.join(
        f'<div><h4>{title}</h4><ul>' + ''.join(f'<li>{escape(text)}</li>' for text in assessment[key]) + '</ul></div>'
        for key,title in (('strengths','Upsides'),('limits','Limits'))) + '</div>'
    parts = [f'<section class="assessment-profile" data-assessment-id="{ident}" '
             f'aria-labelledby="assessment-heading-{ident}">'
             f'<h3 id="assessment-heading-{ident}">Editorial capability profile</h3>'
             f'<p class="assessment-scope"><strong>Assessed scope:</strong> {escape(assessment["scope"])}</p>'
             '<p class="assessment-note">Documented capability levels, not benchmark results or a ranking. '
             '<a href="#score-rubric">Read the rubric and level anchors</a>.</p>'
             '<div class="assessment-layout"><figure class="assessment-radar">',
             _radar(assessment, criteria),
             '<ol class="radar-legend" aria-label="Radar criteria and scores">'+legend+'</ol>',
             f'<figcaption id="radar-caption-{ident}">Same six axes, same 0–3 scale. Spoke numbers '
             'match this legend; ? means Unknown, not zero. Missing points disable the connecting '
             'shape. Radar area is not a total or an overall quality score.</figcaption>'
             '</figure>'+tradeoffs+'</div>'
             '<details class="assessment-rationale"><summary>Why these scores? Criteria and sources</summary>'
             '<ol class="assessment-criteria">']
    for criterion in criteria:
        axis = criterion['id']
        score = assessment['scores'][axis]
        parts.append(f'<li data-axis="{axis}" data-score="{_score_key(score["value"])}">'
                     f'<h4>{escape(criterion["label"])} {_score(score["value"])}</h4>'
                     f'<p class="assessment-question">{escape(criterion["question"])}</p>'
                     f'<p>{escape(score["rationale"])}</p><p class="assessment-sources">')
        if score['sources']:
            parts.append('Sources: ' + '; '.join(
                f'<a href="{escape(url)}" rel="noreferrer">{n}. {escape(urlsplit(url).netloc)}</a>'
                for n, url in enumerate(score['sources'], 1)))
        else:
            parts.append('No supporting source established for this axis in the assessed scope.')
        parts.append('</p></li>')
    return ''.join(parts) + '</ol></details></section>'
