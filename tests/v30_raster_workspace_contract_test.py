from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('raster-model-v30.js','raster-workspace-v30.js','raster-worker-v30.js','raster-workspace-v30.css'):assert (ROOT/name).is_file(),name
model=(ROOT/'raster-model-v30.js').read_text(encoding='utf-8')
workspace=(ROOT/'raster-workspace-v30.js').read_text(encoding='utf-8')
for token in ('sourceAssetId','operations','adjustments','layers','masks','fingerprint'):assert token in model
for token in ('before','after','cancel','save','OffscreenCanvas'):assert token.lower() in workspace.lower()
print('V30_RASTER_WORKSPACE_CONTRACT_TEST_PASSED')
