#!/usr/bin/env python3
"""Browser proof for public progress, section navigation, sharing, and compact mobile geometry."""
from __future__ import annotations
import os,sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from public_guest_feature_runtime_test import build_public,payload

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_CSS=(ROOT/'guest-layouts.css').read_text(encoding='utf-8')+'\n'+(ROOT/'guest-journey.css').read_text(encoding='utf-8')
def journey_payload():
 data=payload(rsvp=True);document=data['document'];document['sectionOrder']=['countdown','schedule','venue','rsvp'];document['settings'].update({'countdownEnabled':True,'scheduleEnabled':True,'venueEnabled':True,'guestNavigationEnabled':True});document['schedule']=[{'time':'4:00 PM','title':'Guest arrival','titleKm':'ទទួលភ្ញៀវ'},{'time':'6:00 PM','title':'Dinner','titleKm':'ពិសាភោជនាហារ'}];return data

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V0_52_GUEST_JOURNEY_NO_PLAYWRIGHT',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V0_52_GUEST_JOURNEY_NO_CHROMIUM',exc)
  capture=Path(os.environ['EINVITE_CAPTURE_DIR']) if os.environ.get('EINVITE_CAPTURE_DIR') else None
  if capture:capture.mkdir(parents=True,exist_ok=True)
  page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(build_public(journey_payload()),wait_until='load');page.add_style_tag(content=PUBLIC_CSS);page.wait_for_timeout(500)
  dock=page.locator('.guest-journey');assert dock.count()==1;assert dock.get_attribute('data-ready')=='false'
  page.locator('#openCover').click();page.wait_for_timeout(120);assert dock.get_attribute('data-ready')=='true'
  assert page.locator('[data-guest-waypoint]').count()>=4
  menu_button=page.locator('[data-journey-menu]');menu_button.click();menu=page.locator('.guest-journey-menu');assert menu.is_visible();assert page.locator('[data-journey-target]').count()>=4
  if capture:page.screenshot(path=str(capture/'guest-journey-mobile-menu.png'),full_page=False)
  page.keyboard.press('Escape');assert menu.is_hidden();assert menu_button.get_attribute('aria-expanded')=='false'
  page.locator('[data-guest-lang="km"]').click();page.wait_for_timeout(80);menu_button.click();assert 'កាលវិភាគ' in page.locator('[data-journey-target]').all_text_contents();page.keyboard.press('Escape')
  page.locator('[data-journey-next]').click();page.wait_for_timeout(700);assert int((dock.locator('small').text_content() or '1').split('/')[0].strip())>=2
  before_share=page.evaluate('scrollY');share_button=page.locator('[data-journey-share]');share_button.click();page.wait_for_timeout(80);assert page.locator('#publicSharePanel').is_visible();page.locator('#publicSharePanel [data-copy]').click();page.wait_for_timeout(40);assert (page.locator('[data-share-status]').text_content() or '').strip()
  page.locator('#publicSharePanel [data-close]').click();assert abs(page.evaluate('scrollY')-before_share)<20;assert share_button.evaluate('button=>button===document.activeElement')
  top=page.locator('[data-journey-top]');assert top.is_visible();top.click();page.wait_for_timeout(700);assert page.evaluate('scrollY')<4
  geometry=page.evaluate("""()=>{const d=document.querySelector('.guest-journey').getBoundingClientRect(),m=document.querySelector('#musicToggle').getBoundingClientRect();return{dock:{left:d.left,right:d.right,bottom:d.bottom},music:{left:m.left,right:m.right},width:innerWidth,doc:document.documentElement.scrollWidth}}""")
  assert geometry['dock']['left']>=0 and geometry['dock']['right']<=geometry['width'] and geometry['dock']['right']<=geometry['music']['left'],geometry
  assert geometry['doc']<=geometry['width']+1,geometry
  assert not errors,errors;page.close()
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_content(build_public(journey_payload()),wait_until='load');page.add_style_tag(content=PUBLIC_CSS);page.locator('#openCover').click();page.wait_for_timeout(100)
  page.wait_for_timeout(850)
  if capture:page.screenshot(path=str(capture/'guest-journey-desktop.png'),full_page=False)
  geometry=page.evaluate("""()=>{const d=document.querySelector('.guest-journey').getBoundingClientRect(),m=document.querySelector('#musicToggle').getBoundingClientRect();return{dock:{left:d.left,right:d.right},music:{left:m.left},width:innerWidth,doc:document.documentElement.scrollWidth}}""")
  assert geometry['dock']['left']>=0 and geometry['dock']['right']<=geometry['music']['left'] and geometry['doc']<=geometry['width']+1,geometry
  page.close();browser.close()
 print('V0_52_GUEST_JOURNEY_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
