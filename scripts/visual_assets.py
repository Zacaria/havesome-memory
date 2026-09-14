"""Small embedded identities and original teaching illustrations. No remote assets."""
from html import escape
from pathlib import Path
import json
import re
import base64
import hashlib
import struct
import zlib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)

# Original, deliberately simple concept drawings—not provider trademarks.
ICONS = {
    'brain': '<path d="M16 7c-3-6-10-3-9 2-6 1-6 9-2 11-1 6 6 10 11 5V7Zm0 0c3-6 10-3 9 2 6 1 6 9 2 11 1 6-6 10-11 5"/><path d="M7 9c0 3 2 4 4 4M5 20c2-2 4-2 6-1M25 9c0 3-2 4-4 4M27 20c-2-2-4-2-6-1M16 12l-3 4m3 5 3-4"/>',
    'chart': '<path d="M4 4v24h25M9 24v-8h4v8M17 24V6h4v18M25 24V12h4v12"/>',
    'puzzle': '<path d="M4 6h9c-3 8 9 8 6 0h9v9c-8-3-8 9 0 6v7h-9c3-8-9-8-6 0H4v-7c8 3 8-9 0-6z"/>',
    'notes': '<path d="M6 4h11l5 5v18H6z"/><path d="M17 4v6h5M10 15h8M10 20h5"/><path d="M3 8v22h15"/>',
    'files': '<path d="M3 9h10l3 4h13v14H3z"/><path d="M7 9V5h17v8M11 18h10M11 22h6"/>',
    'compact': '<path d="M5 5h22M5 10h22M9 22h14M9 27h14M13 14l3 4 3-4"/>',
    'search': '<circle cx="15" cy="14" r="8"/><path d="m21 20 7 8M9 15l5-5 6 4"/><circle cx="9" cy="15" r="1"/><circle cx="14" cy="10" r="1"/>',
    'prism': '<path d="m16 3 13 8-4 15H7L3 11zM3 11h26M16 3 7 26l18 0zM16 3l9 23M3 11l13 18 13-18"/>',
    'chat': '<path d="M4 5h24v17H13l-7 6v-6H4zM10 11h12M10 16h8"/>',
    'memory': '<rect x="8" y="6" width="18" height="22" rx="2"/><path d="M4 23V3h18M12 12h10M12 17h10M12 22h6"/>',
    'retrieve': '<path d="M9 7H4v5M4 11a12 12 0 1 1 0 9"/><path d="m12 17 4 4 8-9"/>',
}
PATTERNS = {'builtin-memory-files':'notes', 'files-and-skills':'files', 'compaction':'compact', 'vector-rag':'search', 'holographic':'prism'}
INITIALS = {'hindsight':'H', 'honcho':'H', 'mem0':'m0', 'openviking':'OV', 'supermemory':'S', 'byterover':'BR', 'retaindb':'R', 'memori':'M'}


def icon(name, css='concept-icon'):
    return f'<svg class="{css}" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'


def safe_svg(source, prefix):
    """Fail closed; namespace local paint references for repeated inline logos."""
    if '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper():
        raise ValueError('SVG declarations are not permitted')
    root = ET.fromstring(source)
    tags = {'svg','g','path','circle','ellipse','rect','line','polyline','polygon','defs','clipPath','mask','linearGradient','radialGradient','stop','title','desc'}
    attrs = {'viewBox','width','height','x','y','x1','y1','x2','y2','cx','cy','r','rx','ry','d','points','fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','fill-rule','clip-rule','transform','opacity','fill-opacity','stroke-opacity','id','clip-path','mask','offset','stop-color','stop-opacity','gradientUnits','gradientTransform','fx','fy','spreadMethod','maskUnits','maskContentUnits','clipPathUnits','version','preserveAspectRatio'}
    if root.tag.rsplit('}',1)[-1] != 'svg' or 'viewBox' not in root.attrib:
        raise ValueError('Expected a self-contained SVG with a viewBox')
    ids = {node.attrib['id'] for node in root.iter() if 'id' in node.attrib}
    if len(ids) != sum('id' in node.attrib for node in root.iter()):
        raise ValueError('Duplicate source SVG IDs')
    for node in root.iter():
        if node.tag.rsplit('}',1)[-1] not in tags:
            raise ValueError('Forbidden SVG element')
        for key,value in list(node.attrib.items()):
            if key not in attrs or any(token in value.lower() for token in ('javascript:', 'data:', 'http:', 'https:')):
                raise ValueError('Forbidden SVG attribute or value')
            if key == 'id':
                node.set(key,prefix+'-'+value)
            elif 'url(' in value:
                match = re.fullmatch(r'url\(#([\w.-]+)\)',value)
                if not match or match.group(1) not in ids:
                    raise ValueError('Only defined local paint references are allowed')
                node.set(key,'url(#'+prefix+'-'+match.group(1)+')')
    root.set('class','provider-glyph')
    root.set('aria-hidden','true')
    root.set('focusable','false')
    root.attrib.pop('width',None)
    root.attrib.pop('height',None)
    return ET.tostring(root,encoding='unicode')


def raster_data(asset):
    """Accept only the exact hash-pinned, bounded, static RGBA PNG asset."""
    raw = base64.b64decode(asset['png_base64'], validate=True)
    if len(raw) > 100_000 or hashlib.sha256(raw).hexdigest() != asset['asset_sha256']:
        raise ValueError('PNG size or checksum mismatch')
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Invalid PNG signature')
    position, chunks = 8, []
    while position < len(raw):
        length = int.from_bytes(raw[position:position+4], 'big')
        kind = raw[position+4:position+8]
        payload = raw[position+8:position+8+length]
        checksum = raw[position+8+length:position+12+length]
        if len(checksum) != 4 or zlib.crc32(kind+payload) != int.from_bytes(checksum,'big'):
            raise ValueError('Invalid PNG chunk')
        if kind not in {b'IHDR', b'IDAT', b'IEND'}:
            raise ValueError('Only static PNG image chunks are allowed')
        chunks.append(kind)
        if kind == b'IHDR':
            if length != 13 or len(chunks) != 1:
                raise ValueError('Invalid PNG header')
            width,height,depth,color,compression,filtering,interlace = struct.unpack('>IIBBBBB',payload)
            if not (0 < width <= 512 and 0 < height <= 512 and depth == 8 and color == 6 and (compression,filtering,interlace) == (0,0,0)):
                raise ValueError('Only bounded RGBA PNGs are allowed')
            if (width,height) != (asset['width'],asset['height']):
                raise ValueError('PNG dimensions differ from manifest')
        position += 12+length
        if kind == b'IEND' and (length or position != len(raw)):
            raise ValueError('PNG has trailing data')
    if not chunks or chunks[0] != b'IHDR' or chunks[-1] != b'IEND' or b'IDAT' not in chunks:
        raise ValueError('Incomplete PNG')
    return 'data:image/png;base64,'+asset['png_base64']


def badge(ident, placement, assets):
    if ident in assets:
        if assets[ident]['format'] == 'png':
            asset = assets[ident]
            art = f'<img class="provider-glyph" src="{raster_data(asset)}" width="{asset["width"]}" height="{asset["height"]}" alt="">'
        else:
            art = safe_svg(assets[ident]['svg'], f'{placement}-{ident}')
        kind = 'provider-logo'
        title = assets[ident]['name']+' logo'
    elif ident in PATTERNS:
        art = icon(PATTERNS[ident])
        kind = 'concept-mark'
        title = 'Concept illustration, not a provider logo'
    else:
        art = '<span class="initial-mark">'+escape(INITIALS[ident])+'</span>'
        kind = 'name-mark'
        title = 'Name marker, not an official logo'
    return f'<span class="identity-badge {kind} identity-{ident}" data-identity="{ident}" title="{escape(title,quote=True)}" aria-hidden="true">{art}</span>'


def load_assets():
    return json.loads((ROOT/'src/provider-logos.json').read_text())['logos']


def emblem():
    return '<svg class="memory-emblem" viewBox="0 0 40 40" fill="none" aria-hidden="true" focusable="false"><path d="M7 8h23v25H7z" fill="#8ebcff" transform="rotate(-9 18 20)"/><path d="M11 5h20l5 6v23H11z" fill="#ffaf83"/><path d="M29 5v8h7M17 18h12M17 24h8" stroke="#0a1930" stroke-width="2"/><circle cx="7" cy="6" r="3" fill="#edf1fa"/></svg>'


def retained_art():
    return '<svg class="retained-art" data-art="retained-decision" viewBox="0 0 132 80" fill="none" aria-hidden="true" focusable="false"><path d="M17 14h64v51H17z" stroke="#8ebcff" stroke-width="1.5" transform="rotate(-8 49 40)"/><path d="m40 9 51 5 8 12-5 48-60-6z" fill="#ffaf83"/><path d="m81 14-1 14 17 1M46 36l31 3M44 46l23 3M43 56l29 3" stroke="#0a1930" stroke-width="2" stroke-linecap="round"/><path d="m111 8 2 7 7 2-7 2-2 7-2-7-7-2 7-2z" fill="#8ebcff"/><path d="m10 69 4-4m-5-4 5 1m0 13 4-2" stroke="#8ebcff" stroke-width="1.5"/></svg>'
