"""Additional reversible feature scenarios, using only the fixture users."""
import datetime as dt
from seed import api, get, post, save


def main():
    for i in range(20):
        user = get(f'user:{i}')
        other = get(f'user:{i + 40}')
        existing = get(f'post:{i}:0')
        source = api('GET', f"/api/v1/statuses/{existing['id']}/source", user['token'], key=f'extra-source:{i}')
        api('PUT', f"/api/v1/statuses/{existing['id']}", user['token'], body={
            'status': source['text'] + '\n\n补记：把遗漏的细节加上了，也修正了一处笔误。谢谢大家认真看完。',
            'language': 'zh-CN'}, key=f'extra-edit-clean:{i}')
        api('GET', f"/api/v1/statuses/{existing['id']}/history", user['token'], key=f'extra-history:{i}')
        post(user, f'extra-direct:{i}', f"@{other['username']} 周末那件小事我整理好了，我们在这里接着聊吧。这个消息仅发给你。", visibility='direct')
        post(user, f'extra-sensitive:{i}', '放一张需要点开查看的图片，用来体验内容提示和图片遮罩。 #图片', 1, spoiler_text='图片展示：按需查看', sensitive=True)
        quoted = get(f'post:{i + 1}:0')
        post(user, f'extra-quote:{i}', '喜欢这段分享，补充一点自己的想法：慢下来之后，很多平时忽略的细节就会浮现。 #交流', quoted_status_id=quoted['id'])
        api('POST', f"/api/v1/accounts/{other['id']}/follow", user['token'], key=f'extra-follow:{i}')
        listing = api('POST', '/api/v1/lists', user['token'], body={'title': '慢慢生活', 'replies_policy': 'list', 'exclusive': False}, key=f'extra-list:{i}')
        api('POST', f"/api/v1/lists/{listing['id']}/accounts", user['token'], body={'account_ids': [other['id']]}, key=f'extra-list-add:{i}')
        api('POST', '/api/v2/filters', user['token'], body={'title': '折叠指定测试词', 'context': ['home', 'public'], 'filter_action': 'warn', 'keywords_attributes': [{'keyword': '折叠演示词', 'whole_word': False}]}, key=f'extra-filter:{i}')
        api('POST', '/api/v1/tags/生活碎片/follow', user['token'], key=f'extra-tag:{i}')
        api('POST', '/api/v1/featured_tags', user['token'], body={'name': user['topic']}, key=f'extra-featured-tag:{i}')
        scheduled = post(user, f'extra-scheduled:{i}', '这是一条预约发布的演示内容。', scheduled_at=(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat())
        api('DELETE', f"/api/v1/scheduled_statuses/{scheduled['id']}", user['token'], key=f'extra-scheduled-cancel:{i}')
        # Exercise create/delete without leaving disposable posts at the top.
        disposable = post(user, f'extra-disposable:{i}', '发布后撤回的临时内容。', visibility='unlisted')
        api('DELETE', f"/api/v1/statuses/{disposable['id']}", user['token'], key=f'extra-delete:{i}')
        print(f'extra scenarios {i + 1}/20', flush=True)
    owner, follower = get('user:50'), get('user:60')
    api('PATCH', '/api/v1/accounts/update_credentials', owner['token'], body={'locked': True}, key='extra-locked')
    api('POST', f"/api/v1/accounts/{owner['id']}/follow", follower['token'], key='extra-follow-request')
    api('POST', f"/api/v1/follow_requests/{follower['id']}/authorize", owner['token'], key='extra-follow-approve')
    for action in ['mute', 'unmute', 'block', 'unblock']:
        api('POST', f"/api/v1/accounts/{get('user:62')['id']}/{action}", get('user:61')['token'], key='extra-' + action)
    save('extras-complete', True)


if __name__ == '__main__':
    main()
