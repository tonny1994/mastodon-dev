"""Export credentials locally and prepare independent server-side count checks."""
import json
from seed import DATA, DB, LOCK, api, get

users = [get(f'user:{i}') for i in range(1000)]
assert all(users), 'Missing completed accounts'
roots = [get(f'root:{j}') for j in range(10)]
assert all(roots), 'Missing showcase roots'
credentials = [{k: u[k] for k in ['username', 'display_name', 'email', 'password', 'id']} for u in users]
(DATA / 'accounts.json').write_text(json.dumps(credentials, ensure_ascii=False, indent=2), encoding='utf8')
(DATA / 'audit-input.json').write_text(json.dumps({'account_ids': [u['id'] for u in users], 'roots': [r['id'] for r in roots]}), encoding='utf8')
timeline = api('GET', '/api/v1/timelines/public?local=true&limit=10', users[0]['token'])
expected = [r['id'] for r in reversed(roots)]
assert [s['id'] for s in timeline] == expected, 'Public timeline top ten differ from showcase roots'
for j, root in enumerate(roots):
    thread = api('GET', f"/api/v1/statuses/{root['id']}/context", users[0]['token'])
    assert len(thread['descendants']) == 400, (j, len(thread['descendants']))
    fresh = api('GET', f"/api/v1/statuses/{root['id']}", users[0]['token'])
    print(f"root {j + 1}: context={len(thread['descendants'])}, direct={fresh['replies_count']}", flush=True)
    for attachment in fresh['media_attachments']:
        response = __import__('requests').get(attachment['url'], verify=__import__('seed').CA, headers={'Range': 'bytes=0-1023'}, timeout=30)
        response.raise_for_status()
admin = json.loads((DATA / 'admin-token.json').read_text(encoding='utf-8-sig'))
home = api('GET', '/api/v1/timelines/home?limit=40', admin['token'])
assert home, 'Admin home timeline is empty'
with LOCK:
    failures = [json.loads(v) for (v,) in DB.execute("SELECT value FROM state WHERE key LIKE 'failures:%'")]
print('API validation passed: top 10 roots, 400 descendants each, media downloads and populated admin home.', flush=True)
