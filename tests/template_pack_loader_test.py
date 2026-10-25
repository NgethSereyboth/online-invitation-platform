#!/usr/bin/env python3
"""TP-1.3: the template-pack loader fetches on demand, caches, and fails cleanly.

Runs against the real test server. The loader must not be part of any bundle, so
the test injects it the same way the gallery does.
"""
from __future__ import annotations

import pytest

from browser_runtime import launch_chromium

LOADER = "/template-pack-loader.js"


def test_pack_loader_is_lazy_and_cached():
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))
            requests: list[str] = []
            page.on("request", lambda request: requests.append(request.url))
            page.goto(base + "/templates.html", wait_until="domcontentloaded", timeout=30000)

            # Nothing from the pack is requested before the gallery asks for it.
            assert not [url for url in requests if "/assets/template-pack/" in url]

            loaded = page.evaluate(
                """async (source) => {
                    if (!window.EInviteTemplatePack) {
                        await new Promise((resolve, reject) => {
                            const script = document.createElement('script');
                            script.src = source;
                            script.onload = resolve;
                            script.onerror = () => reject(new Error('loader failed'));
                            document.head.append(script);
                        });
                    }
                    const pack = window.EInviteTemplatePack;
                    const first = pack.loadCatalog();
                    const second = pack.loadCatalog();
                    const catalog = await first;
                    const sameCatalog = first === second;
                    const one = pack.loadTemplate('wd-royal-maroon-gold');
                    const oneAgain = pack.loadTemplate('wd-royal-maroon-gold');
                    const template = await one;
                    const sameDocument = one === oneAgain;
                    let message = '';
                    try {
                        await pack.loadTemplate('not-a-template');
                    } catch (error) {
                        message = error.message;
                    }
                    let traversal = '';
                    try {
                        await pack.loadTemplate('../catalog');
                    } catch (error) {
                        traversal = error.message;
                    }
                    const shapes = catalog.templates.map(item => ({
                        id: item.id, category: item.category, canvas: item.canvas,
                        pages: item.pages, thumb: item.thumb, built: item.built,
                        nameEn: item.name.en, nameKm: item.name.km,
                    }));
                    return {
                        count: catalog.count,
                        sameCatalog,
                        sameDocument,
                        message,
                        traversal,
                        pageCount: template.document.designPages.length,
                        canvas: template.document.posterCanvas,
                        firstShape: shapes[0],
                        categories: [...new Set(shapes.map(item => item.category))].sort(),
                        loadedIds: pack.loaded,
                    };
                }""",
                LOADER,
            )

            assert loaded["count"] == 36
            assert loaded["sameCatalog"] is True, "the catalogue promise must be cached"
            assert loaded["sameDocument"] is True, "a fetched template must be cached"
            assert loaded["message"] == "Could not load this template. Try again."
            assert loaded["traversal"] == "Could not load this template. Try again."
            assert loaded["pageCount"] == 2
            assert loaded["canvas"] == {"width": 1000, "height": 1414}
            assert loaded["categories"] == ["birthday", "business", "ceremony", "greeting", "wedding"]
            assert loaded["firstShape"] == {
                "id": "wd-royal-maroon-gold",
                "category": "wedding",
                "canvas": "a5p",
                "pages": 2,
                "thumb": "/assets/template-pack/thumbs/wd-royal-maroon-gold.webp",
                "built": "/assets/template-pack/built/wd-royal-maroon-gold.js",
                "nameEn": "Royal Maroon & Gold",
                "nameKm": loaded["firstShape"]["nameKm"],
            }
            assert loaded["loadedIds"] == ["wd-royal-maroon-gold"], loaded["loadedIds"]

            fetched = [url for url in requests if "/assets/template-pack/" in url]
            assert any(url.endswith("/catalog.js") for url in fetched), fetched
            assert any(url.endswith("/built/wd-royal-maroon-gold.js") for url in fetched), fetched
            # One catalogue request and one request per distinct id — the cache
            # prevented repeats. `not-a-template` is a well-formed id, so it makes
            # exactly one (404) request and then reports the error state; the path
            # traversal string never reaches the network at all.
            assert len([url for url in fetched if url.endswith("/catalog.js")]) == 1, fetched
            assert len([url for url in fetched if "/built/wd-royal-maroon-gold.js" in url]) == 1, fetched
            assert not [url for url in fetched if "catalog.js" in url.rsplit("/", 1)[-1] and "/built/" in url], fetched

            page.close()
            browser.close()
    assert not errors, errors
