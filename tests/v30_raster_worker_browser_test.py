#!/usr/bin/env python3
"""Real Chromium worker rendering, cancellation, and stale-result coverage for V30."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
WORKER = (ROOT / "raster-worker-v30.js").read_text(encoding="utf-8")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"V30_RASTER_WORKER_BROWSER_SKIPPED_NO_PLAYWRIGHT: {exc}")
        return 0

    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            print(f"V30_RASTER_WORKER_BROWSER_SKIPPED_NO_CHROMIUM: {exc}")
            return 0
        page = browser.new_page()
        page.set_content("<!doctype html><meta charset=utf-8><body></body>")
        supported = page.evaluate("()=>typeof Worker==='function'&&typeof OffscreenCanvas==='function'&&typeof createImageBitmap==='function'")
        if not supported:
            browser.close()
            print("V30_RASTER_WORKER_BROWSER_SKIPPED_UNSUPPORTED")
            return 0
        result = page.evaluate(
            """async source=>{
 const url=URL.createObjectURL(new Blob([source],{type:'text/javascript'})),worker=new Worker(url),events=[];
 const wait=predicate=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('worker timeout')),10000);const listener=event=>{events.push(event.data);if(predicate(event.data)){clearTimeout(timer);worker.removeEventListener('message',listener);resolve(event.data)}};worker.addEventListener('message',listener)});
 const makeBitmap=(w,h,color='#000')=>{const c=new OffscreenCanvas(w,h),x=c.getContext('2d');x.fillStyle=color;x.fillRect(0,0,w,h);return c.transferToImageBitmap()};
 const sourceCanvas=new OffscreenCanvas(8,6),ctx=sourceCanvas.getContext('2d');ctx.fillStyle='#d22';ctx.fillRect(0,0,8,6);
 const firstBitmap=sourceCanvas.transferToImageBitmap();worker.postMessage({type:'render',jobId:'first',width:16,height:12,bitmap:firstBitmap,adjustments:[{type:'brightness',value:10}],operations:[]},[firstBitmap]);
 const first=await wait(data=>data.type==='result'&&data.jobId==='first');const firstShape={width:first.width,height:first.height,fingerprint:first.operationFingerprint,bitmapWidth:first.bitmap.width,bitmapHeight:first.bitmap.height};first.bitmap.close();
 const many=Array.from({length:1200},(_,i)=>({enabled:true,parameters:{stroke:{tool:'brush',color:'#111',size:2,points:[{x:(i%20)/20,y:0},{x:(i%20)/20,y:1}]}}}));
 const cancelBitmap=makeBitmap(128,128);worker.postMessage({type:'render',jobId:'cancel-me',width:128,height:128,bitmap:cancelBitmap,operations:many},[cancelBitmap]);
 await wait(data=>data.type==='progress'&&data.jobId==='cancel-me'&&data.progress===.2);worker.postMessage({type:'cancel',jobId:'cancel-me'});const cancelled=await wait(data=>data.jobId==='cancel-me'&&(data.type==='cancelled'||data.type==='result'));
 let current='old';const applied=[];const applyListener=event=>{if(event.data.type==='result'&&event.data.jobId===current){applied.push(event.data.jobId);event.data.bitmap.close()}};worker.addEventListener('message',applyListener);
 const oldBitmap=makeBitmap(96,96);worker.postMessage({type:'render',jobId:'old',width:96,height:96,bitmap:oldBitmap,operations:many},[oldBitmap]);
 await wait(data=>data.type==='progress'&&data.jobId==='old'&&data.progress===.2);current='new';worker.postMessage({type:'cancel',jobId:'old'});
 const newBitmap=makeBitmap(4,4);worker.postMessage({type:'render',jobId:'new',width:4,height:4,bitmap:newBitmap,operations:[]},[newBitmap]);
 await wait(data=>data.type==='result'&&data.jobId==='new');await new Promise(resolve=>setTimeout(resolve,80));
 worker.removeEventListener('message',applyListener);worker.terminate();URL.revokeObjectURL(url);
 return{first:firstShape,cancelType:cancelled.type,applied,eventTypes:events.map(x=>x.jobId+':'+x.type)};
}""",
            WORKER,
        )
        assert result["first"]["width"] == 16 and result["first"]["height"] == 12, result
        assert result["first"]["bitmapWidth"] == 16 and result["first"]["bitmapHeight"] == 12, result
        assert len(result["first"]["fingerprint"]) == 8, result
        assert result["cancelType"] == "cancelled", result
        assert result["applied"] == ["new"], result
        browser.close()

    workspace = (ROOT / "raster-workspace-v30.js").read_text(encoding="utf-8")
    for token in ("typeof OffscreenCanvas==='undefined'", "Using bounded Canvas 2D preview", "data.jobId!==workerJobId", "workerGeneration", "URL.revokeObjectURL"):
        assert token in workspace, token
    print("V30_RASTER_WORKER_BROWSER_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
