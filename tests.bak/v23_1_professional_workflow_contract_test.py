#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT / "src" / "js" / "professional-workflow-v23.js").read_text(encoding='utf-8')
css=(ROOT / "src" / "css" / "professional-workflow-v23.css").read_text(encoding='utf-8')
route=(ROOT / "docs" / "route-bundle-sources-v15.json").read_text(encoding='utf-8')
required=['transform.mode','transform.commit','layer.isolate','page.previous','page.next','page.movePrevious','page.moveNext','view.rulers','view.guides','view.snapGuides','image.replaceFrame','image.cropLeft','workspace.arrangePanel']
for token in required: assert token in js,token
assert 'performance-loader-v22.js' in route and 'professional-workflow' in (ROOT / "src" / "js" / "performance-loader-v22.js").read_text(encoding='utf-8')
assert (ROOT / "src" / "js" / "professional-workflow-v23.js").is_file() and (ROOT / "src" / "css" / "professional-workflow-v23.css").is_file()
assert 'v23-transform-mode' in css and 'v23-guide-overlay' in css
assert "EInviteProfessionalWorkflow?.transform?.active" in (ROOT / "src" / "js" / "editor-command-system-v23.js").read_text(encoding='utf-8')
print('V23_1_PROFESSIONAL_WORKFLOW_CONTRACT_TEST_PASSED')
