"""Codex handoff contract for the selected V34–V52 implementation. Not executed during implementation."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
build=json.loads((ROOT / "docs" / "BUILD_INFO.json").read_text(encoding='utf-8'))
assert build['version']=='0.52'
assert build['schemaVersion']==27
required=(
 'future_platform_v52/schema.py','future_platform_v52/service.py','src/js/future-studio-loader.js','src/css/future-studio.css','src/js/future-ui.js','src/js/editor-deferred-tools-bootstrap.js',
 'src/js/unified-editor.js','src/js/ai-production.js','src/js/template-marketplace.js','src/js/enterprise-government.js',
 'src/js/advanced-animation.js','src/js/advanced-motion-runtime.js','src/js/publishing-domains.js','src/js/data-merge.js',
 'src/js/plugin-platform.js','src/js/plugin-runtime.js','src/js/event-ecosystem.js','src/js/future-public-renderer.js',
)
for name in required: assert (ROOT/name).is_file(), name
server=(ROOT/'src'/'python'/'server.py').read_text(encoding='utf-8')
for token in ('/api/platform/v52/','FuturePlatformService','ensure_future_schema'): assert token in server
route=json.loads((ROOT / "docs" / "route-bundles.json").read_text(encoding='utf-8'))['pages']['index.html']
# The 1_420_000 literal here was a third stale copy of the editor-route snapshot
# (see tests/route_budget_utils.py): it predates the declared source of truth,
# docs/perf/lighthouse-budgets.json, which tests/v55_route_weight_budget_test.py
# enforces on the whole page. Read the ceiling from that owner instead, exactly
# as v27_3_5_release_evidence_test.py and v53_1_operator_repair_contract_test.py do.
sys.path.insert(0, str(ROOT / "tests"))
from route_budget_utils import assert_index_route_within_budget  # noqa: E402
assert_index_route_within_budget()
for lazy in ('future-studio-loader.js','src/js/advanced-animation.js','src/js/plugin-runtime.js'):
    assert lazy not in route['sources']['scripts'], lazy
print('V0_52_SELECTED_CAPABILITIES_CONTRACT_TEST_PASSED')
