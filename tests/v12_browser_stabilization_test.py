#!/usr/bin/env python3
"""Chromium checks for V12 first-use UI, overlays, language, media and mobile layout."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from inline_editor_runtime_test import build_inline_editor

ROOT = Path(__file__).resolve().parents[1]
LOCAL_STORAGE_STUB = """
const __makeStorage=()=>{const m=new Map();return{
 getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),clear:()=>m.clear()
}};
Object.defineProperty(window,'localStorage',{value:__makeStorage()});
Object.defineProperty(window,'sessionStorage',{value:__makeStorage()});
"""
PUBLIC_DOC = {
    "schemaVersion": 10,
    "languageMode": "both",
    "fields": {"names": "Invitation A", "namesKm": "លិខិតអញ្ជើញ ក", "date": "2027-03-01", "venue": "Phnom Penh"},
    "objects": {}, "designPages": [], "sectionOrder": ["wishes"],
    "settings": {"rsvpEnabled": False, "wishesEnabled": True, "openingEnabled": False, "musicSource": "none", "musicEnabled": False},
}


def inline_public_html():
    html = (ROOT / "public.html").read_text(encoding="utf-8")
    html = (html.replace("__INVITATION_SLUG__", "browser-a")
            .replace("__INVITATION_TITLE__", "Invitation A")
            .replace("__INVITATION_DESCRIPTION__", "Invitation")
            .replace("__INVITATION_OG_IMAGE__", "social.png")
            .replace("__INVITATION_OG_TYPE__", "image/png")
            .replace("__INVITATION_PUBLIC_URL__", "browser-a"))
    html = re.sub(
        r'<link rel="stylesheet" href="([^"]+)">',
        lambda m: "<style>" + (ROOT / m.group(1).lstrip("/")).read_text(encoding="utf-8") + "</style>",
        html,
    )
    html = re.sub(
        r'<script src="([^"]+)"></script>',
        lambda m: "<script>" + (ROOT / m.group(1).lstrip("/")).read_text(encoding="utf-8") + "</script>",
        html,
    )
    html = html.replace('__INVITATION_SLUG__', 'browser-a')
    payload = json.dumps({"invitationId": "invite-a", "publicationId": "pub-a", "version": 1, "document": PUBLIC_DOC, "guest": None}, ensure_ascii=False)
    fetch_stub = LOCAL_STORAGE_STUB + "window.fetch=async function(url){if(String(url).includes('/api/public/browser-a'))return new Response(" + json.dumps(payload) + ",{status:200,headers:{'Content-Type':'application/json'}});return new Response('{}',{status:200,headers:{'Content-Type':'application/json'}})};"
    return html.replace("</head>", "<script>" + fetch_stub + "</script></head>")


def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return skipped('V12_BROWSER_STABILIZATION',exc)
    with sync_playwright() as p:
        try: browser = launch_chromium(p)
        except Exception as exc:
            return skipped('V12_BROWSER_STABILIZATION',exc)
        context = browser.new_context(viewport={"width": 1440, "height": 900})

        print('V12_BROWSER_STEP dashboard', flush=True)
        # Dashboard empty-state contrast in light, dark and system modes.
        dashboard = context.new_page(); dashboard_errors=[]; dashboard.on("pageerror", lambda e: dashboard_errors.append(str(e)))
        dashboard_html = (
            "<!doctype html><html><head><style>" + (ROOT / "tokens.css").read_text(encoding="utf-8") + "</style><style>" +
            (ROOT / "theme-hardening.css").read_text(encoding="utf-8") + "</style><style>" +
            (ROOT / "dashboard-empty-state.css").read_text(encoding="utf-8") +
            "</style></head><body><div id='inviteGrid'></div><button id='newBtn'></button><script>" +
            (ROOT / "dashboard-empty-state.js").read_text(encoding="utf-8") + "</script></body></html>"
        )
        dashboard.set_content(dashboard_html, wait_until="load"); dashboard.wait_for_selector(".dashboard-empty")
        for theme in ("dark", "light"):
            dashboard.evaluate("theme=>document.documentElement.dataset.theme=theme", theme)
            colors=dashboard.locator(".dashboard-empty h2").evaluate("el=>({c:getComputedStyle(el).color,b:getComputedStyle(el.closest('.dashboard-empty')).backgroundColor})")
            assert colors['c']!=colors['b'],(theme,colors)
        dashboard.evaluate("document.documentElement.removeAttribute('data-theme')");dashboard.emulate_media(color_scheme='dark');dashboard.wait_for_timeout(60)
        system_colors=dashboard.locator('.dashboard-empty h2').evaluate("el=>({c:getComputedStyle(el).color,b:getComputedStyle(el.closest('.dashboard-empty')).backgroundColor})")
        assert system_colors['c']!=system_colors['b'],system_colors
        dashboard.emulate_media(color_scheme='light');assert dashboard.locator(".dashboard-empty h2").is_visible(); assert not dashboard_errors,dashboard_errors

        print('V12_BROWSER_STEP templates', flush=True)
        # Built-in templates for first-time accounts.
        templates = context.new_page(); template_errors=[]; templates.on("pageerror", lambda e: template_errors.append(str(e)))
        template_shell = """<!doctype html><html><body><span id='studioAccount'></span><button id='refreshBtn'>Refresh</button><input id='studioSearch'><select id='studioCategory'><option value='all'>All</option></select><select id='studioSource'><option value='all'>All</option></select><input id='studioFavorites' type='checkbox'><div id='studioGrid'></div><dialog id='studioDialog'><button id='studioClose'>Close</button><div id='studioDialogBody'></div></dialog>"""
        fetch_stub = LOCAL_STORAGE_STUB + "window.fetch=async url=>new Response(String(url).includes('/api/auth/me')?'{\"user\":{\"email\":\"new@example.com\"}}':'[]',{status:200,headers:{'Content-Type':'application/json'}});"
        templates_html = template_shell + "<script>" + fetch_stub + "</script><script>" + (ROOT / "builtin-templates.js").read_text(encoding="utf-8") + "</script><script>" + (ROOT / "templates.js").read_text(encoding="utf-8") + "</script></body></html>"
        templates.set_content(templates_html,wait_until="load");templates.wait_for_timeout(500)
        assert templates.locator('.studio-card').count()>=3, template_errors
        assert templates.get_by_text('Built-in',exact=False).count()>=1
        assert templates.get_by_text('No templates found',exact=False).count()==0
        assert not template_errors,template_errors

        print('V12_BROWSER_STEP editor', flush=True)
        # Real inline editor runtime: floating canvas tools stay off forms and YouTube auto-selects its source.
        editor=context.new_page();editor.set_viewport_size({'width':1440,'height':900});editor_errors=[];editor.on('pageerror',lambda e:editor_errors.append(str(e)));editor.set_content(build_inline_editor(),wait_until='load');editor.wait_for_timeout(900)
        if editor.locator('#finalTourDismiss').count() and editor.locator('#finalTourDismiss').is_visible():editor.locator('#finalTourDismiss').click()
        for section in ('event','blocks','media'):
            editor.evaluate("section=>{document.body.dataset.studioSection=section;document.body.classList.toggle('studio-content-mode',['event','blocks'].includes(section));document.body.classList.toggle('studio-design-mode',!['event','blocks'].includes(section));}",section)
            assert not editor.locator('.ei-experience-launch').is_visible(),section
        editor.locator('button[data-studio-tab="media"]').click();editor.wait_for_timeout(120)
        assert editor.locator('#youtubeUrl').is_visible()
        editor.locator('#youtubeUrl').fill('https://music.youtube.com/watch?v=dQw4w9WgXcQ');editor.wait_for_timeout(150)
        assert editor.locator('#musicSource').input_value()=='youtube' and editor.locator('#musicEnabled').is_checked();assert not editor_errors,editor_errors

        print('V12_BROWSER_STEP public', flush=True)
        # Fully inlined public renderer: Khmer language state, RSVP-off output and overflow.
        public_html=inline_public_html()
        public=context.new_page();public.set_viewport_size({'width':1440,'height':900});public_errors=[];public.on('pageerror',lambda e:public_errors.append(str(e)));public.set_content(public_html,wait_until='load');public.wait_for_timeout(500)
        public.wait_for_selector('[data-guest-lang="km"]');public.locator('[data-guest-lang="km"]').click();assert public.evaluate('document.documentElement.lang')=='km';assert public.locator('#rsvp').count()==0
        assert public.evaluate('document.documentElement.scrollWidth-innerWidth')<=2;assert not public_errors,public_errors
        mobile=context.new_page();mobile.set_viewport_size({'width':390,'height':844});mobile_errors=[];mobile.on('pageerror',lambda e:mobile_errors.append(str(e)));mobile.set_content(public_html,wait_until='load');mobile.wait_for_timeout(500);assert mobile.evaluate('document.documentElement.scrollWidth-innerWidth')<=2;mobile.keyboard.press('Tab');assert mobile.evaluate("document.activeElement && document.activeElement.tagName!=='BODY'");assert not mobile_errors,mobile_errors

        print('V12_BROWSER_STEP cleanup', flush=True)
        mobile.close();public.close();editor.close();templates.close();dashboard.close();context.close();browser.close()
    print('V12_BROWSER_STABILIZATION_TEST_PASSED');return 0

if __name__=='__main__':raise SystemExit(main())
