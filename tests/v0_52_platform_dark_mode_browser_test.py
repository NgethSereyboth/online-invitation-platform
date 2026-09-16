#!/usr/bin/env python3
"""Inline Chromium contrast and modal-mode coverage for the V0.52 platform drawer."""
from __future__ import annotations

import html
import sys
from pathlib import Path

from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]


def page_html(theme: str) -> str:
    modern = html.escape((ROOT / "modern-ui.css").read_text(encoding="utf-8"), quote=False)
    future = html.escape((ROOT / "future-studio-v52.css").read_text(encoding="utf-8"), quote=False)
    loader = (ROOT / "future-studio-loader-v52.js").read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    return f"""<!doctype html><html data-theme=\"{theme}\"><head><meta charset=\"utf-8\">
<style>{modern}</style><style>{future}</style>
<script>window.EInviteLifecycle={{add(){{}}}};window.EInviteEditorBridge={{getState:()=>({{id:'inv-dark'}})}};
window.EInviteFutureUIV052={{notify(){{}}}};
window.EInviteUnifiedEditorV34={{unmount(){{}},async mount(root){{
 const card=document.createElement('section');card.className='v52-card';
 const heading=document.createElement('h3');heading.textContent='Event operations';
 const text=document.createElement('p');text.textContent='Readable platform content';
 const field=document.createElement('label');field.className='v52-field';field.textContent='Event name';
 const input=document.createElement('input');input.value='Khmer wedding';field.append(input);
 const table=document.createElement('table');table.className='v52-table';
 const row=document.createElement('tr'),th=document.createElement('th'),td=document.createElement('td');th.textContent='Status';td.textContent='Ready';row.append(th,td);table.append(row);
 const empty=document.createElement('div');empty.className='v52-empty';empty.textContent='No queued jobs';
 card.append(heading,text,field,table,empty);root.append(card);
}}}};</script>
<script data-einvite-future=\"future-ui-v0_52.js\" data-loaded=\"1\"></script>
<script data-einvite-future=\"unified-editor-v34.js\" data-loaded=\"1\"></script>
</head><body><main id=\"background\"><button id=\"open\">Open platform</button></main>
<script>{loader}</script></body></html>"""


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"V0_52_PLATFORM_DARK_MODE_SKIPPED_NO_PLAYWRIGHT: {exc}")
        return 0

    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            print(f"V0_52_PLATFORM_DARK_MODE_SKIPPED_NO_CHROMIUM: {exc}")
            return 0

        for theme in ("light", "dark"):
            for width, height in ((390, 844), (820, 900), (1280, 900), (1440, 900)):
                page = browser.new_page(viewport={"width": width, "height": height})
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.set_content(page_html(theme), wait_until="load")
                page.locator("#open").focus()
                page.evaluate("()=>window.EInviteFutureStudioV52.open('editor',{opener:document.querySelector('#open')})")
                page.wait_for_selector(".v52-card")
                result = page.evaluate(
                    r"""()=>{
 const shell=document.querySelector('.v52-shell'),bg=document.querySelector('#background'),input=document.querySelector('.v52-field input');
 const rgba=value=>{const v=String(value),m=v.match(/[\d.]+/g)||[];if(v.startsWith('color(srgb'))return[Number(m[0])*255,Number(m[1])*255,Number(m[2])*255,m[3]==null?1:Number(m[3])];return[Number(m[0]||0),Number(m[1]||0),Number(m[2]||0),m[3]==null?1:Number(m[3])]};
 const blend=(top,bottom)=>{const a=top[3]+bottom[3]*(1-top[3]);if(!a)return[0,0,0,0];return[(top[0]*top[3]+bottom[0]*bottom[3]*(1-top[3]))/a,(top[1]*top[3]+bottom[1]*bottom[3]*(1-top[3]))/a,(top[2]*top[3]+bottom[2]*bottom[3]*(1-top[3]))/a,a]};
 const effectiveBg=e=>{const stack=[];for(let n=e;n;n=n.parentElement)stack.push(rgba(getComputedStyle(n).backgroundColor));let out=[255,255,255,1];for(let i=stack.length-1;i>=0;i--)out=blend(stack[i],out);return out};
 const lum=rgb=>{const c=rgb.slice(0,3).map(v=>v/255).map(v=>v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4));return .2126*c[0]+.7152*c[1]+.0722*c[2]};
 const contrast=(fg,bg)=>{const a=lum(rgba(fg)),b=lum(bg);return(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
 const sample=selector=>{const e=document.querySelector(selector),st=getComputedStyle(e),b=effectiveBg(e);return{selector,color:st.color,background:b,ratio:contrast(st.color,b)}};
 input.focus();const focus=getComputedStyle(input);
 return{role:shell.getAttribute('role'),modal:shell.getAttribute('aria-modal'),backgroundInert:bg.inert,scrollWidth:document.documentElement.scrollWidth,innerWidth,
 shellBg:getComputedStyle(shell).backgroundColor,samples:['.v52-heading h2','.v52-heading p','.v52-tab:not([aria-selected=true])','.v52-card h3','.v52-card p','.v52-field','.v52-field input','.v52-table th','.v52-table td','.v52-empty','.v52-foot'].map(sample),focusOutline:focus.outlineStyle,focusWidth:parseFloat(focus.outlineWidth)||0};
}"""
                )
                assert not errors, (theme, width, errors)
                assert result["scrollWidth"] <= result["innerWidth"] + 1, (theme, width, result)
                if width <= 820:
                    assert result["role"] == "dialog" and result["modal"] == "true" and result["backgroundInert"], (theme, width, result)
                else:
                    assert result["role"] == "complementary" and result["modal"] == "false" and not result["backgroundInert"], (theme, width, result)
                if theme == "dark":
                    assert result["shellBg"] != "rgb(255, 255, 255)", (width, result)
                for sample in result["samples"]:
                    assert sample["ratio"] >= 4.5, (theme, width, sample, result)
                assert result["focusOutline"] != "none" and result["focusWidth"] >= 2, (theme, width, result)
                page.evaluate("()=>window.EInviteFutureStudioV52.close()")
                assert page.locator("#open").evaluate("e=>document.activeElement===e")
                page.close()
        browser.close()

    print("V0_52_PLATFORM_DARK_MODE_BROWSER_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
