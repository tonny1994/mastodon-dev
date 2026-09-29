import json
from seed import DATA, api, get

admin = json.loads((DATA / 'admin-token.json').read_text(encoding='utf-8-sig'))
for i in range(100):
    user = get(f'user:{i}')
    api('POST', f"/api/v1/accounts/{user['id']}/follow", admin['token'], key=f'admin-follow:{i}')
    if i % 20 == 19:
        print(f'admin follows: {i + 1}/100', flush=True)
for tag in ['生活碎片', '社区闲聊', '摄影']:
    api('POST', f'/api/v1/tags/{tag}/follow', admin['token'], key='admin-tag:' + tag)
