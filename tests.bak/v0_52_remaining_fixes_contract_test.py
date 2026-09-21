"""Structural handoff contract for the V0.52 repair pass. Intended for Codex execution."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
build=json.loads((ROOT / "docs" / "BUILD_INFO.json").read_text(encoding='utf-8'))
assert build['version']=='0.52'
assert build['schemaVersion']==27
assert build['certification']['editorRouteBytes']<=build['certification']['editorRouteLimit']==1_420_000
route=json.loads((ROOT / "docs" / "route-bundles-v15.json").read_text(encoding='utf-8'))['pages']['index.html']
assert 'editor-deferred-tools-bootstrap-v0_52.js' in route['sources']['scripts']
for lazy in ('ai-assistant-loader-v27.js','advanced-editor-loader-v32.js','font-browser-loader-v22.js','future-studio-loader-v52.js','future-ui-v0_52.js'):
    assert lazy not in route['sources']['scripts'],lazy
selected=('src/js/unified-editor-v34.js','src/js/ai-production-v35.js','src/js/template-marketplace-v36.js','src/js/enterprise-government-v42.js','src/js/advanced-animation-v44.js','src/js/publishing-domains-v45.js','src/js/data-merge-v47.js','src/js/plugin-platform-v48.js','src/js/event-ecosystem-v52.js','src/js/future-studio-loader-v52.js','src/js/future-ui-v0_52.js','src/js/ai-assistant-loader-v27.js','src/js/font-browser-loader-v22.js')
for name in selected:
    source=(ROOT/name).read_text(encoding='utf-8')
    for forbidden in ('innerHTML','insertAdjacentHTML','style.textContent','eval(','new Function'):
        assert forbidden not in source,(name,forbidden)
service=(ROOT/'future_platform_v52/service.py').read_text(encoding='utf-8')
for token in ('marketplace_moderation_required','domain_provider_required','rawRowsPersisted','safe_policy_value'):
    assert token in service,token
assert 'localStorage.getItem(\'einvite-csrf\')' not in (ROOT / "src" / "js" / "future-studio-loader-v52.js").read_text(encoding='utf-8')

app=(ROOT / "src" / "js" / "app.js").read_text(encoding='utf-8')
for token in ('normalizeUploadedAsset','reconcileAssetRefs','localAssetId','serverId','await reconcileAssetRefs(state)'):
    assert token in app,token
platform=(ROOT/'platform_v32/service.py').read_text(encoding='utf-8')
for token in ('resolvedAssetIds','legacyId','asset_wrong_invitation','asset_wrong_workspace','localAssetId'):
    assert token in platform,token
public_route=json.loads((ROOT / "docs" / "route-bundle-sources-v15.json").read_text(encoding='utf-8'))['pages']['public.html']['scripts']
assert 'vendor/momentkh.js' not in public_route
loader=(ROOT / "src" / "js" / "advanced-public-loader-v32.js").read_text(encoding='utf-8')
public=(ROOT / "src" / "js" / "public-page.js").read_text(encoding='utf-8')
assert "script('momentkh','vendor/momentkh.js')" in loader
assert 'await Promise.resolve(window.EInviteAdvancedPublicLoader?.load?.(d))' in public
assert public.index('await Promise.resolve(window.EInviteAdvancedPublicLoader?.load?.(d))') < public.index("khmer=d.khmerDate||khmerFor")

context=(ROOT/'ai_agent/context.py').read_text(encoding='utf-8')
assert "resolved=0" in context and "status='open'" not in context
agent_service=(ROOT/'ai_agent/service.py').read_text(encoding='utf-8')
assert 'client_disconnected' in agent_service and 'job_finished' in agent_service
server=(ROOT/'src'/'python'/'server.py').read_text(encoding='utf-8')
assert server.count('agent_internal_error')>=2 and 'application/x-ndjson' in server
assert "card.querySelector('.actions [data-edit]')?.click()" in (ROOT / "src" / "js" / "final-polish.js").read_text(encoding='utf-8')
for token in ('saveServerDraft(documentSnapshot=state)','serverSaveErrorCode','cancelIdleCallback','server_save_retry','transientServerSaveError'):
    assert token in app,token
runner=(ROOT/'src'/'python'/'run_review_checks.py').read_text(encoding='utf-8')
for test in ('v0_52_ai_real_server_test.py','v0_52_ai_live_browser_test.py','v0_52_dashboard_cover_navigation_test.py','v0_52_autosave_status_test.py'):
    assert test in runner,test

print('V0_52_REMAINING_FIXES_CONTRACT_TEST_PASSED')
