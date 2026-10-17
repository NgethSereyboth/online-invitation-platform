from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=['src/js/document-schema.js','src/python/document_schema_v32.py','src/js/scene-graph.js','src/js/vector-model.js','src/js/professional-layers.js','src/css/professional-layers.css','src/js/advanced-public-renderer.js']
for name in required:assert (ROOT/name).is_file(),name
scene=(ROOT / "src" / "js" / "scene-graph.js").read_text(encoding='utf-8')
vector=(ROOT / "src" / "js" / "vector-model.js").read_text(encoding='utf-8')
assert 'professionalScene' in scene and 'componentDefinition' in scene and 'mask' in scene
for token in ('sanitizeSvg','boolean','pathData','defaultVector'):assert token in vector
print('V29_PROFESSIONAL_SCENE_VECTOR_CONTRACT_TEST_PASSED')
