#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'review-v23.js').read_text(encoding='utf-8');css=(ROOT/'review-v23.css').read_text(encoding='utf-8');loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8');server=(ROOT/'server.py').read_text(encoding='utf-8');pg=(ROOT/'postgres_schema.sql').read_text(encoding='utf-8')
assert "const VERSION='23.8.3'" in js
for token in ['review.open','review.addComment','review.requestApproval','review.togglePins','Mod+Alt+Shift+M','data-place-comment','data-reply-form','data-request-approval','data-decide-approval','commentPin','EInviteReviewWorkflow','review data is private to collaborators','500000','slice(0,100)','document.addEventListener(\'pointerdown\',onStagePointer,true)']:
 assert token in js,token
assert "window.addEventListener('keydown'" not in js and "document.addEventListener('keydown'" not in js
assert 'review-v23.js' in loader and loader.index('photo-style-library-v23.js')<loader.index('review-v23.js')
for token in ['page_id TEXT NOT NULL DEFAULT','parent_id TEXT NOT NULL DEFAULT','anchor_x REAL NOT NULL DEFAULT -1','document_revision INTEGER NOT NULL DEFAULT 0','document_fingerprint TEXT NOT NULL DEFAULT','summary_json TEXT NOT NULL DEFAULT','def delete_comment','comment.added','approval.requested','approval.decided','current_fingerprint','item["stale"]']:
 assert token in server,token
assert '"/comments/" in path and path.count("/")==5:return self.delete_comment' in server
for token in ['anchor_x DOUBLE PRECISION','document_fingerprint TEXT','decided_at BIGINT','idx_invitation_comments_parent']:
 assert token in pg,token
for token in ['.v23-review-drawer','.v23-review-pin-layer','.v23-review-pin','.v23-review-thread','.v23-approval-card','@media(max-width:720px)']:
 assert token in css,token
assert js.count("id:'review.open'")==1
print('V23_7_REVIEW_CONTRACT_TEST_PASSED')
