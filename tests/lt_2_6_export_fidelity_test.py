"""LT-2.6 — Khmer export fidelity: PNG 1x/2x/3x and PDF against the editor.

The fixture is the deterministic sheet from `docs/qa/khmer-text-sheet/`; its
hash is pinned in `expected.sha256`.  The test runs the real editor, exports
through `EInviteExportQuality`, checks that the Khmer glyphs come from the
bundled custom font (CDP platform-font introspection), that the SVG embeds the
font faces as data URLs, and that the rasterized PDF embeds the Khmer face and
matches the editor inside the stated tolerances.
"""
from __future__ import annotations

import base64
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT / 'docs' / 'qa' / 'khmer-text-sheet'))

from build_sheet import digests, document, pick_phrases, read_expected  # noqa: E402
from PIL import Image, ImageChops, ImageStat  # noqa: E402

EXPORT = """async (scale) => {
  await document.fonts.ready;
  const result = await EInviteExportQuality.export.png(scale);
  const bytes = new Uint8Array(await result.blob.arrayBuffer());
  let binary = '';
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return {width: result.width, height: result.height, base64: btoa(binary)};
}"""

PLATFORM_FONTS = """async () => {
  const node = document.querySelector('.object[data-id="sheet"] .rt-run');
  return {text: node?.textContent || '', font: node ? getComputedStyle(node).fontFamily : '',
          check: node ? document.fonts.check(`${getComputedStyle(node).fontWeight} ${getComputedStyle(node).fontSize} "EInvite Noto Sans Khmer"`, node.textContent) : false};
}"""

INSET = 16


def _artboard(image: Image.Image, size: tuple[int, int] | None = None) -> Image.Image:
    if size and image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image.convert('RGB').crop((INSET, INSET, image.width - INSET, image.height - INSET))


def _text_box(image: Image.Image, threshold: int = 170) -> list[int]:
    rgb = image.convert('RGB')
    mask = Image.new('L', rgb.size, 0)
    pixels, mask_pixels = rgb.load(), mask.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            r, g, b = pixels[x, y]
            if (r + g + b) / 3 < threshold:
                mask_pixels[x, y] = 255
    return list(mask.getbbox() or ())


def _compare(editor: Image.Image, exported: Image.Image) -> dict:
    if exported.size != editor.size:
        exported = exported.resize(editor.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(editor.convert('RGB'), exported.convert('RGB'))
    mae = sum(ImageStat.Stat(diff).mean) / 3
    histogram = diff.convert('L').histogram()
    total = editor.width * editor.height
    return {
        'mae': mae,
        'changed_over_8': sum(histogram[8:]) / total,
        'changed_over_32': sum(histogram[32:]) / total,
    }


def _pdf_fonts(path: Path) -> list[str]:
    text = subprocess.run(['pdffonts', str(path)], capture_output=True, text=True).stdout
    return [line for line in text.splitlines() if line.strip() and not line.startswith(('name', '---'))]


def _write_png(payload: dict, path: Path) -> Image.Image:
    path.write_bytes(base64.b64decode(payload['base64']))
    return Image.open(path)


def test_khmer_export_fidelity() -> None:
    sync_playwright = pytest.importorskip('playwright.sync_api')
    from browser_runtime import dismiss_editor_onboarding, launch_chromium
    from playwright.sync_api import sync_playwright as playwright_context
    from v14_test_utils import app_server

    for tool in ('pdftoppm', 'pdffonts', 'pdftotext'):
        if not subprocess.run(['which', tool], capture_output=True).stdout:
            pytest.skip(f'{tool} unavailable')

    tolerance = read_expected()['tolerance']
    phrases = pick_phrases()
    phrase_hash, fixture_hash = digests(phrases, document(phrases))
    expected = read_expected()
    assert phrase_hash == expected['phrases_sha256'], 'Khmer sheet phrases drifted; regenerate expected.sha256'
    assert fixture_hash == expected['fixture_sha256'], 'Khmer sheet fixture drifted; regenerate expected.sha256'

    errors: list[str] = []
    metrics: dict = {}
    with tempfile.TemporaryDirectory(prefix='lt26-') as temp:
        out = Path(temp)
        with app_server() as (_process, base, _data):
            with playwright_context() as playwright:
                try:
                    browser = launch_chromium(playwright)
                except Exception as exc:  # pragma: no cover - environment dependent
                    pytest.skip(f'Chromium unavailable: {exc}')
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                page.goto(base + '/dashboard.html', wait_until='domcontentloaded', timeout=30000)
                page.locator('#authRegisterTab').click()
                page.locator('#email').fill('lt-2-6-export@example.com')
                page.locator('#password').fill('Strong-lt-2-6-export-123')
                page.locator('#registerConfirmPassword').fill('Strong-lt-2-6-export-123')
                page.locator('#loginBtn').click()
                page.wait_for_selector('#dashboardView:not([hidden])', timeout=20000)
                created = page.evaluate(
                    """async model => {
                        const response = await fetch('/api/invitations', {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({slug: model.slug, document: model})
                        });
                        if (!response.ok) throw Error(await response.text());
                        return response.json();
                    }""",
                    document(phrases),
                )
                page.goto(base + f"/invitations/{created['id']}/editor", wait_until='domcontentloaded', timeout=30000)
                page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
                dismiss_editor_onboarding(page)
                page.wait_for_selector('.object[data-id="sheet"]', timeout=20000)
                page.wait_for_timeout(900)
                page.evaluate("() => EInviteEditorBridge.select([])")
                page.mouse.move(2, 2)
                page.add_style_tag(content=(
                    'html body #stage#stage{background:#fff8f2!important;border-radius:0!important;'
                    'box-shadow:none!important}.canvas-viewport:after{display:none!important}'
                ))
                page.wait_for_timeout(400)

                platform = page.evaluate(PLATFORM_FONTS)
                assert platform['check'] is True, platform
                cdp = context.new_cdp_session(page)
                cdp.send('DOM.enable')
                cdp.send('CSS.enable')
                root = cdp.send('DOM.getDocument')['root']['nodeId']
                node_id = cdp.send('DOM.querySelector', {'nodeId': root, 'selector': '.object[data-id="sheet"] .rt-run'})['nodeId']
                assert node_id, 'Khmer run node not found'
                fonts = cdp.send('CSS.getPlatformFontsForNode', {'nodeId': node_id})['fonts']
                assert fonts, 'no platform fonts reported for the Khmer run'
                assert any(font['isCustomFont'] and 'Khmer' in font['familyName'] and font['glyphCount'] > 0 for font in fonts), fonts

                stage = page.locator('#stage')
                box = stage.bounding_box()
                assert box and round(box['width']) == 420 and round(box['height']) == 640, box
                stage.screenshot(path=str(out / 'editor.png'), animations='disabled')
                editor_full = Image.open(out / 'editor.png')
                editor = _artboard(editor_full)
                assert editor.size == (388, 608), editor.size
                editor_text = _text_box(editor)

                svg = page.evaluate("async () => (await EInviteExportQuality.export.svg()).svg")
                assert svg.count('@font-face') >= 3, svg.count('@font-face')
                assert 'EInvite Noto Sans Khmer' in svg
                assert 'url("http' not in svg and 'url(http' not in svg
                assert 'data:' in svg

                # The visible 1x button must produce a real 420x640 download.
                page.evaluate("() => EInviteExportQuality.open('export')")
                page.wait_for_selector('[data-export-png="1"]', timeout=10000)
                assert page.locator('[data-export-png="1"]').inner_text() == '1×'
                assert page.locator('[data-export-png="2"]').inner_text() == '2×'
                assert page.locator('[data-export-png="3"]').inner_text() == '3×'
                with page.expect_download(timeout=30000) as download_info:
                    page.locator('[data-export-png="1"]').click()
                download = Path(download_info.value.path())
                button_image = Image.open(download)
                assert button_image.size == (420, 640), button_image.size
                page.evaluate("() => document.getElementById('v24QualityDialog')?.close()")

                for scale in (1, 2, 3):
                    payload = page.evaluate(EXPORT, scale)
                    exported = _write_png(payload, out / f'export-{scale}x.png')
                    result = _compare(editor, _artboard(exported, editor_full.size))
                    metrics[f'png_{scale}x'] = {key: round(value, 4) for key, value in result.items()}
                    if scale == 1:
                        assert result['mae'] <= tolerance['png_1x_mae'], result
                        assert result['changed_over_8'] <= tolerance['png_1x_changed_over_8'], result
                        assert _text_box(_artboard(exported, editor_full.size)) == editor_text
                    else:
                        assert result['mae'] <= tolerance['png_scaled_mae'], (scale, result)
                        assert result['changed_over_8'] <= tolerance['png_scaled_changed_over_8'], (scale, result)

                with context.expect_page(timeout=30000) as popup_info:
                    page.evaluate("() => EInviteExportQuality.export.printAll()")
                popup = popup_info.value
                popup.wait_for_load_state('load', timeout=30000)
                popup.evaluate("async () => { await document.fonts.ready; }")
                popup.wait_for_timeout(500)
                pdf_path = out / 'export.pdf'
                popup.pdf(path=str(pdf_path), prefer_css_page_size=True,
                          margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'}, print_background=True)
                assert pdf_path.stat().st_size > 1000
                info = subprocess.run(['pdfinfo', str(pdf_path)], capture_output=True, text=True).stdout
                assert re.search(r'^Pages:\s+1$', info, re.M), info
                fonts = _pdf_fonts(pdf_path)
                assert any('Khmer' in line for line in fonts), fonts
                assert all(' yes yes yes ' in line for line in fonts), fonts
                text = subprocess.run(['pdftotext', '-layout', str(pdf_path), '-'], capture_output=True, text=True).stdout
                compact = re.sub(r'\s+', '', text)
                assert all(re.sub(r'\s+', '', phrase) in compact for phrase in phrases), text
                subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-r', '96', '-png', str(pdf_path), str(out / 'pdf')], check=True)
                pdf_image = _artboard(Image.open(out / 'pdf-1.png'), editor_full.size)
                result = _compare(editor, pdf_image)
                metrics['pdf'] = {key: round(value, 4) for key, value in result.items()}
                assert result['mae'] <= tolerance['pdf_mae'], result
                assert result['changed_over_8'] <= tolerance['pdf_changed_over_8'], result
                pdf_text = _text_box(pdf_image)
                assert len(pdf_text) == 4 and all(abs(a - b) <= tolerance['pdf_text_box_px'] for a, b in zip(pdf_text, editor_text)), (pdf_text, editor_text)

                assert not errors, errors
                print('LT-2.6 metrics', metrics)
                context.close()
                browser.close()


if __name__ == '__main__':
    test_khmer_export_fidelity()
    print('LT_2_6_KHMER_EXPORT_FIDELITY_PASSED')
