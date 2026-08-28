#!/usr/bin/env python3
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from ai_agent.tools import tool_catalog, validate_tool_call, ToolValidationError
from ai_agent.capabilities import availability, coverage_report
from ai_agent.design_blueprints import validate_blueprint
from ai_agent.local_providers import validate_endpoint, LocalProviderError, discover_model_directory


def rejected(call):
    try:
        validate_tool_call(call)
    except ToolValidationError:
        return True
    return False


def snapshot(role='owner', **overrides):
    value={
        'invitationRole':role,'accountRole':'customer','uploadEnabled':True,
        'storageRemainingBytes':1_000_000,'archived':False,'workspacePolicyEnabled':True,
        'features':{'events':True,'plugins':True,'animation':True,'publishingDomains':True,'dataMerge':True,'marketplace':True},
    }
    value.update(overrides)
    return value


def main()->int:
    catalog=tool_catalog(); by_id={item['id']:item for item in catalog}
    coverage=coverage_report(catalog)
    assert coverage['toolCount']==80 and coverage['connectedToolCount']==80 and coverage['missingBindings']==[]
    assert all(row['binding'] and row['bindingType'] for row in coverage['tools'])
    required={
        'image.configure_frame','gallery.arrange','page.configure_style','invitation.configure_opening',
        'materials.import_folder','materials.import_zip','design.analyze_reference','design.apply_blueprint',
        'invitation.configure_rsvp','guest.read_delivery_status','event.configure_details'
    }
    assert required <= set(by_id), required-set(by_id)

    # Collaboration/account/workspace intersection.
    assert availability(by_id['object.update'], snapshot('viewer'))[0] is False
    assert availability(by_id['publish.prepare'], snapshot('designer'))[0] is False
    assert availability(by_id['publish.prepare'], snapshot('manager'))[0] is True
    assert availability(by_id['materials.import_folder'], snapshot('owner', uploadEnabled=False))[0] is False
    assert availability(by_id['materials.import_zip'], snapshot('owner', storageRemainingBytes=0))[0] is False
    assert availability(by_id['read.project_summary'], snapshot('owner', workspacePolicyEnabled=False))[0] is False
    assert availability(by_id['object.update'], snapshot('owner', archived=True))[0] is False
    assert availability(by_id['invitation.archive'], snapshot('owner', archived=True))[0] is True

    # Typed schemas and no arbitrary execution/destination fields.
    good=validate_tool_call({'id':'page.configure_style','arguments':{'pageId':'page-1','background':'#FFF8F2','backgroundAssetId':'asset-1','backgroundSize':'cover','transitionPreset':'soft'}})
    assert good['permission']=='edit' and good['arguments']['backgroundAssetId']=='asset-1'
    assert rejected({'id':'page.configure_style','arguments':{'pageId':'page-1','backgroundImage':'https://example.test/a.jpg'}})
    assert rejected({'id':'invitation.configure_opening','arguments':{'sceneId':'made-up-scene'}})
    assert rejected({'id':'object.update','arguments':{'pageId':'hero','objectIds':['x'],'patch':{'selector':'#x'}}})
    assert rejected({'id':'object.create_text','arguments':{'pageId':'hero','text':'file:///etc/passwd'}})
    details=validate_tool_call({'id':'event.configure_details','arguments':{'languageMode':'both','dateFormat':'both','khmerDate':'ថ្ងៃអាទិត្យ','mapUrl':'https://maps.google.com/?q=Phnom+Penh','venues':[{'name':'Reception','address':'Phnom Penh','nameKm':'ពិធីទទួលភ្ញៀវ','addressKm':'ភ្នំពេញ','mapUrl':'https://maps.google.com/?q=Phnom+Penh'}]}})
    assert details['permission']=='edit' and details['arguments']['venues'][0]['nameKm']=='ពិធីទទួលភ្ញៀវ'
    assert rejected({'id':'event.configure_details','arguments':{'languageMode':'fr'}})

    blueprint=validate_blueprint({
        'detectedInvitationCategory':'Wedding','confidence':1.8,
        'colorPalette':['#ffffff','#FFFFFF','not-a-color','#112233'],
        'typographyCategories':{'display':'Ceremonial serif','khmer':'Khmer ceremonial'},
        'textHierarchy':[{'role':'display','relativeSize':99,'weight':'bold','alignment':'center'}],
        'approximationWarnings':['Approximate protected ornaments rather than copying them.'],
    }, ['asset-1'])
    assert blueprint['schema']=='einvite-design-blueprint-v1'
    assert blueprint['confidence']==1.0
    assert blueprint['colorPalette']==['#FFFFFF','#112233']
    assert blueprint['textHierarchy'][0]['relativeSize']==12.0
    assert blueprint['referenceAssetIds']==['asset-1']

    assert validate_endpoint('http://127.0.0.1:11434', set())=='http://127.0.0.1:11434'
    try: validate_endpoint('https://127.0.0.1:11434', set())
    except LocalProviderError as exc: assert exc.code=='invalid_local_endpoint'
    else: raise AssertionError('HTTPS local provider endpoint unexpectedly accepted')
    try: validate_endpoint('http://192.0.2.10:11434', set())
    except LocalProviderError as exc: assert exc.code=='local_endpoint_not_allowed'
    else: raise AssertionError('non-loopback endpoint unexpectedly accepted')

    with tempfile.TemporaryDirectory(prefix='einvite-private-models-') as tmp:
        model_dir=Path(tmp)/'models';model_dir.mkdir()
        (model_dir/'approved.gguf').write_bytes(b'GGUF')
        (model_dir/'ignore.exe').write_bytes(b'MZ')
        found=discover_model_directory(str(model_dir), (str(ROOT),))
        assert found['available'] is True and [row['name'] for row in found['files']]==['approved.gguf']
        assert found['requiresRuntimeRegistration'] is True
        blocked=discover_model_directory(str(ROOT/'models'), (str(ROOT),))
        assert blocked.get('error')=='model_directory_inside_public_root'

    # Every registered tool has a concrete client/server dispatch reference.
    registry=(ROOT/'ai-agent-tool-registry-v28.js').read_text(encoding='utf-8')
    action_service=(ROOT/'ai-editor-action-service-v27.js').read_text(encoding='utf-8')
    action_extension=(ROOT/'ai-editor-action-extension-v53.js').read_text(encoding='utf-8')
    loader=(ROOT/'ai-assistant-loader-v27.js').read_text(encoding='utf-8')
    route_sources=(ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8')
    missing=[tool_id for tool_id in by_id if tool_id not in registry]
    assert not missing, missing
    assert 'materials.retry_import' not in by_id and 'materials.retry_import' not in registry
    postgres=(ROOT/'postgres_schema.sql').read_text(encoding='utf-8')
    for table in ('material_folders','material_import_jobs','ai_design_blueprints','ai_verification_results','ai_local_provider_configs','ai_model_capabilities'):
        assert f'CREATE TABLE IF NOT EXISTS {table}' in postgres, table
    for column in ('feedback_learning','memory_enabled','knowledge_enabled'):
        assert f'ALTER TABLE ai_preferences ADD COLUMN IF NOT EXISTS {column}' in postgres, column
    assert 'updateImageFrame' in action_extension
    assert 'ai-editor-action-extension-v53.js' in loader and 'upload-folder-client-v53.js' in loader
    import json as _json
    _sources=_json.loads(route_sources)
    assert 'upload-folder-client-v53.js' in _sources['pages']['materials.html']['scripts']
    assert 'upload-folder-client-v53.js' not in _sources['pages']['index.html']['scripts']
    for marker in ('updatePageStyle','updateOpeningScene','updateEventDetails','image.configure_frame','gallery.arrange','backgroundAssetId'):
        assert marker in registry or marker in action_service or marker in action_extension, marker

    # ZIP path validation is deliberately imported after a temp data directory is configured.
    with tempfile.TemporaryDirectory(prefix='einvite-v53-server-') as data:
        os.environ['EINVITE_DATA_DIR']=data
        import server
        assert server.validate_material_zip_entry_path('Wedding Materials/Bride/portrait.jpg')=='Wedding Materials/Bride/portrait.jpg'
        for bad in ('../evil.jpg','/etc/passwd','C:\\evil.exe','Wedding/./x.jpg','Wedding/../x.jpg'):
            try: server.validate_material_zip_entry_path(bad)
            except ValueError: pass
            else: raise AssertionError(f'unsafe ZIP path accepted: {bad}')

    print('V53_1_AI_PROJECT_OPERATOR_CONTRACT_TEST_PASSED')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
