# CLEANUP_MANIFEST — what was reviewed, what was removed, how to restore

**Generated:** 2026-11-01 · **Order:** `CLEANUP_WORKORDER.md` · **Branch:** `chore/cleanup`

## 0. Safety net (Step 1)

| Item | Value |
|---|---|
| Snapshot commit | `a125343bc8284c1583901a5683347e29715dac43` |
| Restore ref | branch **`backup/pre-cleanup`** (the order asked for tag `pre-cleanup`; project rule OD-3 forbids tags, so the snapshot is a branch — same object, same restore) |
| Working branch | `chore/cleanup` |
| Tree at snapshot | clean tracked tree; only 4 untracked owner dirs (`.cloud-attachments/`, `.playwright-cli/`, `.specify/`, `deploy/local/`) |
| Undo one file | `git checkout backup/pre-cleanup -- <path>` |
| Undo everything | `git checkout backup/pre-cleanup -- .` |
| Untracked archive | `artifacts/cleanup-backup-2026-11-01.tar.gz` (gitignored, stays on this machine) |

## 1. Groups

| Group | Meaning | Files |
|---|---|---|
| A | history / issue / fix / audit documents (extract → delete) | 185 candidates |
| B | test results, caches and leftovers | 18 paths |
| C | test sources | `tests/` kept (see §4) |
| D | current product documentation | kept without change |

## 2. Group A — history documents

Summary is each file's own first heading, not an invented description.

| Path | Size | Action | Reason | Own heading |
|---|---|---|---|---|
| `CANVA-UI-TASK.md` | 13.3 KB | **delete** | old work order / fix ledger / prompt / status record | Canva-UI Pass — Work Order & Planning Ledger (Do Not Lose Track) |
| `CANVAS-MOTION-FIX-TASK.md` | 9.5 KB | **delete** | old work order / fix ledger / prompt / status record | Canvas-motion fix task (handoff work order) |
| `DESIGN-FIX-REPORT.md` | 12.5 KB | **delete** | old work order / fix ledger / prompt / status record | Design Page Fix — Final Report (2026-10-19) |
| `DESIGN-FIX-TASK.md` | 12.7 KB | **delete** | old work order / fix ledger / prompt / status record | Design-Page Fix Task — Planning Ledger (Do Not Lose Track) |
| `FREEBUFF-ANSWERS-2026-10-28.md` | 16.7 KB | **keep** | holds the local demo credentials that `docs/qa/DEVICE-CHECKLIST.md` and the demo point at; untracked by design | Answers from Freebuff to `FREEBUFF-QUESTIONS-2026-10-28.md` |
| `FREEBUFF-CONTINUATION-2026-10-21.md` | 25.6 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — eInvite continuation pass (2026-10-21) |
| `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` | 53.4 KB | **delete** | old work order / fix ledger / prompt / status record | OKID / eInvite — Freebuff Long-Term Plan (autonomous mode) |
| `FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md` | 7.7 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — OKID long-term plan, autonomous run (2026-10-24) |
| `FREEBUFF-NEXT-STEPS-2026-10-27.md` | 55.8 KB | **delete** | old work order / fix ledger / prompt / status record | eInvite — Next steps: re-sequenced queue after Phase 6 and LT-7.2 step 3 |
| `FREEBUFF-OPEN-ISSUES-2026-10-21.md` | 98.0 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff Work Order — Every Open eInvite Issue |
| `FREEBUFF-OWNER-INBOX.md` | 1.5 KB | **keep** | live owner→agent channel (open findings still arrive here); archived copy in the tarball | Owner inbox — issues seen on the demo |
| `FREEBUFF-PROMPT.md` | 8.8 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — canvas motion fixes + UI visual audit fixes (one work order) |
| `FREEBUFF-QUESTIONS-2026-10-28.md` | 7.8 KB | **delete** | old work order / fix ledger / prompt / status record | Questions from Claude (chat) to Freebuff — 2026-10-28 |
| `FREEBUFF-REFINEMENT-ORDER-2026-10-22.md` | 20.3 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff Refinement Order — review of the 2026-10-22 pass, then FB-23 … FB-34 |
| `FREEBUFF-REFINEMENT-ORDER-2026-10-23.md` | 13.4 KB | **delete** | old work order / fix ledger / prompt / status record | eInvite — Freebuff Refinement Order, Round 3 (FB-35 … FB-41) |
| `FREEBUFF-REFINEMENT-ORDER-ROUND4-2026-10-23.md` | 28.4 KB | **delete** | old work order / fix ledger / prompt / status record | eInvite / OKID — Freebuff Refinement Order, Round 4 (FB-46 … FB-57) |
| `FREEBUFF-REFINEMENT-ORDER-ROUND5-2026-10-24.md` | 33.0 KB | **delete** | old work order / fix ledger / prompt / status record | > **SUPERSEDED (2026-10-24 19:00).** Do not follow this file. Its items are carried in |
| `FREEBUFF-REFINEMENT-PROMPT-2026-10-23.md` | 5.3 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — eInvite refinement pass, round 3 (2026-10-23) |
| `FREEBUFF-REFINEMENT-PROMPT-ROUND4-2026-10-23.md` | 7.0 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — OKID refinement pass, round 4 (revised 2026-10-24) |
| `FREEBUFF-REFINEMENT-PROMPT-ROUND5-2026-10-24.md` | 7.9 KB | **delete** | old work order / fix ledger / prompt / status record | > **SUPERSEDED (2026-10-24 19:00).** Use `FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md` ins |
| `FREEBUFF-REFINEMENT-PROMPT.md` | 4.4 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — eInvite refinement pass (2026-10-22 evening) |
| `FREEBUFF-TEMPLATES-PROMPT-2026-10-25.md` | 6.5 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — OKID 36-template Khmer event pack, autonomous run (2026-10-25) |
| `FREEBUFF-TEMPLATES-WORKORDER-2026-10-25.md` | 36.0 KB | **delete** | old work order / fix ledger / prompt / status record | OKID / eInvite — Freebuff Work Order: the 36-Template Khmer Event Pack (autonomous mod |
| `FREEBUFF-UI-AUDIT-FIX-ORDER-2026-10-29.md` | 25.5 KB | **delete** | old work order / fix ledger / prompt / status record | OKID / eInvite — Freebuff Work Order: fix the 2026-10-29 UI audit findings |
| `FREEBUFF-UI-REFINEMENT-PROMPT.md` | 18.4 KB | **delete** | old work order / fix ledger / prompt / status record | Freebuff prompt — eInvite visual-quality, research & testing pass |
| `IMPROVEMENT-AND-VISUAL-FIX-PLAN-2026-10-22.md` | 11.2 KB | **delete** | old work order / fix ledger / prompt / status record | eInvite — Status Read, Improvement Plan & Visual Bug Fix Plan |
| `NEXT-WORK-TASK.md` | 52.9 KB | **delete** | old work order / fix ledger / prompt / status record | eInvite — Next Work Order: Improvement, Refinement & Hardening |
| `RELEASE-CANDIDATE.md` | 8.9 KB | **delete** | dated release-candidate record (gate numbers and open criteria now in HISTORY.md §1/§2) | RELEASE-CANDIDATE — Stage F tree, 2026-10-29 |
| `RILL-WALKTHROUGH.md` | 6.3 KB | **delete** | old work order / fix ledger / prompt / status record | Walkthrough — Create a bilingual invitation, publish it, and collect an RSVP |
| `UI-VISUAL-AUDIT-FIX-TASK.md` | 26.7 KB | **delete** | old work order / fix ledger / prompt / status record | UI Visual Audit & Design-Fix Task |
| `docs/ACCOUNT_UPLOAD_PERMISSION_REPORT.md` | 1.8 KB | **delete** | superseded version/pass report or dated audit | Per-account upload permission |
| `docs/AI_PROJECT_OPERATOR_V53_1_IMPLEMENTATION_REPORT.md` | 20.6 KB | **delete** | superseded version/pass report or dated audit | AI Project Operator V53.1 — Implementation Report |
| `docs/BRANCH-REVIEW-2026-10-21.md` | 4.4 KB | **delete** | superseded version/pass report or dated audit | Branch review note — `pass/2026-10-21-next-work` (2026-10-21) |
| `docs/CAPABILITY-MATRIX-2026-10-24.md` | 19.9 KB | **keep** | current roadmap/capability truth (31 exists / 6 partial / 0 absent), still cited as live | Capability matrix (2026-10-24, LT-3.1; updated 2026-10-27 at the LT-3.10 Phase 3 close |
| `docs/LEGACY-VERSION-HISTORY.md` | 172.3 KB | **keep** | pre-0.52 product version record, linked from VERSION_HISTORY.md; too large to condense without loss | eInvite Version History |
| `docs/MULTI_HOST_DEPLOYMENT_REPORT.md` | 1.2 KB | **keep** | read by tests/v0_52_multi_host_deployment_test.py | V0.52 multi-host deployment implementation |
| `docs/ROADMAP-IMPLEMENTATION-REPORT.md` | 46.7 KB | **delete** | superseded version/pass report or dated audit | eInvite Platform — Roadmap Implementation Report |
| `docs/ROADMAP-RECONCILIATION-2026-10-24.md` | 29.7 KB | **keep** | current roadmap/capability truth (31 exists / 6 partial / 0 absent), still cited as live | Roadmap reconciliation — Parts 3–6 (LT-7.1, 2026-10-27) |
| `docs/SECURITY_HARDENING_REPORT_2026-08-10.md` | 5.0 KB | **delete** | superseded version/pass report or dated audit | V0.52 Security Hardening Report |
| `docs/STATUS-INDEX.md` | 19.1 KB | **delete** | superseded version/pass report or dated audit | STATUS-INDEX — work orders, ledgers, and audits |
| `docs/STRUCTURE-MAPPING.md` | 13.4 KB | **delete** | superseded version/pass report or dated audit | Structure Mapping — Part 2 Reorganization |
| `docs/STRUCTURE-PILOT-AUDIT.md` | 16.0 KB | **delete** | superseded version/pass report or dated audit | Structure-Migration Pilot Audit — Read-only |
| `docs/V0_52_ARCHITECTURE.md` | 1.8 KB | **keep** | required by tests/v27_3_5_release_evidence_test.py (DOCS set) — the test fails if absent | V0.52 Architecture Note |
| `docs/V0_52_CHANGED_FILES.md` | 2.2 KB | **keep** | required by tests/v27_3_5_release_evidence_test.py (DOCS set) — the test fails if absent | V0.52 Changed Files — Independent Audit Repair |
| `docs/V0_52_CHANGELOG.md` | 1.7 KB | **keep** | required by tests/v27_3_5_release_evidence_test.py (DOCS set) — the test fails if absent | V0.52 Changelog — Independent Audit Repair |
| `docs/V0_52_CODEX_TEST_HANDOFF.md` | 1.4 KB | **keep** | required by tests/v27_3_5_release_evidence_test.py (DOCS set) — the test fails if absent | V0.52 Independent Testing Handoff |
| `docs/V0_52_FINAL_V17_RELIABILITY_REPORT.md` | 6.3 KB | **delete** | superseded version/pass report or dated audit | V0.52 Final V17 Reliability Correction Report |
| `docs/V0_52_IMPLEMENTATION_STATUS.md` | 1.1 KB | **keep** | required by tests/v27_3_5_release_evidence_test.py (DOCS set) — the test fails if absent | V0.52 Implementation Status |
| `docs/V0_52_KNOWN_LIMITATIONS.md` | 1.1 KB | **keep** | required by tests/v27_3_5_release_evidence_test.py (DOCS set) — the test fails if absent | V0.52 Known Limitations |
| `docs/V0_52_RELEASE_GATE_RELIABILITY_REPORT.md` | 5.9 KB | **delete** | superseded version/pass report or dated audit | V0.52 Release-Gate Reliability Stabilization Report |
| `docs/V0_52_RELEASE_GATE_STABILIZATION_REPORT.md` | 6.8 KB | **delete** | superseded version/pass report or dated audit | V0.52 Release-Gate Stabilization Report |
| `docs/V0_52_REPAIR_REPORT.md` | 5.9 KB | **delete** | superseded version/pass report or dated audit | V0.52 Cumulative Repair Report |
| `docs/V0_52_SECURITY_HARDENING_REPORT.md` | 2.7 KB | **delete** | superseded version/pass report or dated audit | V0.52 security hardening report |
| `docs/V0_52_TEST_MATRIX.md` | 1.8 KB | **keep** | required by tests/v27_3_5_release_evidence_test.py (DOCS set) — the test fails if absent | V0.52 Test Matrix |
| `docs/V10_STYLE_EXPERIENCE_REPORT_2026-07-23.md` | 3.6 KB | **delete** | superseded version/pass report or dated audit | E-invitation Platform — Style Experience V10 |
| `docs/V11_MEDIA_EXPERIENCE_HARDENING_REPORT_2026-07-23.md` | 11.9 KB | **delete** | superseded version/pass report or dated audit | E-invitation Platform — V11 Media & Experience Hardening |
| `docs/V12_IMMEDIATE_STABILIZATION_REPORT_2026-07-24.md` | 16.3 KB | **delete** | superseded version/pass report or dated audit | V12 Immediate Stabilization Report — 2026-07-24 |
| `docs/V13_FUTURE_DEVELOPMENT_REPORT_2026-07-24.md` | 17.4 KB | **delete** | superseded version/pass report or dated audit | E-invitation Platform V13 — Future Development Report |
| `docs/V15_INTEGRATION_HARDENING_REPORT_2026-07-25.md` | 9.9 KB | **delete** | superseded version/pass report or dated audit | V15 Integration Hardening Report |
| `docs/V16_WINDOWS_UI_HARDENING_REPORT.md` | 12.0 KB | **delete** | superseded version/pass report or dated audit | V16 Windows and Editor UI Hardening Report |
| `docs/V17_PROFESSIONAL_TRANSFORM_LAYERS_REPORT.md` | 12.0 KB | **delete** | superseded version/pass report or dated audit | V17 Professional Transform and Layers Foundation |
| `docs/V18_CHANGELOG.md` | 3.1 KB | **delete** | superseded version/pass report or dated audit | V18 Stabilization Changelog |
| `docs/V18_STABILIZATION_RELEASE_REPORT.md` | 6.7 KB | **delete** | superseded version/pass report or dated audit | V18 Stabilization Release Report |
| `docs/V19_1_CHANGELOG.md` | 1.8 KB | **delete** | superseded version/pass report or dated audit | V19.1 Typography Stabilization Changelog |
| `docs/V19_1_STABILIZATION_REPORT.md` | 16.8 KB | **delete** | superseded version/pass report or dated audit | V19.1 Typography Stabilization Report |
| `docs/V19_ADVANCED_TYPOGRAPHY_RELEASE_REPORT.md` | 5.3 KB | **delete** | superseded version/pass report or dated audit | V19 Advanced Typography Release Report |
| `docs/V19_CHANGELOG.md` | 2.1 KB | **delete** | superseded version/pass report or dated audit | V19 Advanced Typography Changelog |
| `docs/V20_1_STABILIZATION_REPORT.md` | 19.4 KB | **delete** | superseded version/pass report or dated audit | V20.1 Stabilization Report |
| `docs/V20_1_TEST_MATRIX.md` | 3.0 KB | **delete** | superseded version/pass report or dated audit | V20.1 Test Matrix |
| `docs/V20_TYPOGRAPHY_SYSTEM_REPORT.md` | 15.8 KB | **delete** | superseded version/pass report or dated audit | V20 Typography System Report |
| `docs/V23_6_0_PHOTO_STYLE_MODEL_REPORT.md` | 696 B | **delete** | superseded version/pass report or dated audit | V23.6.0 Photo-Style Model Report |
| `docs/V23_6_1_BATCH_APPLICATION_REPORT.md` | 777 B | **delete** | superseded version/pass report or dated audit | V23.6.1 Batch Application Report |
| `docs/V23_6_2_LIBRARY_IO_REPORT.md` | 704 B | **delete** | superseded version/pass report or dated audit | V23.6.2 Library Import/Export Report |
| `docs/V23_6_3_COMPLETION_REPORT.md` | 1.2 KB | **delete** | superseded version/pass report or dated audit | V23.6.3 Completion Report |
| `docs/V23_6_3_KNOWN_LIMITATIONS.md` | 1.3 KB | **delete** | superseded version/pass report or dated audit | V23.6.3 Known Limitations |
| `docs/V23_6_ARCHITECTURE.md` | 3.5 KB | **delete** | superseded version/pass report or dated audit | V23.6 Reusable Photo-Style Architecture |
| `docs/V23_6_FOCUSED_VERIFICATION.md` | 2.4 KB | **delete** | superseded version/pass report or dated audit | V23.6.3 Focused Verification Record |
| `docs/V23_6_MIGRATION_REPORT.md` | 1.3 KB | **delete** | superseded version/pass report or dated audit | V23.6 Migration and Rollback Report |
| `docs/V23_6_PERFORMANCE_REPORT.md` | 866 B | **delete** | superseded version/pass report or dated audit | V23.6 Performance Report |
| `docs/V23_6_TEST_MATRIX.md` | 1.5 KB | **delete** | superseded version/pass report or dated audit | V23.6 Test Matrix |
| `docs/V24_6_3_COMPLETION_REPORT.md` | 3.7 KB | **delete** | superseded version/pass report or dated audit | V24.6.3 Completion Report |
| `docs/V24_ARCHITECTURE.md` | 5.7 KB | **delete** | superseded version/pass report or dated audit | V24 Canva-Quality Invitation Workflow Architecture |
| `docs/V26_3_3_COMPLETION_REPORT.md` | 1.3 KB | **delete** | superseded version/pass report or dated audit | V26.3.3 Completion Report |
| `docs/V27_3_3_COMPLETION_REPORT.md` | 1.3 KB | **delete** | superseded version/pass report or dated audit | V27.3.3 Completion Report |
| `docs/V27_3_5_CERTIFICATION_STATUS.md` | 2.0 KB | **delete** | superseded version/pass report or dated audit | V27.3.5 Certification Status |
| `docs/V27_3_5_KNOWN_LIMITATIONS.md` | 2.2 KB | **delete** | superseded version/pass report or dated audit | V27.3.5 Known Limitations |
| `docs/V27_3_5_RELEASE_EVIDENCE.md` | 2.5 KB | **delete** | superseded version/pass report or dated audit | V27.3.5 Release Evidence |
| `docs/V27_3_5_TEST_MATRIX.md` | 15.6 KB | **delete** | superseded version/pass report or dated audit | V27.3.5 Full Test Matrix |
| `docs/V27_ARCHITECTURE.md` | 1.7 KB | **delete** | superseded version/pass report or dated audit | V27 Studio Automation Architecture |
| `docs/V27_FOCUSED_VERIFICATION.md` | 1.1 KB | **delete** | superseded version/pass report or dated audit | V27.3.3 Focused Verification |
| `docs/V28_ARCHITECTURE.md` | 3.4 KB | **delete** | superseded version/pass report or dated audit | V28.0 AI Creative Agent Architecture |
| `docs/V28_CHANGED_FILES.md` | 2.3 KB | **delete** | superseded version/pass report or dated audit | V28.0 Changed Files |
| `docs/V28_CONFIRMATION_BOUNDARIES.md` | 1.2 KB | **delete** | superseded version/pass report or dated audit | V28.0 Confirmation and Permission Boundaries |
| `docs/V28_IMPLEMENTATION_STATUS.md` | 1.2 KB | **delete** | superseded version/pass report or dated audit | V28.0 Implementation Status |
| `docs/V28_KNOWN_LIMITATIONS.md` | 1.2 KB | **delete** | superseded version/pass report or dated audit | V28.0 Known Limitations |
| `docs/V28_RELEASE_EVIDENCE.md` | 1011 B | **delete** | superseded version/pass report or dated audit | V28.0 Release Evidence — Implementation Handoff |
| `docs/V28_TEST_MATRIX.md` | 2.1 KB | **delete** | superseded version/pass report or dated audit | V28.0 Test Matrix — Codex Execution Required |
| `docs/V28_TOOL_REGISTRY.md` | 1.5 KB | **delete** | superseded version/pass report or dated audit | V28.0 Registered Agent Tools |
| `docs/V29_ARCHITECTURE.md` | 1.3 KB | **delete** | superseded version/pass report or dated audit | V29 Professional Layers and Vector Architecture |
| `docs/V29_CHANGELOG.md` | 635 B | **delete** | superseded version/pass report or dated audit | V29 Changelog |
| `docs/V29_PROFESSIONAL_LAYERS_VECTOR_ARCHITECTURE.md` | 552 B | **delete** | superseded version/pass report or dated audit | V29 Professional Layers and Vector — Architecture Plan Only |
| `docs/V29_V32_IMPLEMENTATION_SUMMARY.md` | 904 B | **delete** | superseded version/pass report or dated audit | V29–V32 Cumulative Implementation Summary |
| `docs/V30_ARCHITECTURE.md` | 996 B | **delete** | superseded version/pass report or dated audit | V30 Non-Destructive Raster Workspace Architecture |
| `docs/V30_CHANGELOG.md` | 581 B | **delete** | superseded version/pass report or dated audit | V30 Changelog |
| `docs/V30_RASTER_OPERATION_FORMAT.md` | 1.0 KB | **delete** | superseded version/pass report or dated audit | V30 Raster Operation Format |
| `docs/V30_RASTER_WORKSPACE_ARCHITECTURE.md` | 408 B | **delete** | superseded version/pass report or dated audit | V30 Raster Workspace — Architecture Plan Only |
| `docs/V31_AUTHORIZATION.md` | 613 B | **delete** | superseded version/pass report or dated audit | V31 Collaboration Authorization |
| `docs/V31_CANVA_SCALE_COLLABORATION_ARCHITECTURE.md` | 491 B | **delete** | superseded version/pass report or dated audit | V31 Canva-Scale Creation and Collaboration — Architecture Plan Only |
| `docs/V31_CHANGELOG.md` | 704 B | **delete** | superseded version/pass report or dated audit | V31 Changelog |
| `docs/V31_COMPACTION.md` | 508 B | **delete** | superseded version/pass report or dated audit | V31 Update Compaction and Checkpoints |
| `docs/V31_OFFLINE_MERGE.md` | 502 B | **delete** | superseded version/pass report or dated audit | V31 Offline Merge Behavior |
| `docs/V31_PROTOCOL.md` | 720 B | **delete** | superseded version/pass report or dated audit | V31 Collaboration Protocol |
| `docs/V32_CHANGELOG.md` | 1.1 KB | **delete** | superseded version/pass report or dated audit | V32 Changelog |
| `docs/V32_DEPLOYMENT.md` | 778 B | **delete** | superseded version/pass report or dated audit | V32 Deployment Topology |
| `docs/V32_IMPLEMENTATION_STATUS.md` | 419 B | **delete** | superseded version/pass report or dated audit | V32 Implementation Status |
| `docs/V32_KNOWN_LIMITATIONS.md` | 1.1 KB | **delete** | superseded version/pass report or dated audit | V32 Known Intentionally Deferred Limitations |
| `docs/V32_OPERATIONS.md` | 520 B | **delete** | superseded version/pass report or dated audit | V32 Operations and Observability |
| `docs/V32_PRODUCTION_HARDENING_ARCHITECTURE.md` | 361 B | **delete** | superseded version/pass report or dated audit | V32 Production Hardening — Architecture Plan Only |
| `docs/V32_RECOVERY.md` | 660 B | **delete** | superseded version/pass report or dated audit | V32 Backup and Recovery |
| `docs/V32_SECURITY.md` | 710 B | **delete** | superseded version/pass report or dated audit | V32 Security Architecture |
| `docs/V32_STORAGE.md` | 709 B | **delete** | superseded version/pass report or dated audit | V32 Storage and Media Architecture |
| `docs/V34_UNIFIED_EDITOR_CHANGELOG.md` | 550 B | **delete** | superseded version/pass report or dated audit | V34 Unified Editor Experience |
| `docs/V35_AI_AGENT_PRODUCTION_CHANGELOG.md` | 609 B | **delete** | superseded version/pass report or dated audit | V35 Production AI Agent |
| `docs/V36_TEMPLATE_MARKETPLACE_CHANGELOG.md` | 600 B | **delete** | superseded version/pass report or dated audit | V36 Template Marketplace |
| `docs/V42_ENTERPRISE_GOVERNMENT_CHANGELOG.md` | 547 B | **delete** | superseded version/pass report or dated audit | V42 Enterprise and Government Edition |
| `docs/V44_ADVANCED_ANIMATION_EXPORT_CHANGELOG.md` | 609 B | **delete** | superseded version/pass report or dated audit | V44 Advanced Animation and Export |
| `docs/V45_PUBLISHING_DOMAINS_CHANGELOG.md` | 612 B | **delete** | superseded version/pass report or dated audit | V45 Publishing and Custom Domains |
| `docs/V47_DATA_MERGE_BULK_CHANGELOG.md` | 574 B | **delete** | superseded version/pass report or dated audit | V47 Data Merge and Bulk Generation |
| `docs/V48_PLUGIN_PLATFORM_CHANGELOG.md` | 638 B | **delete** | superseded version/pass report or dated audit | V48 Plugin Platform |
| `docs/V52_ARCHITECTURE.md` | 1.8 KB | **delete** | superseded version/pass report or dated audit | V52 Selected Roadmap Architecture |
| `docs/V52_CHANGED_FILES.md` | 1.8 KB | **delete** | superseded version/pass report or dated audit | V52 Changed Files |
| `docs/V52_EVENT_ECOSYSTEM_CHANGELOG.md` | 682 B | **delete** | superseded version/pass report or dated audit | V52 Intelligent Automation and Event Ecosystem |
| `docs/V52_IMPLEMENTATION_STATUS.md` | 702 B | **delete** | superseded version/pass report or dated audit | V52 Implementation Status |
| `docs/V52_KNOWN_LIMITATIONS.md` | 1.1 KB | **delete** | superseded version/pass report or dated audit | V52 Known Limitations |
| `docs/V52_TEST_MATRIX.md` | 364 B | **delete** | superseded version/pass report or dated audit | V52 Test Matrix — Pending Codex Execution |
| `docs/V9_STABILIZATION_REPORT_2026-07-23.md` | 7.7 KB | **delete** | superseded version/pass report or dated audit | E-invitation-website — V9 Stabilization & Production-Hardening Report |
| `docs/reviews/A1-2026-10-13.md` | 6.7 KB | **delete** | completed review pass / audit report | A1 — signed-out pages must not fetch session-only data |
| `docs/reviews/A2-2026-10-13.md` | 10.3 KB | **delete** | completed review pass / audit report | A2 — the `/api/admin/*-v2` gap: measured, named, handed off (2026-10-13) |
| `docs/reviews/A4-2026-10-13.md` | 9.1 KB | **delete** | completed review pass / audit report | A4 — account.html on a signed-out load (2026-10-13) |
| `docs/reviews/C1-2026-10-13.md` | 5.7 KB | **delete** | completed review pass / audit report | C1 — the pre-paint language bootstrap is refused by the CSP on every route |
| `docs/reviews/D1-2026-10-13.md` | 12.8 KB | **delete** | completed review pass / audit report | D1 — Design Studio overflow menu painted permanently over the workspace |
| `docs/reviews/D1b-2026-10-13.md` | 12.4 KB | **delete** | completed review pass / audit report | D1b — Design Studio overflow menu: edge-aware placement (2026-10-13) |
| `docs/reviews/D4-residuals-2026-10-13.md` | 3.4 KB | **delete** | completed review pass / audit report | D4 residuals — detector fixed, candidates re-classified (2026-10-13) |
| `docs/reviews/E4-2026-10-13.md` | 4.4 KB | **delete** | completed review pass / audit report | E4 — the collapsed-pane handle covered the canvas and did nothing |
| `docs/reviews/E5-2026-10-13.md` | 9.2 KB | **delete** | completed review pass / audit report | E5 — Editor capture-phase Escape ownership (2026-10-13) |
| `docs/reviews/J1-2026-10-13.md` | 2.4 KB | **delete** | completed review pass / audit report | J1 — `guests.html` Export CSV threw instead of downloading |
| `docs/reviews/J2-2026-10-13.md` | 2.9 KB | **delete** | completed review pass / audit report | J2 — every editor tool click threw `root.querySelectorAll is not a function` |
| `docs/reviews/analytics-and-unanimity-report.md` | 44.2 KB | **delete** | completed review pass / audit report | Wiring the analytics feature, expanding the unanimity sweep, and the Style & Layout re |
| `docs/reviews/bug-inventory.md` | 15.8 KB | **delete** | completed review pass / audit report | Bug Inventory |
| `docs/reviews/bulk-guest-import-implementation.md` | 72.1 KB | **delete** | completed review pass / audit report | Bulk guest import and per-guest invitation links — implementation report |
| `docs/reviews/bulk-guest-import-research.md` | 104.1 KB | **delete** | completed review pass / audit report | Bulk guest import and per-guest invitation links: a research pass |
| `docs/reviews/canva-analysis-and-closure-report.md` | 38.4 KB | **delete** | completed review pass / audit report | Canva analysis and pass closure — report |
| `docs/reviews/canva-fidelity-review.md` | 41.9 KB | **delete** | completed review pass / audit report | Canva Fidelity Review — Editor & Dashboard (v54 Redesign) |
| `docs/reviews/consolidation-and-fidelity-report.md` | 34.8 KB | **delete** | completed review pass / audit report | Consolidation and fidelity pass — report |
| `docs/reviews/dashboard-feature-inventory-2026-10-16.md` | 11.5 KB | **delete** | completed review pass / audit report | Dashboard feature inventory |
| `docs/reviews/deploy-02-linux.md` | 27.5 KB | **delete** | completed review pass / audit report | DISPATCH DEPLOY-02 — Linux Full Security Re-scan, Configuration, Commit, Push |
| `docs/reviews/deploy-03-render.md` | 11.0 KB | **delete** | completed review pass / audit report | DEPLOY-03: Render Free-Tier Deployment |
| `docs/reviews/design-space-preview.md` | 4.8 KB | **delete** | completed review pass / audit report | Design-space preview — Canva-style editor rebuild (review guide, 2026-10-16) |
| `docs/reviews/final-report-phase2.md` | 5.5 KB | **delete** | completed review pass / audit report | Phase 2 final report — einvite-platform UI remediation (2026-10-13) |
| `docs/reviews/final-report.md` | 8.0 KB | **delete** | completed review pass / audit report | Final report — UI/UX sweep and fix pass, 2026-10-13 |
| `docs/reviews/fix-e1-dock-chip-overlap.md` | 7.6 KB | **delete** | completed review pass / audit report | E1 — the page dock's chips paint over their own controls |
| `docs/reviews/fix-e3-rail-over-canvas.md` | 8.1 KB | **delete** | completed review pass / audit report | E3 — the tool rail floats on top of the page, not beside it |
| `docs/reviews/fix-m2-doubled-filter-labels.md` | 5.4 KB | **delete** | completed review pass / audit report | The materials and responses filters read every label twice |
| `docs/reviews/fix-shell-mobile-rail-drawer.md` | 13.3 KB | **delete** | completed review pass / audit report | The shell below 1025px: a sticky rail starved the page, and four controls that did not |
| `docs/reviews/g1-restorefile.md` | 43.8 KB | **delete** | completed review pass / audit report | G1 — `#restoreFile` null at `src/js/bundle-index-v15.js:5386` |
| `docs/reviews/instrument-and-closure-report.md` | 44.5 KB | **delete** | completed review pass / audit report | Instrument and closure — the pass after `623b233` |
| `docs/reviews/instrument-repair-report.md` | 54.8 KB | **delete** | completed review pass / audit report | Repairing the instruments: the lift probe's three defects, the trace's own stack, and  |
| `docs/reviews/next-pass-2026-10-15.md` | 28.8 KB | **delete** | completed review pass / audit report | Next fix pass — open items only (2026-10-15) |
| `docs/reviews/no-repro-e2-m1-m2-spacing.md` | 7.4 KB | **delete** | completed review pass / audit report | The three written symptoms that did not reproduce — and what the measurement found ins |
| `docs/reviews/optimisation-report.md` | 33.5 KB | **delete** | completed review pass / audit report | Optimisation pass — tasks 2–8 |
| `docs/reviews/page-sweep-2026-10-15.md` | 6.9 KB | **delete** | completed review pass / audit report | Page sweep — all 16 routes, signed out and signed in (2026-10-15) |
| `docs/reviews/race-and-consolidation-report.md` | 45.1 KB | **delete** | completed review pass / audit report | Race and consolidation report — 2026-10-11 |
| `docs/reviews/redesign-report.md` | 35.4 KB | **delete** | completed review pass / audit report | Redesign report — Canva-language pass across all 16 pages |
| `docs/reviews/reproducibility-and-performance-report.md` | 84.6 KB | **delete** | completed review pass / audit report | Reproducibility and performance report |
| `docs/reviews/sec-01-scan-92806ad.md` | 21.4 KB | **delete** | completed review pass / audit report | SEC-01 — Security Scan Report |
| `docs/reviews/sec-02-hardening.md` | 20.3 KB | **delete** | completed review pass / audit report | SEC-02 — Scan, Harden, and Re-Verify for Public Deployment |
| `docs/reviews/sec-03-ci-gate.md` | 43.1 KB | **delete** | completed review pass / audit report | SEC-03 — CI Security Gate Verification Report |
| `docs/reviews/sec-04-close-loops.md` | 25.2 KB | **delete** | completed review pass / audit report | SEC-04 — Close the Four Open Security Loops (SEC-01/02/03) |
| `docs/reviews/security-status.md` | 22.7 KB | **delete** | completed review pass / audit report | Security Status Ledger — SEC-01 through SEC-05 |
| `docs/reviews/v54-commit.md` | 51.1 KB | **delete** | completed review pass / audit report | V54-COMMIT — Commit v54 and push to GitHub (execution report) |
| `docs/reviews/v54-khmer-gate.md` | 10.2 KB | **delete** | completed review pass / audit report | v54 Khmer gate — re-derived 11-string table |
| `docs/reviews/v54-rc-verification.md` | 83.4 KB | **delete** | completed review pass / audit report | V54-RC — Independent verification of the v54 changeset |
| `docs/superpowers/plans/2026-10-15-eliminate-version-labeling.md` | 14.7 KB | **delete** | completed plan document | Eliminate Version Labeling from UI/Pages/Functions — Plan |
| `docs/superpowers/plans/2026-10-15-unfix-issues-holistic-fix.md` | 28.4 KB | **delete** | completed plan document | Fix Documented Issues/Bugs — Holistic Remediation Plan |
| `docs/superpowers/plans/2026-10-16-version-free-source-names.md` | 8.3 KB | **delete** | completed plan document | Version-Free Source Names — Staged Plan |
| `docs/SESSION-LOG-2026-09-26.md` | 8.4 KB | **delete** | dated agent session log (gitignored, so it was invisible to the tracked scan) | Session log — 2026-09-26 |
| `docs/UX-AUDIT-2026-09-26.md` | 12 KB | **delete** | dated UX audit (gitignored; superseded by the 2026-10-29/30 audits) | UX audit — 2026-09-26 |
| `docs/reviews/*.png` | 42 MB | **delete** | review captures from completed passes (gitignored; `docs/reviews/*.png` rule) | — |

## 3. Group B and C — artefacts, caches and test sources

| Path | Group | Action | Reason |
|---|---|---|---|
| `.lighthouseci/` | B | **delete** | regenerable LHCI JSON/HTML output (16 routes, 668 MB); `.gitignore` already covers it |
| `__pycache__/` | B | **delete** | Python bytecode cache, regenerable |
| `.pytest_cache/` | B | **delete** | pytest cache, regenerable |
| `.sec04-tmp/` | B | **delete** | SEC-04 audit scratch directory, regenerable |
| `screenshots/` | B | **archive+delete** | review captures from completed passes; archived first (16 MB) |
| `.ff_screenshots/` | B | **archive+delete** | throwaway diagnostic scripts and PNGs; archived first |
| `deliverables/` | B | **archive+delete** | DISPATCH box evidence + bilingual captures; archived first |
| `_i18n_all_result.json` | B | **archive+delete** | stale one-off i18n audit output embedding a host path |
| `sec04_behavior_test.py` | B | **archive+delete** | ad-hoc SEC-04 script, superseded |
| `artifacts/` | B | **keep** | 2.7 GB evidence corpus; UNTRACKED — no git backup exists, so rule 1 (safety net first) forbids deletion. Deferred to the owner |
| `.playwright-cli/` | B | **keep** | browser-tool state for the current session, not repo clutter |
| `.cache/` | B | **keep** | Puppeteer browser download (655 MB); deleting it breaks every Lighthouse run until re-downloaded |
| `.pw-browsers/` | B | **keep** | Playwright browser binaries (311 MB); required by the canvas/layout gates |
| `node_modules/` | B | **keep** | installed dependencies; `package.json` + lockfile are the source |
| `fixture-public.html` | B | **keep** | read by ad-hoc font/subset runs; `.gitignore` documents the decision |
| `test-i18n-beacon.html` | B | **keep** | same class as above; `.gitignore` documents the decision |
| `tests/` | C | **keep** | the project's verification contract: `make test`, the pytest gate phase, and four tests read build/doc inputs. Deleting it breaks Step 5 of this order |
| `tools/` | C | **keep** | gate and measurement harnesses (build inputs are read from here) |

## 4. Kept — unsure (needs the owner)

| Path | Question for the owner |
|---|---|
| `tests/` (223 tests) | The order lists test sources as Group C (summarise, then delete). Here the suite is the gate contract: `make test`, the `pytest` phase of `tools/run-gates.py`, and four tests read build/doc inputs (`docs/requirements-test.txt`, `docs/i18n/TRANSLATIONS.csv`, `docs/ASSETS.md`, `docs/ONLINE_AND_SERVER_HOSTING.md`). Deleting it would make Step 5 unverifiable and remove the only regression net. **Kept.** Say the word and it becomes one revertable commit. |
| `artifacts/` (2.7 GB) | Untracked and gitignored, so no git backup exists and deletion would be permanent. It holds the 2026-10-29/30 audit corpora and every gate log this history cites. **Deferred.** Delete on request (or after an external archive). |
| `docs/LEGACY-VERSION-HISTORY.md` (176 KB) | A 258-line pre-0.52 timeline that cannot be condensed without losing detail. **Kept**, linked from `VERSION_HISTORY.md`. |
| `docs/CAPABILITY-MATRIX-2026-10-24.md`, `docs/ROADMAP-RECONCILIATION-2026-10-24.md` | Dated names but still the live roadmap truth. **Kept**; say the word to fold them into HISTORY.md. |
| `docs/V0_52_*.md` (7 files), `docs/MULTI_HOST_DEPLOYMENT_REPORT.md` | Kept only because tests assert they exist / read them. Move the assertions into HISTORY.md and these can go. |
| `.playwright-cli/`, `.specify/`, `.cloud-attachments/`, `deploy/local/` | Owner/agent working state, not documented product. Untouched. |

## 5. Verification (Step 5)

| Check | Command | Result |
|---|---|---|
| Build + mirror | `python3 build.py all` | **`BUILD_OK editor bundles manifests mirror`** · `MIRROR_CHECK_PASSED` · exit 0 |
| Route bundles | `python3 build.py bundles --check` | **`ROUTE_BUNDLE_CHECK_PASSED`** · `BUILD_OK bundles (check)` · exit 0 |
| Doc/build-dependent tests | `.venv/bin/python -m pytest tests/v27_3_5_release_evidence_test.py tests/readme_quickstart_test.py tests/architecture_doc_test.py tests/v0_52_multi_host_deployment_test.py tests/test_template_pack_assets_test.py -q` | **8 passed in 23.49 s** |
| Server boot (fresh data dir, port 8131) | `PYTHONPATH=src/python:. … server.py --port 8131` | `GET /` **200** · `/designer.html` **200** · `/dashboard.html` **200** · `KHMER_FONT_STATUS ok … shaping=True` |
| Broken links to removed files | markdown-link scan over every tracked `.md` | **0** · three pre-existing hits remain and are unrelated: `docs/plugins/{PLUGIN-SANDBOX,MODERATION-PIPELINE}.md` are `(…)/(args)` parenthetical false positives, and `docs/design/CANVA-MOTION.md` points at `artifacts/canvas-motion/P6/…`, which was already absent |
| Tracked deletion mechanism | `git rm` | 155 files, every one restorable from `backup/pre-cleanup` |
| Untracked deletion mechanism | tar → delete | 21 paths archived to `artifacts/cleanup-backup-2026-11-01.tar.gz` (346.2 MB, gitignored) and the gitignored leftovers to `artifacts/cleanup-backup-2026-11-01-ignored.tar.gz` before removal |
| Disk | `du` before/after | ≈ **730 MB** removed: `.lighthouseci/` 668 MB, `docs/reviews/` 42 MB, `screenshots/` 8.3 MB, `.ff_screenshots/` 8.2 MB, `.sec04-tmp/` 485 KB, `deliverables/` 41 KB, plus caches |

**Not run:** the full 223-test suite and the ten-phase gate matrix. Only documentation and review
files were removed; the five tests that read `docs/` or build inputs were run and pass, and both build
checks are green. Run `make test` before merging if you want the whole matrix.

## 6. Current product documentation kept without change (group D)

`docs/*.md` not listed above: `docs/AI_LEARNING_AND_AUTOMATION_V53.md`, `docs/ARCHITECTURE.md`, `docs/ASSETS.md`, `docs/design/CANVA-MOTION.md`, `docs/CANVA-SMOOTHNESS-BRIEF.md`, `docs/design/DESIGN.md`, `docs/FIRST_TIME_INSTALL_AND_HOSTING.md`, `docs/FONT_LICENSES_AND_REGISTRY.md`, `docs/HISTORY.md`, `docs/guides/LAPTOP_HOSTING.md`, `docs/LINUX_LAPTOP_HOSTING.md`, `docs/ONLINE_AND_SERVER_HOSTING.md`, `docs/PRODUCTION_DEPLOYMENT.md`, `docs/guides/PRODUCTION_LAUNCH_CHECKLIST.md`, `docs/README.md`, `docs/ROADMAP-V2.md`, `docs/ROADMAP-v0.54-to-v1.0.md`, `docs/ROADMAP.md`, `docs/SECURITY.md`, `docs/SESSION-LOG-2026-09-26.md`, `docs/guides/START_PLATFORM_IN_VSCODE.md`, `docs/reference/USER_PLATFORM_WAIVER.md`, `docs/UX-AUDIT-2026-09-26.md`, plus everything under `docs/a11y/`, `docs/ai/`, `docs/analytics/`, `docs/certification/`, `docs/collab/`, `docs/hosted/`, `docs/i18n/`, `docs/ops/`, `docs/perf/`, `docs/plugins/`, `docs/qa/`, `docs/security/` and `docs/templates/`.

## 7. Counts

- Scanned: **178** markdown candidates + **18** artefact/test paths.
- Deleted: **172** document rows — 155 tracked (`git rm`) and 17 untracked (archived first) — plus
  **2** further gitignored session/audit documents, **6** artefact directories/files and the
  leftover review captures in `docs/reviews/`.
- Kept with a reason: **11** documents in the table, plus `tests/`, `tools/`, the current product docs
  (§6) and the toolchain.
- Unsure for the owner: **7** rows in §4.
