"""Redraft own-thread replies through the API so showcases stay at the top."""
import json
import re
from seed import DB, LOCK, api, get, save

with LOCK:
    rows = [(k, json.loads(v)) for k, v in DB.execute('SELECT key,value FROM state') if re.fullmatch(r'reply:\d+:\d+', k)]
bad = {v['id'] for k, v in rows if v['account']['id'] == get('root:' + k.split(':')[1])['account']['id']}
while True:
    expanded = bad | {v['id'] for _, v in rows if v['in_reply_to_id'] in bad}
    if expanded == bad:
        break
    bad = expanded
users = {get(f'user:{i}')['id']: get(f'user:{i}') for i in range(1000)}
for key, status in sorted(rows, key=lambda row: int(row[1]['id']), reverse=True):
    if status['id'] not in bad:
        continue
    api('DELETE', '/api/v1/statuses/' + status['id'], users[status['account']['id']]['token'], key='redraft-delete:' + status['id'])
    save('redrafted:' + status['id'], status)
    with LOCK:
        DB.execute('DELETE FROM state WHERE key=? OR key LIKE ?', (key, key + ':%'))
        DB.execute('DELETE FROM state WHERE key=?', (key.replace('reply:', 'reply-like:'),))
        DB.commit()
    print('Redrafted ' + key, flush=True)
