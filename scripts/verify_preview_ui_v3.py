#!/usr/bin/env python3
"""Verify Preview v3 UI without requesting image or video generation.

Reuses the unchanged front-build-spec first_viewport.py JS_COUNT measurement
that produced reports/first_viewport_d_primary/summary.json. This script checks
only declared D-010 budgets; fonts and comprehension remain UNMEASURED.
Off mode submits one real preflight solely to inspect the required disabled copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

BUSY_COPY = "Preview is busy right now — try again in a minute. The risk check still works."
MEASUREMENT_SOURCE = "/Users/felix/.codex/skills/front-build-spec/scripts/first_viewport.py"
MEASUREMENT_SOURCE_SHA256 = 'c36f15ea2960b2f837cf069205ac50e5a27d5eb706a4058011f8824be0fbadaf'
MEASUREMENT_JS_SHA256 = 'f16c6279542b50d3f79c9174996391a77f13a4c4993aad4e5cd68ba3169afc1f'
JS_COUNT = r"""() => {
  const H = innerHeight, W = innerWidth;
  const faded = e => { for (let n = e; n && n.nodeType === 1; n = n.parentElement) if (parseFloat(getComputedStyle(n).opacity) < 0.01) return true; return false; };
  const vis = e => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < H && r.right > 0 && r.left < W && cs.visibility !== 'hidden' && cs.display !== 'none' && !faded(e); };
  const sel = 'h1,h2,h3,h4,p,a,button,img,canvas,svg,video,picture,nav,form,select,input,textarea,li,blockquote,figure,table,span,div,small,label,strong,em';
  const ownText = e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  const counted = []; const out = [];
  document.querySelectorAll(sel).forEach(e => {
    if (!vis(e)) return;
    if (/^(span|div|small|label|strong|em)$/i.test(e.tagName) && !ownText(e)) return; // generic wrappers count only when they carry their own text
    if (e.closest('header,nav,form,li,figure,table,picture') && e.closest('header,nav,form,li,figure,table,picture') !== e && counted.some(c => c.contains(e))) return;
    if (counted.some(c => c.contains(e))) return;
    // an <a> that wraps only an svg+text is one object; an svg inside a counted <a> is skipped by the contains test above
    counted.push(e);
    out.push((e.tagName.toLowerCase()) + (e.id ? '#' + e.id : (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ')[0] : '')));
  });
  const colors = new Map(); const fams = new Set(); let text = '';
  document.querySelectorAll('body *').forEach(e => {
    if (!vis(e)) return;
    const cs = getComputedStyle(e);
    [cs.color, cs.backgroundColor].forEach(c => { const m = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/); if (!m) return; if (m[4] !== undefined && parseFloat(m[4]) === 0) return; const k = m[1]+','+m[2]+','+m[3]; colors.set(k, (colors.get(k)||0)+1); });
  });
  // Text nodes preserve mixed inline copy (including direct body text). Range rects
  // exclude off-screen or overflow-clipped parts of an otherwise visible element.
  const clippedRectVisible = (rect, e) => {
    let left = Math.max(0, rect.left), right = Math.min(W, rect.right);
    let top = Math.max(0, rect.top), bottom = Math.min(H, rect.bottom);
    for (let n = e; n; n = n.parentElement) {
      const cs = getComputedStyle(n), r = n.getBoundingClientRect();
      if (cs.display === 'none' || cs.contentVisibility === 'hidden') return false;
      if (/^(hidden|clip|scroll|auto)$/.test(cs.overflowX)) {
        left = Math.max(left, r.left); right = Math.min(right, r.right);
      }
      if (/^(hidden|clip|scroll|auto)$/.test(cs.overflowY)) {
        top = Math.max(top, r.top); bottom = Math.min(bottom, r.bottom);
      }
      const inset = cs.clipPath.match(/^inset\(([^)]+)\)$/);
      if (inset) {
        const values = inset[1].split(/\s+round\s+/)[0].trim().split(/\s+/);
        if (values.length <= 4 && values.every(v => /^-?[\d.]+(?:px|%)$/.test(v))) {
          const [a, b = a, c = a, d = b] = values;
          const pixels = (v, size) => parseFloat(v) * (v.endsWith('%') ? size / 100 : 1);
          left = Math.max(left, r.left + pixels(d, r.width));
          right = Math.min(right, r.right - pixels(b, r.width));
          top = Math.max(top, r.top + pixels(a, r.height));
          bottom = Math.min(bottom, r.bottom - pixels(c, r.height));
        }
      }
    }
    return right > left && bottom > top;
  };
  const blockOf = e => {
    for (let n = e; n; n = n.parentElement) {
      if (/^(block|flow-root|flex|grid|table-cell|list-item)$/.test(getComputedStyle(n).display)) return n;
    }
    return document.body;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node, previousBlock = null, previousRect = null;
  while ((node = walker.nextNode())) {
    const e = node.parentElement;
    if (!e || !node.textContent || e.closest('script,style,template,noscript') || faded(e)) continue;
    const cs = getComputedStyle(e);
    if (cs.visibility !== 'visible' || cs.color === 'transparent' || /rgba\([^)]*,\s*0\)$/.test(cs.color)) continue;
    const range = document.createRange(); range.selectNodeContents(node);
    if (![...range.getClientRects()].some(r => clippedRectVisible(r, e))) continue;
    let visible = '', firstRect = null, lastRect = null;
    for (let i = 0; i < node.length; i++) {
      range.setStart(node, i); range.setEnd(node, i + 1);
      const rects = [...range.getClientRects()].filter(r => clippedRectVisible(r, e));
      if (rects.length) {
        visible += node.textContent[i];
        firstRect ||= rects[0]; lastRect = rects[rects.length - 1];
      } else visible += ' '; // do not join letters across an invisible span
    }
    if (!visible) continue;
    const block = blockOf(e);
    const separated = previousRect && firstRect &&
      firstRect.left - previousRect.right > Math.max(1, parseFloat(cs.fontSize) * 0.2);
    if ((previousBlock && block !== previousBlock) || separated) text += ' ';
    text += visible;
    previousBlock = block;
    previousRect = lastRect;
    if (visible.trim()) fams.add(cs.fontFamily.split(',')[0].replace(/["']/g,'').trim());
  }
  return {elements: out, colors: [...colors.keys()], families: [...fams], text: text.replace(/\s+/g,' ')};
}"""

def now_kst() -> str:
    return datetime.now(ZoneInfo('Asia/Seoul')).isoformat()


def save(path: Path, receipt: dict) -> None:
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def summary_results(measured: dict) -> list[list]:
    objects, colors, families = (len(measured[key]) for key in ('elements', 'colors', 'families'))
    return [
        ['V1', 'PASS' if objects <= 18 else 'FAIL', f'{objects} visible objects; declared budget 18'],
        ['V2', 'PASS' if colors <= 12 else 'FAIL', f'{colors} rgb-merged UI colours; declared budget 12'],
        ['V3', 'UNMEASURED', f'{families} first font families; no family budget declared'],
        ['V4', 'UNMEASURED', 'No comprehension strings or human comprehension test declared'],
    ]


def verify(args) -> dict:
    expected = args.expected_preview == 'on'
    receipt = {
        'url': args.url, 'started_at_kst': now_kst(), 'expected_preview': expected,
        'viewport': [1440, 900], 'budgets': {'elements': 18, 'colors': 12, 'families': None},
        'budgets_declared': ['elements', 'colors'], 'words': {'what': None, 'who': None, 'next': None},
        'method': {
            'source': MEASUREMENT_SOURCE, 'source_sha256_at_copy': MEASUREMENT_SOURCE_SHA256,
            'js_count_sha256': hashlib.sha256(JS_COUNT.encode()).hexdigest(),
            'js_count_unchanged': hashlib.sha256(JS_COUNT.encode()).hexdigest() == MEASUREMENT_JS_SHA256,
            'baseline_receipt': 'reports/first_viewport_d_primary/summary.json',
            'baseline_objects': 18, 'baseline_colors': 7,
            'objects': 'Visible content objects intersecting the viewport at rest. Count descendants once per containing object; nav/form each count once. Exclude opacity <0.01, hidden, and zero-size elements.',
            'colors': 'Distinct computed text/background RGB in the viewport; merge alpha variants of the same RGB; omit transparent and canvas pixels.',
            'cta': '#check-button getBoundingClientRect().bottom at scrollY=0, budget <=900 px',
            'overflow': 'document.documentElement.scrollWidth <= innerWidth at scrollY=0',
            'readiness': 'Original 2500 ms post-commit wait plus confirmed status and document.fonts.ready before measurement',
            'browser_args': ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
            'preview_policy': 'No preview action; fail if any POST /preview is observed. Off mode submits one real POST /preflight.',
        },
        'network': [], 'request_failures': [], 'page_errors': [], 'screenshots': [], 'overflow_checks': [],
        'passed': False,
    }
    report_path = args.report_dir / 'summary.json'

    def write():
        save(report_path, receipt)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=receipt['method']['browser_args'])
        receipt['browser_version'] = browser.version
        page = browser.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=1,
                                locale='en-US', timezone_id='Asia/Seoul')
        page.set_default_timeout(6000)
        page.on('pageerror', lambda error: receipt['page_errors'].append(str(error)))
        page.on('requestfailed', lambda request: receipt['request_failures'].append({
            'method': request.method, 'path': urlsplit(request.url).path, 'failure': request.failure}))
        page.on('response', lambda response: receipt['network'].append({
            'method': response.request.method, 'path': urlsplit(response.url).path, 'http_status': response.status}))

        def load(path=''):
            response = page.goto(args.url + path, wait_until='commit', timeout=30000)
            if response is None or response.status != 200:
                raise RuntimeError(f'Page {path or "/"} did not return HTTP 200')
            page.wait_for_timeout(2500)
            page.wait_for_function('window.preflightStatus !== undefined', timeout=25000)
            status = page.evaluate('window.preflightStatus')
            page.evaluate('document.fonts.ready')
            if status.get('preview') is not expected or status.get('mode') != 'cloud':
                raise RuntimeError(f'Expected cloud mode preview={expected}; observed {status.get("mode")}, preview={status.get("preview")}')
            return {key: status.get(key) for key in (
                'mode', 'cloud_run', 'firestore', 'gemini', 'adk', 'postcheck', 'preview', 'agent_platform_session')}

        def screenshot_and_overflow(state):
            for width, height in ((1440, 900), (390, 844)):
                page.set_viewport_size({'width': width, 'height': height})
                page.evaluate('scrollTo(0,0)')
                page.wait_for_timeout(150)
                geometry = page.evaluate('''() => ({inner_width:innerWidth, scroll_width:document.documentElement.scrollWidth,
                    scroll_height:document.documentElement.scrollHeight, scroll_y:scrollY,
                    no_horizontal_overflow:document.documentElement.scrollWidth <= innerWidth})''')
                receipt['overflow_checks'].append({'state': state, 'viewport': [width, height], **geometry})
                path = args.report_dir / f'{state}_{width}x{height}.png'
                page.screenshot(path=str(path), full_page=False)
                receipt['screenshots'].append(str(path))
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.evaluate('scrollTo(0,0)')
            write()

        try:
            receipt['status'] = load()
            page.evaluate('scrollTo(0,0)')
            receipt['measured'] = page.evaluate(JS_COUNT)
            receipt['objects'] = len(receipt['measured']['elements'])
            receipt['colors'] = len(receipt['measured']['colors'])
            receipt['results'] = summary_results(receipt['measured'])
            receipt['cta_bottom_px'] = page.locator('#check-button').evaluate('e => e.getBoundingClientRect().bottom')
            receipt['resting_preview_controls'] = page.locator('.preview-button:visible, .preview-original:visible').count()
            screenshot_and_overflow('first_viewport')
            if not expected:
                page.locator('#prompt').fill('a spoon and a laptop')
                with page.expect_response(lambda response: urlsplit(response.url).path == '/preflight'
                                          and response.request.method == 'POST', timeout=60000) as pending:
                    page.locator('#check-button').click()
                response = pending.value
                receipt['off_mode_check'] = {'preflight_http_status': response.status}
                page.locator('.results-panel[aria-busy="false"]').wait_for(state='visible')
                page.locator('.preview-button').wait_for(state='visible')
                preview = page.locator('.preview-button')
                receipt['off_mode_check'].update({
                    'preview_disabled': preview.is_disabled(), 'preview_title': preview.get_attribute('title'),
                    'required_copy': BUSY_COPY,
                    'copy_matches': preview.get_attribute('title') == BUSY_COPY,
                    'obsolete_region_copy_present': 'Preview unavailable in this region' in page.locator('body').inner_html(),
                })
                screenshot_and_overflow('after_check')
            receipt['architecture_status'] = load('/architecture')
            component = page.locator('#component-list li').filter(has_text='Image preview (Gemini image model)')
            receipt['architecture_image_preview'] = component.locator('.connection-status').inner_text().strip()
            screenshot_and_overflow('architecture')
            expected_badge = 'Active' if expected else 'Not active'
            off = receipt.get('off_mode_check', {})
            receipt['preview_http_requests'] = sum(row['method'] == 'POST' and row['path'] == '/preview' for row in receipt['network'])
            receipt['preflight_http_requests'] = sum(row['method'] == 'POST' and row['path'] == '/preflight' for row in receipt['network'])
            receipt['passed'] = all([
                receipt['method']['js_count_unchanged'], receipt['objects'] <= 18, receipt['colors'] <= 12,
                receipt['cta_bottom_px'] <= 900, receipt['resting_preview_controls'] == 0,
                all(row['no_horizontal_overflow'] for row in receipt['overflow_checks']),
                receipt['architecture_image_preview'] == expected_badge,
                expected or (off.get('preflight_http_status') == 200 and off.get('preview_disabled')
                             and off.get('copy_matches') and not off.get('obsolete_region_copy_present')),
                receipt['preview_http_requests'] == 0, receipt['preflight_http_requests'] == (0 if expected else 1),
                not receipt['request_failures'], not receipt['page_errors'],
                all(row['http_status'] < 400 for row in receipt['network']),
            ])
        except Exception as error:
            receipt['error'] = f'{type(error).__name__}: {error}'
            receipt['passed'] = False
        finally:
            browser.close()
            receipt['ended_at_kst'] = now_kst()
            write()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True, help='Accepted candidate or promoted HTTPS URL')
    parser.add_argument('--expected-preview', choices=('on', 'off'), required=True)
    parser.add_argument('--report-dir', type=Path, default=Path('reports/preview_v3/ui'))
    parser.add_argument('--allow-http', action='store_true', help='Explicit local development only')
    args = parser.parse_args()
    args.url = args.url.rstrip('/')
    if urlsplit(args.url).scheme != 'https' and not args.allow_http:
        parser.error('The live URL must use HTTPS')
    args.report_dir = args.report_dir.resolve()
    args.report_dir.mkdir(parents=True, exist_ok=False)
    receipt = verify(args)
    print(json.dumps({key: receipt.get(key) for key in ('passed', 'objects', 'colors', 'cta_bottom_px', 'preview_http_requests', 'error')}, ensure_ascii=False))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
