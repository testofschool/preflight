#!/usr/bin/env python3
"""Read-only independent checks of an exported deck against the official template."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from collections import Counter
import hashlib
import json
import posixpath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
NUM = re.compile(r'\d+(?:,\d{3})*(?:\.\d+)?(?:/\d+(?:\.\d+)?)?%?')
URL = re.compile(r'https?://[^\s<>]+')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def bounds(xml):
    if xml is None:
        return None
    return [(E.QName(c).localname, dict(c.attrib)) for c in E.fromstring(xml)]


def nontext_xml(data):
    root = E.fromstring(data)
    for t in root.xpath('//a:t', namespaces=NS):
        t.text = ''
    return E.tostring(root, method='c14n')


def shape_info(root):
    result = {}
    for sp in root.xpath('//p:sp', namespaces=NS):
        cn = sp.find('p:nvSpPr/p:cNvPr', NS)
        if cn is None:
            continue
        xf = sp.find('p:spPr/a:xfrm', NS)
        result[cn.get('id')] = {
            'text': '\n'.join(sp.xpath('.//a:t/text()', namespaces=NS)),
            'xfrm': E.tostring(xf).decode() if xf is not None else None,
            'fonts': sp.xpath('.//a:latin/@typeface | .//a:ea/@typeface | .//a:cs/@typeface', namespaces=NS),
            'sizes': sp.xpath('.//a:rPr/@sz | .//a:defRPr/@sz', namespaces=NS),
        }
    return result


def main():
    pdf = ROOT / 'docs/Preflight_pitch_deck.pdf'
    pptx = ROOT / 'docs/Preflight_pitch_deck.pptx'
    baseline = json.loads((OUT / 'template_manifest.json').read_text())
    with ZipFile(ROOT / baseline['template_path']) as template_zip:
        original_slide_1 = template_zip.read('ppt/slides/slide1.xml')
    if not pdf.exists() or not pptx.exists():
        raise SystemExit('WAITING: both final PDF and PPTX must exist before the independent audit runs.')
    canonical = (ROOT / 'reports/final_v6/CODEX_ONESHOT_preflight_final_v5.md').read_text()
    section = canonical.split('## Track B —', 1)[1].split('## Track C —', 1)[0]
    facts = '\n'.join(line.split('|', 3)[3] for line in section.splitlines()
                      if re.match(r'^\|\s*\d+\s*\|', line))
    allowed_tokens = sorted(set(NUM.findall(facts)))
    text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    (OUT / 'deck_pdf_text.txt').write_text(text)
    pages = text.split('\f')
    if not pages[-1].strip():
        pages.pop()
    native_text = '\n'.join(s['text'] for s in baseline['slides'])
    native_tokens = set(NUM.findall(native_text))
    numeric = []
    for page, content in enumerate(pages, 1):
        url_spans = [(m.start(), m.end()) for m in URL.finditer(content)]
        for m in NUM.finditer(content):
            token = m.group()
            context = content[max(0, m.start()-70):m.end()+90].replace('\n', ' ')
            in_table = token in allowed_tokens
            if any(start <= m.start() < end for start, end in url_spans):
                category = ('v5-table' if in_table else 'EXTRA') + ' URL identifier digits, not a quantity'
            elif re.match(r'\s*Minutes\b', content[m.end():]) and token == '3':
                category = 'EXTRA native-template duration quantity: 3 Minutes; user clarified governing requirement as 3-4 minutes and authorized a new submission video; new-video QA pending'
            elif content[max(0, m.start()-1):m.start()].isalpha() or content[m.end():m.end()+1].isalpha():
                category = ('v5-table' if in_table else 'EXTRA') + ' technical or brand identifier digits; verify context'
            elif in_table:
                category = 'v5-table numeric quantity or model-version token; verify context'
            elif token in native_tokens:
                category = 'EXTRA native-template numeric token; verify same context'
            else:
                category = 'EXTRA literal quantity: not in v5 table or native template text'
            numeric.append({'page': page, 'token': token,
                            'context': context, 'literal_token_in_v5_table': in_table,
                            'class': category})
    with ZipFile(pptx) as z:
        names = set(z.namelist())
        shared = [{'part': k, 'present': k in names,
                   'byte_identical': k in names and sha(z.read(k)) == v}
                  for k, v in baseline['parts'].items()]
        media = [{'part': m['part'], 'present': m['part'] in names,
                  'byte_identical': m['part'] in names and sha(z.read(m['part'])) == m['sha256'],
                  'native_image_text_classification': m['visual_numeric_classification']}
                 for m in baseline['media']]
        slides = sorted([n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)],
                        key=lambda s: int(re.search(r'slide(\d+)', s).group(1)))
        slide_diffs = []
        for old in baseline['slides']:
            part = old['part']
            if part not in names:
                slide_diffs.append({'part': part, 'missing': True})
                continue
            current = shape_info(E.fromstring(z.read(part)))
            for sp in old['shapes']:
                cid = sp['id']
                now = current.get(cid)
                if now is None:
                    slide_diffs.append({'part': part, 'shape': cid, 'removed': True})
                    continue
                changes = {key: {'before': sp[key], 'after': now[key]}
                           for key in ('text', 'xfrm', 'fonts', 'sizes') if sp[key] != now[key]}
                if changes:
                    slide_diffs.append({'part': part, 'shape': cid, 'changes': changes})
        root = E.fromstring(z.read('ppt/presentation.xml'))
        relroot = E.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
        relmap = {r.get('Id'): posixpath.normpath(posixpath.join('ppt', r.get('Target'))) for r in relroot}
        rid_name = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
        displayed = [relmap[s.get(rid_name)] for s in root.find('p:sldIdLst', NS)]
        size = dict(root.find('p:sldSz', NS).attrib)
        first = shape_info(E.fromstring(z.read('ppt/slides/slide1.xml')))
        old_first = next(s for s in baseline['slides'][0]['shapes'] if s['id'] == '54')
        slide_1_nontext_identical = nontext_xml(z.read('ppt/slides/slide1.xml')) == nontext_xml(original_slide_1)
        fonts = set()
        for n in names:
            if n.startswith('ppt/') and n.endswith('.xml'):
                fonts.update(E.fromstring(z.read(n)).xpath('//a:latin/@typeface | //a:ea/@typeface | //a:cs/@typeface', namespaces=NS))
    data = {
        'read_only': True,
        'template_sha256': baseline['sha256'],
        'pptx': {'path': str(pptx), 'sha256': sha(pptx.read_bytes()), 'bytes': pptx.stat().st_size},
        'pdf': {'path': str(pdf), 'sha256': sha(pdf.read_bytes()), 'bytes': pdf.stat().st_size,
                'page_count': len(pages), 'under_5000000_bytes': pdf.stat().st_size <= 5000000},
        'slide_xml_part_count_including_orphans': len(slides),
        'slide_count': len(displayed), 'same_slide_count': len(displayed) == len(baseline['slides']),
        'displayed_slide_parts': displayed,
        'omitted_template_slides': [s['part'] for s in baseline['slides'] if s['part'] not in displayed],
        'slide_size_emu': size, 'same_slide_size': size == baseline['slide_size_emu'],
        'shared_parts': shared, 'all_shared_parts_byte_identical': all(p['byte_identical'] for p in shared),
        'native_media': media, 'all_native_media_byte_identical': all(p['byte_identical'] for p in media),
        'slide_1_shape_54_present': '54' in first,
        'slide_1_shape_54_same_bounds': '54' in first and bounds(first['54']['xfrm']) == bounds(old_first['xfrm']),
        'slide_1_all_nontext_xml_identical': slide_1_nontext_identical,
        'explicit_fonts': sorted(fonts), 'original_shape_differences': slide_diffs,
        'v5_table_numeric_tokens': allowed_tokens,
        'native_template_text_numeric_tokens': sorted(native_tokens),
        'pdf_numeric_occurrences': numeric,
        'numeric_exceptions': [n for n in numeric if n['class'].startswith('EXTRA')],
        'notes_delta_receipt': 'notes_delta_independent.json',
        'pdf_font_glyph_usage_receipt': 'pdf_font_glyph_usage.json',
        'pdf_symbol_fallback': 'LucidaGrande only for 5 U+2192 arrows, pages 5 and 8; body text uses embedded Google Sans Flex families.',
        'duration_resolution': 'User clarified governing range as 3-4 minutes and authorized a new 3:20 submission video; 2:52 is backup, new-video QA pending.',
        'caveats': ['PDF text extraction does not read embedded screenshots or image text.',
                    'Native template image OCR and manual classification are in template_manifest.json.',
                    'Token whitelist membership does not establish claim correctness; inspect contexts.',
                    'Original-shape differences must be classified as intentional content fill or reported formatting changes.',
                    'Visual review of every rendered page is separately required.'],
    }
    (OUT / 'export_audit.json').write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps({k: data[k] for k in ['pdf', 'slide_count', 'same_slide_count', 'same_slide_size',
                                        'all_shared_parts_byte_identical', 'all_native_media_byte_identical',
                                        'slide_1_shape_54_present', 'slide_1_shape_54_same_bounds',
                                        'explicit_fonts', 'numeric_exceptions']}, indent=2))


if __name__ == '__main__':
    main()
