#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'review-v23.js').read_text(encoding='utf-8');css=(ROOT/'review-v23.css').read_text(encoding='utf-8');server=(ROOT/'server.py').read_text(encoding='utf-8');app=(ROOT/'app.js').read_text(encoding='utf-8');pg=(ROOT/'postgres_schema.sql').read_text(encoding='utf-8');loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8')
assert "const VERSION='23.8.3'" in js
for token in ['review.openActivity','review.configurePolicy','review-context','review-policy','review-notifications','data-review-policy','data-mark-all-read','showPublishReadiness','Publishing policy','Optional publish gate','unreadCount']:
 assert token in js,token
assert "window.addEventListener('keydown'" not in js and "document.addEventListener('keydown'" not in js
assert 'review-v23.js' in loader and loader.index('photo-style-library-v23.js')<loader.index('review-v23.js')
for token in ['CREATE TABLE IF NOT EXISTS invitation_review_policies','CREATE TABLE IF NOT EXISTS review_notifications','def _review_readiness','def review_context','def update_review_policy','def mark_review_notifications','review_gate_blocked','approval_required','unresolved_comments','policy.updated','comment.replied']:
 assert token in server,token
for token in ['invitation_review_policies','review_notifications','idx_review_notifications_user','idx_review_notifications_invite']:
 assert token in pg,token
publish=app[app.index("$('#publishBtn').onclick"):app.index('function refreshPublish()')]
assert publish.index("await api('/api/invitations/'+serverInvite.id+'/publish'")<publish.index('inviteStore.write(publishKey,snap)')
assert "error?.code==='review_gate_blocked'" in publish and 'showPublishReadiness' in publish
for token in ['.v23-review-readiness','.v23-review-policy','.v23-review-notification','.v23-review-activity-list']:
 assert token in css,token
assert js.count("id:'review.openActivity'")==1 and js.count("id:'review.configurePolicy'")==1
print('V23_8_REVIEW_OPERATIONS_CONTRACT_TEST_PASSED')
