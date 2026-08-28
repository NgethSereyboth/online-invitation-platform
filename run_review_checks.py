#!/usr/bin/env python3
"""Run the cumulative V0.52 deterministic and required real-browser release gate.

Browser skips are failures by default. ``--skip-browser`` is intentionally a
local-development convenience and must never be used by ``release_check.py``.
Every subprocess receives isolated data, bounded time, process-tree shutdown,
and retrying cleanup for Windows SQLite/filesystem timing.
"""
from __future__ import annotations
import argparse,concurrent.futures,os,signal,subprocess,sys,tempfile,time,shutil,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def configure_utf8_console():
 for stream in (sys.stdout,sys.stderr):
  reconfigure=getattr(stream,'reconfigure',None)
  if reconfigure:
   try:reconfigure(encoding='utf-8',errors='replace')
   except (ValueError,OSError):pass

configure_utf8_console()

FAST_CHECKS=[
 'tests/v0_52_final_ux_refinement_contract_test.py',
 'tests/v0_52_security_boundary_test.py',
 'tests/v0_52_security_hardening_attack_test.py',
 'tests/v0_52_upload_permission_test.py',
 'tests/v0_52_multi_host_deployment_test.py',
 'tests/v0_52_laptop_host_contract_test.py',
 'tests/v0_52_first_time_setup_contract_test.py',
 'tests/v0_52_guest_journey_contract_test.py',
 'tests/v53_1_operator_repair_contract_test.py',
 'tests/v53_1_ai_project_operator_backend_test.py',
 'tests/v0_52_ai_real_server_test.py','tests/v0_52_remaining_fixes_contract_test.py','tests/v0_52_production_deployment_hardening_test.py','tests/v52_selected_capabilities_contract_test.py','tests/v29_professional_scene_vector_contract_test.py','tests/v30_raster_workspace_contract_test.py','tests/v31_collaboration_contract_test.py','tests/v32_platform_contract_test.py','tests/v28_agent_server_contract_test.py','tests/v28_agent_provider_test.py','tests/v28_agent_storage_test.py','tests/v28_agent_tool_contract_test.py','tests/v28_agent_performance_contract_test.py','tests/v0_52_asset_identity_test.py','tests/v22_zoom_layout_test.py',
 'tests/v27_3_5_ai_backend_contract_test.py','tests/v27_3_5_release_evidence_test.py', 'tests/v27_3_4_repair_contract_test.py','tests/v27_studio_automation_contract_test.py','tests/v27_studio_automation_backend_test.py','tests/v27_studio_automation_migration_test.py','tests/v27_studio_backup_scheduler_test.py', 'tests/v26_studio_operations_contract_test.py','tests/v26_studio_operations_backend_test.py','tests/v26_studio_operations_migration_test.py','tests/v25_template_governance_contract_test.py','tests/v25_template_governance_backend_test.py', 'tests/v24_canva_experience_contract_test.py','tests/v24_collaboration_tasks_backend_test.py', 'tests/build_integrity_test.py','tests/v10_experience_test.py','tests/v11_media_experience_test.py',
 'tests/v12_storage_privacy_test.py','tests/v12_immediate_stabilization_test.py','tests/v12_routing_context_test.py','tests/v12_media_source_test.py',
 'tests/v13_future_foundation_test.py','tests/v13_account_security_test.py','tests/v13_editor_model_test.py','tests/v13_backup_restore_test.py','tests/v13_product_lifecycle_test.py','tests/v13_privacy_lifecycle_test.py',
 'tests/v14_lifecycle_signing_test.py','tests/v14_performance_budget_test.py','tests/v15_integration_hardening_test.py','tests/v15_http_integration_test.py','tests/v16_windows_ui_hardening_test.py','tests/v17_professional_foundation_test.py','tests/v17_persistence_snapshot_test.py',
 'tests/v19_typography_model_test.py','tests/v19_typography_invalid_input_test.py','tests/v20_typography_architecture_test.py','tests/v22_scene_model_test.py','tests/v22_1_performance_contract_test.py','tests/v22_2_page_experience_contract_test.py','tests/v23_command_registry_test.py','tests/v23_2_navigation_history_contract_test.py','tests/v23_3_style_history_contract_test.py','tests/v23_4_asset_workflow_contract_test.py','tests/v23_5_photo_workflow_contract_test.py','tests/v23_6_photo_style_library_contract_test.py','tests/v23_8_review_operations_contract_test.py','tests/v23_8_review_operations_backend_test.py','tests/v23_7_review_contract_test.py','tests/v23_7_review_backend_test.py','tests/v22_custom_font_upload_test.py','tests/v22_custom_font_server_endpoint_test.py','tests/v22_0_3_khmer_custom_font_quality_test.py','tests/v20_1_stabilization_contract_test.py','tests/v21_0_rich_text_model_test.py','tests/v21_0_rich_text_server_test.py','tests/v21_0_migration_roundtrip_test.py','tests/static_integrity_test.py','tests/smoke_test.py','tests/plan_limit_test.py','tests/final_features_test.py','tests/production_foundations_test.py','tests/provider_adapters_test.py','tests/realtime_storage_test.py','tests/signed_upload_backend_test.py','tests/final_visual_polish_test.py','tests/ux_ai_v5_test.py','tests/pro_editor_v6_test.py','tests/workflow_continuity_test.py','tests/final_workflow_audit_v7_test.py','tests/security_regression_test.py','tests/security_maintenance_test.py','tests/private_access_header_test.py','tests/collaboration_asset_permissions_test.py','tests/optimistic_revision_test.py','tests/collaboration_revision_test.py',
]
SERIAL_FAST_CHECKS={
 'tests/v0_52_security_hardening_attack_test.py','tests/v53_1_ai_project_operator_backend_test.py','tests/v0_52_ai_real_server_test.py','tests/v0_52_asset_identity_test.py','tests/provider_adapters_test.py','tests/realtime_storage_test.py','tests/v27_3_5_release_evidence_test.py','tests/v11_media_experience_test.py','tests/v12_storage_privacy_test.py','tests/v12_immediate_stabilization_test.py','tests/v13_account_security_test.py','tests/v13_backup_restore_test.py','tests/v13_product_lifecycle_test.py','tests/v13_privacy_lifecycle_test.py','tests/v15_http_integration_test.py','tests/v17_persistence_snapshot_test.py','tests/plan_limit_test.py','tests/smoke_test.py','tests/production_foundations_test.py', 'tests/v27_studio_automation_backend_test.py','tests/v27_studio_automation_migration_test.py','tests/v27_studio_backup_scheduler_test.py', 'tests/v26_studio_operations_backend_test.py','tests/v26_studio_operations_migration_test.py','tests/v25_template_governance_backend_test.py', 'tests/v23_8_review_operations_backend_test.py','tests/v23_7_review_backend_test.py','tests/collaboration_asset_permissions_test.py','tests/optimistic_revision_test.py','tests/collaboration_revision_test.py',
}
BROWSER_CHECKS=[
 'tests/v0_52_final_ux_refinement_browser_test.py',
 'tests/v0_52_guest_journey_browser_test.py',
 'tests/v0_52_ai_live_browser_test.py','tests/v0_52_dashboard_cover_navigation_test.py','tests/v0_52_autosave_status_test.py','tests/v0_52_platform_dark_mode_browser_test.py','tests/v0_52_public_lazy_loader_browser_test.py','tests/v30_raster_worker_browser_test.py','tests/ui_smoke_test.py','tests/v28_agent_conversation_browser_test.py','tests/v28_agent_mobile_browser_test.py','tests/v28_agent_registry_browser_test.py',
 'tests/v27_3_5_ai_transaction_browser_test.py','tests/v27_3_5_ai_rich_text_browser_test.py','tests/v27_3_5_ai_target_revision_test.py','tests/v27_3_5_ai_layout_preview_test.py','tests/v27_3_5_ai_accessibility_mobile_test.py','tests/v27_3_5_mobile_canvas_hud_test.py','tests/v27_3_5_typography_preview_sequence_test.py', 'tests/v27_3_4_repair_browser_test.py','tests/v27_studio_automation_browser_test.py','tests/v27_studio_automation_mobile_test.py','tests/v27_studio_automation_performance_test.py', 'tests/v26_studio_operations_browser_test.py','tests/v26_studio_operations_mobile_test.py','tests/v26_studio_operations_performance_test.py','tests/v25_template_governance_browser_test.py','tests/v25_template_governance_mobile_test.py','tests/v25_template_governance_performance_test.py', 'tests/v24_canva_experience_browser_test.py','tests/v24_canva_experience_mobile_test.py','tests/v24_export_quality_browser_test.py','tests/v24_canva_experience_performance_test.py', 'tests/v23_8_review_operations_browser_test.py','tests/v23_8_review_operations_mobile_test.py','tests/v23_8_review_operations_performance_test.py','tests/v23_7_review_workflow_browser_test.py','tests/v23_7_review_mobile_test.py','tests/v23_7_review_performance_test.py','tests/v23_6_photo_style_library_browser_test.py','tests/v23_6_photo_style_library_mobile_test.py','tests/v23_6_photo_style_library_performance_test.py','tests/v23_5_photo_workflow_browser_test.py','tests/v23_5_photo_workflow_performance_test.py','tests/v23_4_asset_workflow_browser_test.py','tests/v23_4_asset_workflow_performance_test.py','tests/v23_3_style_history_browser_test.py','tests/v23_3_style_history_performance_test.py','tests/v23_2_navigation_history_browser_test.py','tests/v23_2_navigation_history_performance_test.py','tests/v23_command_system_browser_test.py','tests/v23_command_lazy_loader_test.py','tests/v23_command_performance_test.py', 'tests/v22_2_page_experience_test.py','tests/v22_2_page_refinement_test.py','tests/v22_2_page_mobile_test.py','tests/v22_2_page_performance_test.py','tests/v22_1_4_webgl_backend_test.py','tests/v22_1_5_texture_cache_test.py','tests/v22_1_6_gpu_projection_test.py','tests/v22_1_7_adaptive_gpu_quality_test.py','tests/v22_1_7_gpu_editor_integration_test.py','tests/v22_1_7_gpu_fallback_test.py','tests/v22_1_7_real_webgl_runtime_test.py','tests/v22_1_worker_rendering_browser_test.py','tests/v22_1_editor_interaction_performance_test.py','tests/v22_1_performance_benchmark.py','tests/v14_static_server_test.py','tests/v14_live_server_acceptance_test.py','tests/v14_live_layout_test.py','tests/v14_dashboard_mobile_test.py','tests/v16_browser_geometry_test.py','tests/v0_52_free_canvas_drag_test.py','tests/v17_professional_editor_core_test.py',('tests/v18_nested_transform_matrix_test.py','--case','nw'),('tests/v18_nested_transform_matrix_test.py','--case','n'),('tests/v18_nested_transform_matrix_test.py','--case','ne'),('tests/v18_nested_transform_matrix_test.py','--case','e'),('tests/v18_nested_transform_matrix_test.py','--case','se'),('tests/v18_nested_transform_matrix_test.py','--case','s'),('tests/v18_nested_transform_matrix_test.py','--case','sw'),('tests/v18_nested_transform_matrix_test.py','--case','w'),('tests/v18_nested_transform_matrix_test.py','--case','finish'),'tests/v17_professional_editor_mobile_test.py','tests/v17_layers_clipboard_history_test.py','tests/v17_served_editor_test.py',
 'tests/v19_typography_runtime_test.py','tests/v20_typography_editor_runtime_test.py','tests/v20_font_registry_loading_test.py','tests/v20_khmer_shaping_test.py','tests/v20_typography_accessibility_test.py','tests/v20_semantic_style_parity_test.py','tests/v22_custom_font_browser_runtime_test.py','tests/v22_custom_font_lazy_loader_test.py','tests/v22_0_3_khmer_custom_font_browser_test.py','tests/v20_1_dashboard_actions_runtime_test.py','tests/v20_1_semantic_boundary_runtime_test.py','tests/v20_1_bilingual_public_runtime_test.py','tests/v20_1_lifecycle_mobile_runtime_test.py','tests/v21_0_rich_text_runtime_test.py','tests/v21_1_renderer_parity_test.py','tests/v21_2_accessible_editing_test.py','tests/v21_3_workspace_hardening_test.py','tests/v19_server_typography_contract_test.py','tests/v19_editor_public_parity_test.py','tests/v19_responsive_autofit_test.py','tests/v19_font_loading_test.py','tests/v19_typography_visual_geometry_test.py','tests/inline_editor_runtime_test.py','tests/v10_browser_runtime_test.py','tests/v11_browser_runtime_test.py','tests/v12_browser_stabilization_test.py','tests/v13_browser_runtime_test.py','tests/editor_layout_geometry_test.py','tests/public_layout_runtime_test.py','tests/public_guest_feature_runtime_test.py','tests/theme_launcher_runtime_test.py',
]

def process_kwargs():
 return {'creationflags':getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)} if os.name=='nt' else {'start_new_session':True}

def stop_tree(process):
 try:
  if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
  else:os.killpg(process.pid,signal.SIGTERM)
 except Exception:
  try:process.terminate()
  except Exception:pass
 try:process.wait(timeout=8)
 except subprocess.TimeoutExpired:
  try:
   if os.name=='nt':process.kill()
   else:os.killpg(process.pid,signal.SIGKILL)
  except Exception:pass
  try:process.wait(timeout=3)
  except Exception:pass

def cleanup(path):
 path=Path(path)
 for attempt in range(14):
  try:
   if path.exists():shutil.rmtree(path)
   return
  except (PermissionError,OSError):gc.collect();time.sleep(min(.08*(attempt+1),.8))
 if path.exists():raise RuntimeError(f'Unable to clean isolated test directory: {path}')

def execute(script,timeout=240,require_browser=False):
 parts=list(script) if isinstance(script,(tuple,list)) else [script]
 label=' '.join(map(str,parts))
 data_dir=Path(tempfile.mkdtemp(prefix='einvite-check-'))
 output_path=data_dir/'suite-output.log'
 env={**os.environ,'EINVITE_DATA_DIR':str(data_dir),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}
 if os.name=='nt' and env.get('OPENSSL_CONF') and not Path(env['OPENSSL_CONF']).is_file():
  print(f"Ignoring invalid OPENSSL_CONF for child test process: {env['OPENSSL_CONF']}",flush=True);env.pop('OPENSSL_CONF',None)
 if require_browser:env['EINVITE_REQUIRE_BROWSER']='1'
 process=None;code=1;timed_out=False
 try:
  with output_path.open('w',encoding='utf-8',errors='replace') as stream:
   process=subprocess.Popen([sys.executable,str(ROOT/parts[0]),*map(str,parts[1:])],cwd=ROOT,text=True,env=env,stdout=stream,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',**process_kwargs())
   try:code=process.wait(timeout=timeout);code=code or 0
   except subprocess.TimeoutExpired:
    timed_out=True;stop_tree(process);code=124
   finally:
    stream.flush()
  output=output_path.read_text(encoding='utf-8',errors='replace') if output_path.exists() else ''
  if timed_out:output+='\nTEST_TIMEOUT after %ss'%timeout
  if require_browser and code==0 and 'SKIP' in output.upper():
   output+='\nREQUIRED_BROWSER_SUITE_WAS_SKIPPED';code=125
  return label,code,output
 finally:
  if process:stop_tree(process)
  cleanup(data_dir)

def main(argv=None):
 parser=argparse.ArgumentParser()
 parser.add_argument('--skip-browser',action='store_true',help='development only; not valid for release acceptance')
 parser.add_argument('--continue-on-failure',action='store_true',help='run the complete current-release matrix and report every failure before exiting nonzero')
 parser.add_argument('--fast-workers',type=int,default=int(os.getenv('EINVITE_FAST_WORKERS','1')),help='bounded deterministic-test concurrency')
 args=parser.parse_args(argv);workers=max(1,min(args.fast_workers,len(FAST_CHECKS)));failures=[]
 print(f'Running {len(FAST_CHECKS)} V0.52 deterministic checks with up to {workers} workers...',flush=True)
 results={}
 if workers==1:
  for check in FAST_CHECKS:
   label,code,output=execute(check);results[check]=(code,output);print(f"  {'PASS' if code==0 else 'FAIL'} {label}",flush=True)
   if code:
    failures.append((label,code,output))
    if not args.continue_on_failure:break
   time.sleep(float(os.getenv('EINVITE_TEST_TEARDOWN_SECONDS','0.25')))
 else:
  parallel=[check for check in FAST_CHECKS if check not in SERIAL_FAST_CHECKS]
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
   futures={pool.submit(execute,check):check for check in parallel}
   for future in concurrent.futures.as_completed(futures):
    label,code,output=future.result();results[futures[future]]=(code,output);print(f"  {'PASS' if code==0 else 'FAIL'} {label}",flush=True)
    if code:failures.append((label,code,output))
  for check in FAST_CHECKS:
   if check not in SERIAL_FAST_CHECKS:continue
   label,code,output=execute(check);results[check]=(code,output);print(f"  {'PASS' if code==0 else 'FAIL'} {label}",flush=True)
   if code:
    failures.append((label,code,output))
    if not args.continue_on_failure:break
 if failures and not args.continue_on_failure:
  label,code,output=failures[0];print(f'\n== {label} ==\n{output.rstrip()}',flush=True);print(f'\nREVIEW_CHECK_FAILED: {label}',file=sys.stderr);return code
 if not args.skip_browser:
  print(f'\nRunning {len(BROWSER_CHECKS)} required V0.52 browser checks sequentially...',flush=True)
  for check in BROWSER_CHECKS:
   label,code,output=execute(check,timeout=420,require_browser=True);print(f"  {'PASS' if code==0 else 'FAIL'} {label}",flush=True)
   if code:
    failures.append((label,code,output))
    if not args.continue_on_failure:break
 elif args.skip_browser:print('\nDEVELOPMENT_BROWSER_CHECKS_SKIPPED (not a release result)')
 if failures:
  print(f'\nV0.52 complete audit found {len(failures)} failing checks:',file=sys.stderr)
  for label,code,output in failures:
   print(f'\n== {label} (exit {code}) ==',file=sys.stderr)
   if output:print(output.rstrip(),file=sys.stderr)
  return 1
 if args.skip_browser:return 0
 print('\nEINVITATION_V0_52_ALL_REQUIRED_REVIEW_CHECKS_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
