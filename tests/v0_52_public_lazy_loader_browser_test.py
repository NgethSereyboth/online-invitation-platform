#!/usr/bin/env python3
"""Inline Chromium proof that Khmer support is loaded only for documents that need it."""
from __future__ import annotations

import sys
from pathlib import Path

from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
LOADER = (ROOT / "advanced-public-loader-v32.js").read_text(encoding="utf-8")
MOMENT = (ROOT / "vendor/momentkh.js").read_text(encoding="utf-8")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"V0_52_PUBLIC_LAZY_LOADER_SKIPPED_NO_PLAYWRIGHT: {exc}")
        return 0
    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            print(f"V0_52_PUBLIC_LAZY_LOADER_SKIPPED_NO_CHROMIUM: {exc}")
            return 0
        page = browser.new_page()
        page.set_content("<!doctype html><head></head><body></body>")
        result = page.evaluate(
            """async ({loader,moment})=>{
 const appended=[];const original=Element.prototype.append;
 Element.prototype.append=function(...nodes){for(const node of nodes){if(node.tagName==='SCRIPT'){appended.push(node.getAttribute('src')||'');if((node.getAttribute('src')||'').endsWith('vendor/momentkh.js')){node.removeAttribute('src');node.textContent=moment;const answer=original.apply(this,nodes);setTimeout(()=>node.dispatchEvent(new Event('load')),0);return answer}}}return original.apply(this,nodes)};
 const loaderNode=document.createElement('script');loaderNode.textContent=loader;document.head.append(loaderNode);
 const before=typeof window.momentkh;
 await window.EInviteAdvancedPublicLoader.load({languageMode:'en',dateFormat:'gregorian',objects:{}});
 const afterEnglish={moment:typeof window.momentkh,count:appended.filter(x=>x.endsWith('momentkh.js')).length};
 await window.EInviteAdvancedPublicLoader.load({languageMode:'both',dateFormat:'both',fields:{date:'2026-12-27'},objects:{}});
 const khmer=window.momentkh.format(window.momentkh.fromGregorian(2026,12,27,16,0));
 const afterKhmer={moment:typeof window.momentkh,count:appended.filter(x=>x.endsWith('momentkh.js')).length,khmer};
 await window.EInviteAdvancedPublicLoader.load({languageMode:'km',dateFormat:'khmer',objects:{}});
 const afterRepeat={count:appended.filter(x=>x.endsWith('momentkh.js')).length};
 Element.prototype.append=original;return{before,afterEnglish,afterKhmer,afterRepeat};
}""",
            {"loader": LOADER, "moment": MOMENT},
        )
        assert result["before"] == "undefined", result
        assert result["afterEnglish"] == {"moment": "undefined", "count": 0}, result
        assert result["afterKhmer"]["moment"] == "object" and result["afterKhmer"]["count"] == 1, result
        assert any("\u1780" <= char <= "\u17ff" for char in result["afterKhmer"]["khmer"]), result
        assert result["afterRepeat"]["count"] == 1, result
        browser.close()
    print("V0_52_PUBLIC_LAZY_LOADER_BROWSER_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
