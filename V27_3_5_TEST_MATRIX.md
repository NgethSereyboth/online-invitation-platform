# V27.3.5 Full Test Matrix

## Evidence summary

| Gate | Result | Evidence mode |
|---|---:|---|
| Deterministic contracts | 76/76 passed | Isolated segmented execution; the single orchestration process could not finish within the host command window, so the uninterrupted marker is not claimed. |
| Browser contracts | 97/104 passed | Every browser contract was attempted. Seven loopback server-navigation suites were blocked by managed Chromium policy before assertions. |
| Application assertion failures after page load | 0 | No loaded-page browser assertion failed. |
| Focused typography preview stress | 10/10 passed | Sequence test repeats the repaired keyboard activation path ten times. |
| Required final release markers | Not produced | Full release remains pending by design. |

## Deterministic contracts — 76/76 passed in segmented execution

| # | Contract | Result |
|---:|---|---|
| 1 | `tests/v27_3_5_ai_backend_contract_test.py` | PASS |
| 2 | `tests/v27_3_5_release_evidence_test.py` | PASS |
| 3 | `tests/v27_3_4_repair_contract_test.py` | PASS |
| 4 | `tests/v27_studio_automation_contract_test.py` | PASS |
| 5 | `tests/v27_studio_automation_backend_test.py` | PASS |
| 6 | `tests/v27_studio_automation_migration_test.py` | PASS |
| 7 | `tests/v27_studio_backup_scheduler_test.py` | PASS |
| 8 | `tests/v26_studio_operations_contract_test.py` | PASS |
| 9 | `tests/v26_studio_operations_backend_test.py` | PASS |
| 10 | `tests/v26_studio_operations_migration_test.py` | PASS |
| 11 | `tests/v25_template_governance_contract_test.py` | PASS |
| 12 | `tests/v25_template_governance_backend_test.py` | PASS |
| 13 | `tests/v24_canva_experience_contract_test.py` | PASS |
| 14 | `tests/v24_collaboration_tasks_backend_test.py` | PASS |
| 15 | `tests/build_integrity_test.py` | PASS |
| 16 | `tests/v10_experience_test.py` | PASS |
| 17 | `tests/v11_media_experience_test.py` | PASS |
| 18 | `tests/v12_storage_privacy_test.py` | PASS |
| 19 | `tests/v12_immediate_stabilization_test.py` | PASS |
| 20 | `tests/v12_routing_context_test.py` | PASS |
| 21 | `tests/v12_media_source_test.py` | PASS |
| 22 | `tests/v13_future_foundation_test.py` | PASS |
| 23 | `tests/v13_account_security_test.py` | PASS |
| 24 | `tests/v13_editor_model_test.py` | PASS |
| 25 | `tests/v13_backup_restore_test.py` | PASS |
| 26 | `tests/v13_product_lifecycle_test.py` | PASS |
| 27 | `tests/v13_privacy_lifecycle_test.py` | PASS |
| 28 | `tests/v14_lifecycle_signing_test.py` | PASS |
| 29 | `tests/v14_performance_budget_test.py` | PASS |
| 30 | `tests/v15_integration_hardening_test.py` | PASS |
| 31 | `tests/v15_http_integration_test.py` | PASS |
| 32 | `tests/v16_windows_ui_hardening_test.py` | PASS |
| 33 | `tests/v17_professional_foundation_test.py` | PASS |
| 34 | `tests/v17_persistence_snapshot_test.py` | PASS |
| 35 | `tests/v19_typography_model_test.py` | PASS |
| 36 | `tests/v19_typography_invalid_input_test.py` | PASS |
| 37 | `tests/v20_typography_architecture_test.py` | PASS |
| 38 | `tests/v22_scene_model_test.py` | PASS |
| 39 | `tests/v22_1_performance_contract_test.py` | PASS |
| 40 | `tests/v22_2_page_experience_contract_test.py` | PASS |
| 41 | `tests/v23_command_registry_test.py` | PASS |
| 42 | `tests/v23_2_navigation_history_contract_test.py` | PASS |
| 43 | `tests/v23_3_style_history_contract_test.py` | PASS |
| 44 | `tests/v23_4_asset_workflow_contract_test.py` | PASS |
| 45 | `tests/v23_5_photo_workflow_contract_test.py` | PASS |
| 46 | `tests/v23_6_photo_style_library_contract_test.py` | PASS |
| 47 | `tests/v23_8_review_operations_contract_test.py` | PASS |
| 48 | `tests/v23_8_review_operations_backend_test.py` | PASS |
| 49 | `tests/v23_7_review_contract_test.py` | PASS |
| 50 | `tests/v23_7_review_backend_test.py` | PASS |
| 51 | `tests/v22_custom_font_upload_test.py` | PASS |
| 52 | `tests/v22_custom_font_server_endpoint_test.py` | PASS |
| 53 | `tests/v22_0_3_khmer_custom_font_quality_test.py` | PASS |
| 54 | `tests/v20_1_stabilization_contract_test.py` | PASS |
| 55 | `tests/v21_0_rich_text_model_test.py` | PASS |
| 56 | `tests/v21_0_rich_text_server_test.py` | PASS |
| 57 | `tests/v21_0_migration_roundtrip_test.py` | PASS |
| 58 | `tests/static_integrity_test.py` | PASS |
| 59 | `tests/smoke_test.py` | PASS |
| 60 | `tests/plan_limit_test.py` | PASS |
| 61 | `tests/final_features_test.py` | PASS |
| 62 | `tests/production_foundations_test.py` | PASS |
| 63 | `tests/provider_adapters_test.py` | PASS |
| 64 | `tests/realtime_storage_test.py` | PASS |
| 65 | `tests/signed_upload_backend_test.py` | PASS |
| 66 | `tests/final_visual_polish_test.py` | PASS |
| 67 | `tests/ux_ai_v5_test.py` | PASS |
| 68 | `tests/pro_editor_v6_test.py` | PASS |
| 69 | `tests/workflow_continuity_test.py` | PASS |
| 70 | `tests/final_workflow_audit_v7_test.py` | PASS |
| 71 | `tests/security_regression_test.py` | PASS |
| 72 | `tests/security_maintenance_test.py` | PASS |
| 73 | `tests/private_access_header_test.py` | PASS |
| 74 | `tests/collaboration_asset_permissions_test.py` | PASS |
| 75 | `tests/optimistic_revision_test.py` | PASS |
| 76 | `tests/collaboration_revision_test.py` | PASS |

## Required browser contracts — all 104 attempted

| # | Contract | Result | Notes |
|---:|---|---|---|
| 1 | `tests/v27_3_5_ai_transaction_browser_test.py` | PASS | Completed without skip. |
| 2 | `tests/v27_3_5_ai_rich_text_browser_test.py` | PASS | Completed without skip. |
| 3 | `tests/v27_3_5_ai_target_revision_test.py` | PASS | Completed without skip. |
| 4 | `tests/v27_3_5_ai_layout_preview_test.py` | PASS | Completed without skip. |
| 5 | `tests/v27_3_5_ai_accessibility_mobile_test.py` | PASS | Completed without skip. |
| 6 | `tests/v27_3_5_mobile_canvas_hud_test.py` | PASS | Completed without skip. |
| 7 | `tests/v27_3_5_typography_preview_sequence_test.py` | PASS | Completed without skip. |
| 8 | `tests/v27_3_4_repair_browser_test.py` | PASS | Completed without skip. |
| 9 | `tests/v27_studio_automation_browser_test.py` | PASS | Completed without skip. |
| 10 | `tests/v27_studio_automation_mobile_test.py` | PASS | Completed without skip. |
| 11 | `tests/v27_studio_automation_performance_test.py` | PASS | Completed without skip. |
| 12 | `tests/v26_studio_operations_browser_test.py` | PASS | Completed without skip. |
| 13 | `tests/v26_studio_operations_mobile_test.py` | PASS | Completed without skip. |
| 14 | `tests/v26_studio_operations_performance_test.py` | PASS | Completed without skip. |
| 15 | `tests/v25_template_governance_browser_test.py` | PASS | Completed without skip. |
| 16 | `tests/v25_template_governance_mobile_test.py` | PASS | Completed without skip. |
| 17 | `tests/v25_template_governance_performance_test.py` | PASS | Completed without skip. |
| 18 | `tests/v24_canva_experience_browser_test.py` | PASS | Completed without skip. |
| 19 | `tests/v24_canva_experience_mobile_test.py` | PASS | Completed without skip. |
| 20 | `tests/v24_export_quality_browser_test.py` | PASS | Completed without skip. |
| 21 | `tests/v24_canva_experience_performance_test.py` | PASS | Completed without skip. |
| 22 | `tests/v23_8_review_operations_browser_test.py` | PASS | Completed without skip. |
| 23 | `tests/v23_8_review_operations_mobile_test.py` | PASS | Completed without skip. |
| 24 | `tests/v23_8_review_operations_performance_test.py` | PASS | Completed without skip. |
| 25 | `tests/v23_7_review_workflow_browser_test.py` | PASS | Completed without skip. |
| 26 | `tests/v23_7_review_mobile_test.py` | PASS | Completed without skip. |
| 27 | `tests/v23_7_review_performance_test.py` | PASS | Completed without skip. |
| 28 | `tests/v23_6_photo_style_library_browser_test.py` | PASS | Completed without skip. |
| 29 | `tests/v23_6_photo_style_library_mobile_test.py` | PASS | Completed without skip. |
| 30 | `tests/v23_6_photo_style_library_performance_test.py` | PASS | Completed without skip. |
| 31 | `tests/v23_5_photo_workflow_browser_test.py` | PASS | Completed without skip. |
| 32 | `tests/v23_5_photo_workflow_performance_test.py` | PASS | Completed without skip. |
| 33 | `tests/v23_4_asset_workflow_browser_test.py` | PASS | Completed without skip. |
| 34 | `tests/v23_4_asset_workflow_performance_test.py` | PASS | Completed without skip. |
| 35 | `tests/v23_3_style_history_browser_test.py` | PASS | Completed without skip. |
| 36 | `tests/v23_3_style_history_performance_test.py` | PASS | Completed without skip. |
| 37 | `tests/v23_2_navigation_history_browser_test.py` | PASS | Completed without skip. |
| 38 | `tests/v23_2_navigation_history_performance_test.py` | PASS | Completed without skip. |
| 39 | `tests/v23_command_system_browser_test.py` | PASS | Completed without skip. |
| 40 | `tests/v23_command_lazy_loader_test.py` | PASS | Completed without skip. |
| 41 | `tests/v23_command_performance_test.py` | PASS | Completed without skip. |
| 42 | `tests/v22_2_page_experience_test.py` | PASS | Completed without skip. |
| 43 | `tests/v22_2_page_refinement_test.py` | PASS | Completed without skip. |
| 44 | `tests/v22_2_page_mobile_test.py` | PASS | Completed without skip. |
| 45 | `tests/v22_2_page_performance_test.py` | PASS | Completed without skip. |
| 46 | `tests/v22_1_4_webgl_backend_test.py` | PASS | Completed without skip. |
| 47 | `tests/v22_1_5_texture_cache_test.py` | PASS | Completed without skip. |
| 48 | `tests/v22_1_6_gpu_projection_test.py` | PASS | Completed without skip. |
| 49 | `tests/v22_1_7_adaptive_gpu_quality_test.py` | PASS | Completed without skip. |
| 50 | `tests/v22_1_7_gpu_editor_integration_test.py` | PASS | Completed without skip. |
| 51 | `tests/v22_1_7_gpu_fallback_test.py` | PASS | Completed without skip. |
| 52 | `tests/v22_1_7_real_webgl_runtime_test.py` | PASS | Completed without skip. |
| 53 | `tests/v22_1_worker_rendering_browser_test.py` | PASS | Completed without skip. |
| 54 | `tests/v22_1_editor_interaction_performance_test.py` | PASS | Completed without skip. |
| 55 | `tests/v22_1_performance_benchmark.py` | PASS | Completed without skip. |
| 56 | `tests/v14_static_server_test.py` | BLOCKED | Managed Chromium policy blocked loopback navigation with ERR_BLOCKED_BY_ADMINISTRATOR before application assertions. |
| 57 | `tests/v14_live_server_acceptance_test.py` | BLOCKED | Managed Chromium policy blocked loopback navigation with ERR_BLOCKED_BY_ADMINISTRATOR before application assertions. |
| 58 | `tests/v14_live_layout_test.py` | BLOCKED | Managed Chromium policy blocked loopback navigation with ERR_BLOCKED_BY_ADMINISTRATOR before application assertions. |
| 59 | `tests/v14_dashboard_mobile_test.py` | BLOCKED | Managed Chromium policy blocked loopback navigation with ERR_BLOCKED_BY_ADMINISTRATOR before application assertions. |
| 60 | `tests/v16_browser_geometry_test.py` | PASS | Completed without skip. |
| 61 | `tests/v17_professional_editor_core_test.py` | PASS | Completed without skip. |
| 62 | `tests/v18_nested_transform_matrix_test.py --case nw` | PASS | Completed without skip. |
| 63 | `tests/v18_nested_transform_matrix_test.py --case n` | PASS | Completed without skip. |
| 64 | `tests/v18_nested_transform_matrix_test.py --case ne` | PASS | Completed without skip. |
| 65 | `tests/v18_nested_transform_matrix_test.py --case e` | PASS | Completed without skip. |
| 66 | `tests/v18_nested_transform_matrix_test.py --case se` | PASS | Completed without skip. |
| 67 | `tests/v18_nested_transform_matrix_test.py --case s` | PASS | Completed without skip. |
| 68 | `tests/v18_nested_transform_matrix_test.py --case sw` | PASS | Completed without skip. |
| 69 | `tests/v18_nested_transform_matrix_test.py --case w` | PASS | Completed without skip. |
| 70 | `tests/v18_nested_transform_matrix_test.py --case finish` | PASS | Completed without skip. |
| 71 | `tests/v17_professional_editor_mobile_test.py` | PASS | Completed without skip. |
| 72 | `tests/v17_layers_clipboard_history_test.py` | PASS | Completed without skip. |
| 73 | `tests/v17_served_editor_test.py` | BLOCKED | Managed Chromium policy blocked loopback navigation with ERR_BLOCKED_BY_ADMINISTRATOR before application assertions. |
| 74 | `tests/v19_typography_runtime_test.py` | PASS | Completed without skip. |
| 75 | `tests/v20_typography_editor_runtime_test.py` | PASS | Completed without skip. |
| 76 | `tests/v20_font_registry_loading_test.py` | PASS | Completed without skip. |
| 77 | `tests/v20_khmer_shaping_test.py` | PASS | Completed without skip. |
| 78 | `tests/v20_typography_accessibility_test.py` | PASS | Completed without skip. |
| 79 | `tests/v20_semantic_style_parity_test.py` | PASS | Completed without skip. |
| 80 | `tests/v22_custom_font_browser_runtime_test.py` | PASS | Completed without skip. |
| 81 | `tests/v22_custom_font_lazy_loader_test.py` | PASS | Completed without skip. |
| 82 | `tests/v22_0_3_khmer_custom_font_browser_test.py` | PASS | Completed without skip. |
| 83 | `tests/v20_1_dashboard_actions_runtime_test.py` | PASS | Completed without skip. |
| 84 | `tests/v20_1_semantic_boundary_runtime_test.py` | PASS | Completed without skip. |
| 85 | `tests/v20_1_bilingual_public_runtime_test.py` | PASS | Completed without skip. |
| 86 | `tests/v20_1_lifecycle_mobile_runtime_test.py` | PASS | Completed without skip. |
| 87 | `tests/v21_0_rich_text_runtime_test.py` | PASS | Completed without skip. |
| 88 | `tests/v21_1_renderer_parity_test.py` | PASS | Completed without skip. |
| 89 | `tests/v21_2_accessible_editing_test.py` | PASS | Completed without skip. |
| 90 | `tests/v21_3_workspace_hardening_test.py` | PASS | Completed without skip. |
| 91 | `tests/v19_server_typography_contract_test.py` | BLOCKED | Managed Chromium policy blocked loopback navigation with ERR_BLOCKED_BY_ADMINISTRATOR before application assertions. |
| 92 | `tests/v19_editor_public_parity_test.py` | PASS | Completed without skip. |
| 93 | `tests/v19_responsive_autofit_test.py` | PASS | Completed without skip. |
| 94 | `tests/v19_font_loading_test.py` | BLOCKED | Managed Chromium policy blocked loopback navigation with ERR_BLOCKED_BY_ADMINISTRATOR before application assertions. |
| 95 | `tests/v19_typography_visual_geometry_test.py` | PASS | Completed without skip. |
| 96 | `tests/inline_editor_runtime_test.py` | PASS | Completed without skip. |
| 97 | `tests/v10_browser_runtime_test.py` | PASS | Completed without skip. |
| 98 | `tests/v11_browser_runtime_test.py` | PASS | Completed without skip. |
| 99 | `tests/v12_browser_stabilization_test.py` | PASS | Completed without skip. |
| 100 | `tests/v13_browser_runtime_test.py` | PASS | Completed without skip. |
| 101 | `tests/editor_layout_geometry_test.py` | PASS | Completed without skip. |
| 102 | `tests/public_layout_runtime_test.py` | PASS | Completed without skip. |
| 103 | `tests/public_guest_feature_runtime_test.py` | PASS | Completed without skip. |
| 104 | `tests/theme_launcher_runtime_test.py` | PASS | Completed without skip. |

## Blocked suites

All seven blocked suites started their test/server process but Chromium rejected the initial `127.0.0.1` navigation with `net::ERR_BLOCKED_BY_ADMINISTRATOR`. The policy was not modified or bypassed:

- `tests/v14_static_server_test.py`
- `tests/v14_live_server_acceptance_test.py`
- `tests/v14_live_layout_test.py`
- `tests/v14_dashboard_mobile_test.py`
- `tests/v17_served_editor_test.py`
- `tests/v19_server_typography_contract_test.py`
- `tests/v19_font_loading_test.py`

## Build, integrity, and focused release checks

- Baseline SHA-256 and safe ZIP path validation: PASS.
- Pristine editor/route/page check-only stage: PASS.
- Regenerate-then-check editor/route/page stage: PASS.
- Python compilation: PASS.
- JavaScript syntax checks: PASS for all top-level JavaScript files.
- Dependency preflight including Chromium launch, Pillow, QR, Argon2, cryptography, Playwright, FontTools, Brotli, and WOFF2: PASS.
- Editor route byte ceiling: PASS.
- README unchanged: PASS.
- Schema version 14: PASS.
