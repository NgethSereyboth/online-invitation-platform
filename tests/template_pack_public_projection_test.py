#!/usr/bin/env python3
"""TP-5.2 regression: the guest page applies each stored object's typography model.

``installResponsive`` collects the elements it fits with
``querySelectorAll(selector).forEach(observe)``. ``observe(source, model)`` takes a
caller-supplied model as its second parameter, so ``forEach`` handed it the array
INDEX: every element after the first cached a number as ``__typographyModel``, and
``renderedElementModel`` returns that cache first. The fit pass then applied a blank
model, so each object fell back to ``font-size 32 / text-auto-fit none`` — 33 of the
flagship's 34 text objects rendered unfitted and were cut by their boxes at 375 px.

This test publishes one pack template and asserts, object by object, that the live
element carries the model the stored document asked for and that the auto-fit pass
actually ran.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from browser_runtime import launch_chromium  # noqa: E402
from v14_test_utils import app_server  # noqa: E402
from template_pack_edit_export_test import built_document  # noqa: E402

TEMPLATE = "wd-royal-maroon-gold"

PUBLISH_JS = """
async ([id, model]) => {
  const csrf = decodeURIComponent((document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]+)/) || [])[1] || '');
  const response = await fetch('/api/invitations/' + id + '/publish', {
    method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
    body: JSON.stringify({document: model, expectedRevision: null}),
  });
  const body = await response.json().catch(() => ({}));
  return {ok: response.ok, status: response.status, body};
}
"""

CREATE_JS = """
async model => {
  const csrf = decodeURIComponent((document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]+)/) || [])[1] || '');
  const response = await fetch('/api/invitations', {
    method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
    body: JSON.stringify({slug: model.templateId, document: model}),
  });
  if (!response.ok) throw Error(await response.text());
  return response.json();
}
"""

# Reads the live element for one object id. Kept to primitives so the assertion
# message can print exactly what the page did.
PROBE_JS = """
id => {
  const node = document.querySelector(`.published-text[data-object-id="${CSS.escape(id)}"]`);
  if (!node) return {missing: true};
  const model = node.__typographyModel;
  return {
    styleId: node.dataset.textStyleId,
    fontSize: node.dataset.fontSize,
    autoFit: node.dataset.textAutoFit,
    computed: node.dataset.textComputedFontSize || null,
    modelType: model === null ? 'null' : typeof model,
    modelStyleId: model && typeof model === 'object' ? model.styleId : null,
    modelFontSize: model && typeof model === 'object' ? model.fontSize : null,
    modelAutoFit: model && typeof model === 'object' ? model.textAutoFit : null,
  };
}
"""


PAYLOAD_JS = """
async () => {
  const slug = (document.querySelector('meta[name="einvite-invitation-slug"]') || {}).content || '';
  const response = await fetch('/api/public/' + encodeURIComponent(slug));
  if (!response.ok) throw Error('public payload ' + response.status);
  return (await response.json()).document || {};
}
"""


def stored_text_objects(document: dict) -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    for page in document.get("designPages") or []:
        if page.get("enabled") is False:
            continue
        for object_id, object_model in (page.get("objects") or {}).items():
            if object_model.get("type") == "text":
                rows.append((object_id, object_model))
    return rows


def test_public_page_applies_stored_typography_models() -> None:
    from playwright.sync_api import sync_playwright

    document = built_document(TEMPLATE)
    assert len(stored_text_objects(document)) >= 20, "the flagship template should ship text objects"

    with app_server() as (_process, base, _data):
        with sync_playwright() as play:
            browser = launch_chromium(play)
            context = browser.new_context(viewport={"width": 375, "height": 900})
            page = context.new_page()
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("projection-regression@example.com")
            page.locator("#password").fill("Strong-projection-regression-123")
            page.locator("#registerConfirmPassword").fill("Strong-projection-regression-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            created = page.evaluate(CREATE_JS, document)
            published = page.evaluate(PUBLISH_JS, [created["id"], document])
            assert published["ok"], published
            url = published["body"]["url"]
            page.goto(base + url if url.startswith("/") else url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector(".published-text", timeout=20000)
            page.wait_for_timeout(1500)

            # Compare against what the guest page itself was served, not the built
            # module: the server normalises the document (ids, style references) and
            # that normalised payload is the contract the renderer must honour.
            payload = page.evaluate(PAYLOAD_JS)
            expected = stored_text_objects(payload)
            assert len(expected) >= 20, f"the published payload should carry text objects, found {len(expected)}"

            problems: list[str] = []
            fitted = 0
            for object_id, object_model in expected:
                live = page.evaluate(PROBE_JS, object_id)
                if live.get("missing"):
                    problems.append(f"{object_id}: not rendered")
                    continue
                wanted_style = object_model.get("textStyleId") or ""
                wanted_size = float(object_model.get("fontSize") or 0)
                wanted_fit = object_model.get("textAutoFit") or "none"
                if live["modelType"] != "object":
                    problems.append(f"{object_id}: typography model cached as {live['modelType']} ({live['modelStyleId']!r})")
                # An object the resolver could not place renders as 32 / none with a
                # blank style id — the exact signature of the projection failure.
                if not live["styleId"] and wanted_style:
                    problems.append(f"{object_id}: style {live['styleId']!r} != stored {wanted_style!r}")
                if abs(float(live["fontSize"] or 0) - wanted_size) > 0.01:
                    problems.append(f"{object_id}: font-size {live['fontSize']!r} != stored {wanted_size!r}")
                if live["autoFit"] != wanted_fit:
                    problems.append(f"{object_id}: auto-fit {live['autoFit']!r} != stored {wanted_fit!r}")
                if wanted_fit == "fit":
                    fitted += 1
                    if live["computed"] is None:
                        problems.append(f"{object_id}: stored auto-fit but the fit pass never ran")
                    elif float(live["computed"]) > wanted_size + 0.01:
                        problems.append(f"{object_id}: fitted size {live['computed']} above the stored {wanted_size}")

            browser.close()

    assert not problems, "public page did not apply the stored typography models:\n" + "\n".join(problems[:20])
    assert fitted == sum(1 for _, model in expected if (model.get("textAutoFit") or "none") == "fit")


if __name__ == "__main__":
    test_public_page_applies_stored_typography_models()
    print("TEMPLATE_PACK_PUBLIC_PROJECTION_PASSED")
