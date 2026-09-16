from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=['document-schema-v32.js','document_schema_v32.py','scene-graph-v29.js','vector-model-v29.js','professional-layers-v29.js','professional-layers-v29.css','advanced-public-renderer-v32.js']
for name in required:assert (ROOT/name).is_file(),name
scene=(ROOT/'scene-graph-v29.js').read_text(encoding='utf-8')
vector=(ROOT/'vector-model-v29.js').read_text(encoding='utf-8')
assert 'professionalScene' in scene and 'componentDefinition' in scene and 'mask' in scene
for token in ('sanitizeSvg','boolean','pathData','defaultVector'):assert token in vector
print('V29_PROFESSIONAL_SCENE_VECTOR_CONTRACT_TEST_PASSED')
