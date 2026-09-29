"""Resolve repeated display names using other natural given names."""
from seed import GIVEN, api, get, run_parallel, save

seen, changes = set(), {}
for i in range(1000):
    user = get(f'user:{i}')
    name = user['display_name']
    if name in seen:
        for given in GIVEN:
            candidate = name[0] + given
            if candidate not in seen:
                name = candidate
                break
        else:
            raise RuntimeError('No available natural name')
        changes[i] = name
    seen.add(name)


def update(i):
    user = get(f'user:{i}')
    result = api('PATCH', '/api/v1/accounts/update_credentials', user['token'], body={'display_name': changes[i]}, key=f'name-unique:{i}')
    for suffix in ['', ':credentials']:
        record = get(f'user:{i}' + suffix)
        record['display_name'] = changes[i]
        save(f'user:{i}' + suffix, record)
    save(f'user:{i}:profile', result)


run_parallel(update, list(changes), 'unique-names', workers=6)
print('1000 distinct natural display names', flush=True)
