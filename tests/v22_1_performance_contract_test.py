#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(name:str)->str:return (ROOT/name).read_text(encoding='utf-8')

def main()->int:
 required=['performance-loader-v22.js','performance-observability-v22.js','interaction-scheduler-v22.js','incremental-scene-renderer-v22.js','render-worker-bridge-v22.js','scene-render-worker-v22.js','gpu-loader-v22.js','gpu-texture-cache-v22.js','webgl-scene-backend-v22.js','gpu-projection-v22.js','adaptive-gpu-quality-v22.js']
 for name in required:
  assert (ROOT/name).is_file(),name
 sources=json.loads(read('route-bundle-sources-v15.json'))['pages']['index.html']['scripts']
 assert 'performance-loader-v22.js' in sources
 loader=read('performance-loader-v22.js')
 for name in required[1:5]:assert name.removesuffix('-v22.js') in loader,name
 assert 'gpu-loader' not in loader
 bridge=read('render-worker-bridge-v22.js');assert 'gpu-loader-v22.js' in bridge and 'loadGPU' in bridge
 gpu_loader=read('gpu-loader-v22.js')
 for name in required[7:]:assert name.removesuffix('-v22.js') in gpu_loader,name
 app=read('app.js');pro=read('professional-editor-v17.js')
 assert ('options.incremental === true' in app or 'options.incremental===true' in app) and 'EInviteIncrementalRenderer.applyDocument' in app
 assert 'EInviteInteractionScheduler' in pro and 'editor-gesture:' in pro
 assert "'compositor'" in pro and 'peTransformPreview' in pro
 assert 'EInviteIncrementalRenderer?.queryRect' in pro
 assert "event.type==='pointercancel'" in pro
 manifest=json.loads(read('page-assets-v15.json'))['pages']['index.html']
 assert manifest['bytes']<=1_420_000,manifest
 gpu=read('webgl-scene-backend-v22.js');textures=read('gpu-texture-cache-v22.js');adaptive=read('adaptive-gpu-quality-v22.js');projection=read('gpu-projection-v22.js')
 assert "powerPreference:'high-performance'" in gpu and 'webglcontextlost' in gpu and 'setEnabled' in gpu
 assert 'maxBytes' in textures and 'Cross-origin GPU texture blocked' in textures and 'evict()' in textures
 assert 'renderPickBuffer' in projection and 'u_pick' in gpu and 'gpuMaskSrc' in gpu
 assert 'Compatibility mode' in adaptive and 'Rendering quality' in adaptive and 'navigator.gpu' in adaptive
 for name in required:
  text=read(name)
  assert '\x00' not in text and len(text)>100,name
 print('V22_1_PERFORMANCE_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
