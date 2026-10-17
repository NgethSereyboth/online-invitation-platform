from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('src/js/raster-model.js','src/js/raster-workspace.js','src/js/raster-worker.js','src/css/raster-workspace.css'):assert (ROOT/name).is_file(),name
model=(ROOT / "src" / "js" / "raster-model.js").read_text(encoding='utf-8')
workspace=(ROOT / "src" / "js" / "raster-workspace.js").read_text(encoding='utf-8')
for token in ('sourceAssetId','operations','adjustments','layers','masks','fingerprint'):assert token in model
for token in ('before','after','cancel','save','OffscreenCanvas'):assert token.lower() in workspace.lower()
print('V30_RASTER_WORKSPACE_CONTRACT_TEST_PASSED')
