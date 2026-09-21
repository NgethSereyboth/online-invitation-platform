from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('src/js/crdt-adapter-v31.js','src/js/collaboration-studio-v31.js','src/js/canva-scale-v31.js','src/css/collaboration-studio-v31.css'):assert (ROOT/name).is_file(),name
crdt=(ROOT / "src" / "js" / "crdt-adapter-v31.js").read_text(encoding='utf-8')
server=(ROOT/'platform_v32/service.py').read_text(encoding='utf-8')
for token in ('stateVector','sequence-insert','rich-text','EPOCH_MISMATCH','compact'):assert token in crdt
for token in ('append_collaboration_updates','collaboration_checkpoints','document_version','_apply_document_update'):assert token in server
print('V31_COLLABORATION_CONTRACT_TEST_PASSED')
