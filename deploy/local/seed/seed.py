"""Resumable, API-driven local Mastodon fixture population. Secrets stay in data/."""
import argparse
import concurrent.futures as cf
import contextlib
import datetime as dt
import hashlib
import html
import json
import mimetypes
import os
import random
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
MEDIA = DATA / 'media'
BASE = 'https://mastodon.test.com'
CA = str(Path(os.environ['LOCALAPPDATA']) / 'mkcert' / 'rootCA.pem')
DB = sqlite3.connect(DATA / 'state.sqlite3', check_same_thread=False)
DB.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
DB.commit()
LOCK = threading.RLock()
TLS = threading.local()
BOOT = json.loads((DATA / 'bootstrap.json').read_text(encoding='utf-8-sig'))
SECRET = next(x.split('=', 1)[1] for x in (ROOT.parents[2] / '.env.seed.local').read_text(encoding='utf-8-sig').splitlines() if x.startswith('LOCAL_FIXTURE_KEY='))


def get(key):
    with LOCK:
        row = DB.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None


def save(key, value):
    with LOCK:
        DB.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps(value, ensure_ascii=False)))
        DB.commit()
    return value


def session():
    if not hasattr(TLS, 'session'):
        TLS.session = requests.Session()
        TLS.session.verify = CA
        TLS.session.trust_env = False
    return TLS.session


def api(method, path, token=None, body=None, files=None, form=None, key=None):
    cached = get(key) if key else None
    if cached is not None:
        return cached
    headers = {'X-Local-Fixture-Key': SECRET}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if key and method == 'POST' and path == '/api/v1/statuses':
        headers['Idempotency-Key'] = hashlib.sha256(key.encode()).hexdigest()
    for attempt in range(12):
        try:
            with contextlib.ExitStack() as stack:
                parts = {field: (p.name, stack.enter_context(p.open('rb')), mimetypes.guess_type(p.name)[0] or 'application/octet-stream') for field, p in (files or {}).items()}
                response = session().request(method, BASE + path, headers=headers, json=body,
                                             files=parts or None, data=form, timeout=120)
            if response.status_code in (429, 502, 503, 504):
                wait = min(60, max(3, int(response.headers.get('Retry-After', 5 + attempt * 3))))
                time.sleep(wait)
                continue
            if response.status_code >= 400:
                raise RuntimeError(f'{method} {path} {response.status_code}: {response.text[:450]}')
            result = response.json() if response.content and 'json' in response.headers.get('Content-Type', '') else {'ok': True}
            return save(key, result) if key else result
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 11:
                raise
            time.sleep(3 + attempt)
    raise RuntimeError(f'retries exhausted: {method} {path}')


def app_token():
    app = api('POST', '/api/v1/apps', body={'client_name': '本机社区功能测试', 'redirect_uris': 'urn:ietf:wg:oauth:2.0:oob', 'scopes': 'read write follow push'}, key='app')
    return api('POST', '/oauth/token', body={'grant_type': 'client_credentials', 'client_id': app['client_id'], 'client_secret': app['client_secret'], 'scope': 'read write follow push'}, key='app-token')['access_token']


SURNAMES = '林 陈 李 王 张 刘 赵 周 吴 徐 孙 胡 朱 高 郭 何 罗 郑 梁 谢 宋 唐 许 韩 冯 邓 曹 彭 曾 萧 田 董 袁 潘 于 蒋 蔡 余 杜 叶 程 苏 魏 吕 丁 沈 任 姚 陆 方'.split()
GIVEN = '知夏 予安 景行 晓雨 清禾 书宁 星野 沐言 嘉树 思远 一诺 若溪 南舟 以宁 云舒 可欣 亦辰 子墨 沐晴 安然 向晚 明川 乐知 静宜 语桐 初晴 文轩 小满 闻溪 怀瑾'.split()
PEN_A = '慢慢 认真 偶尔 山间 海边 午后 深夜 清晨 窗边 路过 等风 南城 北巷 夏日 秋日 冬日 春日 橘子 柠檬 薄荷 松间 云下 巷口 月下 雨后'.split()
PEN_B = '散步的人 喝咖啡 看云 听雨 拍照片 读两页 养花人 画画 写日记 煮面 留白 追日落 骑单车 数星星 听唱片'.split()
TOPICS = [
 ('城市漫步', '老街', '绕过热闹的主路，才发现街角那家小店还亮着灯。', '你最喜欢城市里的哪个角落？'),
 ('咖啡时间', '窗边', '今天把水温稍微降低了一点，入口的苦味轻了，尾段反而更清楚。', '手冲和拿铁，你平时更常喝哪一种？'),
 ('周末做饭', '厨房', '临时换了手边的食材，意外做出了很喜欢的味道，准备下次再试一次。', '有没有一道你闭着眼都能做好的家常菜？'),
 ('阅读笔记', '图书馆', '读到一段话停了很久，合上书以后，感觉日常的小事也有了新的解释。', '最近哪本书让你愿意慢慢读？'),
 ('摄影练习', '河堤', '同一个位置等了十分钟，云散开之后，整个画面的层次都变了。', '拍照片时你更在意光线还是构图？'),
 ('阳台花园', '阳台', '新叶子终于舒展开了。少浇一点水，多一点耐心，原来真的有用。', '想养一盆好打理的植物，有什么经验？'),
 ('通勤日常', '地铁口', '提前一站下车走了一段路，耳机里的歌还没放完，心情已经轻松了。', '你会给通勤留一点自己的时间吗？'),
 ('音乐分享', '书桌旁', '循环播放的这一小段旋律，第一遍听节奏，第二遍开始留意那些很轻的声音。', '你听音乐时会专门留意哪件乐器？'),
 ('骑行路线', '公园', '今天没有追配速，走走停停，顺便记下了几处适合休息的位置。', '周末骑行，你喜欢平路还是缓坡？'),
 ('整理生活', '房间', '清理抽屉时找到了很久以前的票根，原来一些记忆一直躲在纸片后面。', '你会保留哪些看起来没用的小东西？'),
 ('代码手记', '工作台', '把一个很长的函数拆开以后，错误的位置反而容易找了。先写清楚，再考虑优化。', '你有没有最近才养成的好习惯？'),
 ('画画练习', '画室', '今天只练习明暗关系，没有急着把细节补满，画面反而呼吸起来了。', '开始学画时，哪种练习对你最有帮助？'),
 ('电影闲聊', '客厅', '片尾响起的时候没有立刻关掉，字幕后的那一点安静，和电影本身一样值得停留。', '你喜欢怎样的电影结尾？'),
 ('天气观察', '桥边', '天色从灰蓝慢慢变成橘色，只是抬头几分钟，就觉得今天没有白过。', '你会专门出门看一次日落吗？'),
 ('运动记录', '操场', '今天终于找到舒服的节奏了，不勉强加速，结束时还有余力就很好。', '怎样才能把运动变成长期习惯？'),
 ('小小旅行', '车站', '地图上很近的地方，真正走进去才发现能逛很久。没有赶时间的一天真舒服。', '你喜欢列好清单，还是到了再决定？'),
 ('手作日记', '桌边', '第一次做的边缘还有些歪，不过是自己慢慢完成的，看着就很开心。', '你最近尝试了什么新的手作？'),
 ('面包实验', '烤箱旁', '这次多给面团一点休息时间，切开后的组织比上次均匀，香气也很温柔。', '你喜欢松软的面包还是有嚼劲的？'),
 ('宠物日常', '沙发边', '把新买的垫子放好，它却选择躺在包装纸上。好吧，开心就好。', '你家小动物有什么特别坚持的习惯？'),
 ('夜间随想', '台灯下', '忙完以后倒了一杯温水，把明天要做的事写下来，今天就到这里。', '睡前你会用什么方式放松？'),
]


def identity(i):
    rng = random.Random(1000 + i)
    if i % 3 == 0:
        name = PEN_A[(i // 3) % len(PEN_A)] + PEN_B[(i // 75) % len(PEN_B)]
    else:
        name = SURNAMES[i % 50] + GIVEN[(i // 50 + i % 3 * 10) % 30]
    topic = TOPICS[i % len(TOPICS)][0]
    return {'username': f'{["lin", "yue", "qing", "chen", "mu", "yun", "xia", "zhou"][i % 8]}_{["notes", "walk", "garden", "light", "days", "coffee", "studio", "river"][(i // 8) % 8]}_{i + 1:04d}',
            'display_name': name, 'topic': topic, 'city': rng.choice(['杭州', '成都', '南京', '厦门', '苏州', '广州', '青岛', '昆明', '重庆', '武汉', '上海', '北京'])}


def confirm(email):
    for attempt in range(90):
        r = requests.get('http://localhost:8026/api/v1/search', params={'query': 'to:' + email}, timeout=30)
        r.raise_for_status()
        for message in r.json().get('messages', []):
            detail = requests.get('http://localhost:8026/api/v1/message/' + message['ID'], timeout=30).json()
            text = html.unescape(detail.get('Text', '') + '\n' + detail.get('HTML', ''))
            link = re.search(r'https://mastodon\.test\.com/auth/confirmation\?confirmation_token=[A-Za-z0-9_-]+', text)
            if link:
                result = session().get(link.group(), timeout=45)
                result.raise_for_status()
                return
        time.sleep(2)
    raise RuntimeError('Confirmation message timeout for ' + email)


def register(i, client_token):
    ident = identity(i)
    prefix = f'user:{i}'
    credentials = get(prefix + ':credentials')
    if not credentials:
        credentials = save(prefix + ':credentials', {**ident, 'email': ident['username'] + '@mastodon.test.com', 'password': secrets.token_urlsafe(22)})
    registration = api('POST', '/api/v1/accounts', client_token, body={
        'username': credentials['username'], 'email': credentials['email'], 'password': credentials['password'],
        'agreement': True, 'locale': 'zh-CN', 'time_zone': 'Asia/Shanghai', 'invite_code': BOOT['invite_code']}, key=prefix + ':registration')
    token = registration['access_token']
    if not get(prefix + ':confirmed'):
        confirm(credentials['email'])
        save(prefix + ':confirmed', True)
    photos = sorted(MEDIA.glob('photo-*.jpg'))
    fields = {'display_name': ident['display_name'], 'note': f"住在{ident['city']}，喜欢{ident['topic']}。记录小事，也认真听别人说话。\n本机功能测试用虚构账号。", 'discoverable': 'true', 'indexable': 'false',
              'source[language]': 'zh-CN', 'fields_attributes[0][name]': '常驻', 'fields_attributes[0][value]': ident['city'],
              'fields_attributes[1][name]': '兴趣', 'fields_attributes[1][value]': ident['topic'],
              'fields_attributes[2][name]': '说明', 'fields_attributes[2][value]': '本机演示 / 虚构人物',
              'avatar_description': '用于测试账号的摄影头像，来源 Lorem Picsum'}
    files = {'avatar': photos[i % len(photos)]}
    if i % 4 == 0:
        files['header'] = photos[(i + 27) % len(photos)]
        fields['header_description'] = '摄影封面，来源 Lorem Picsum'
    account = api('PATCH', '/api/v1/accounts/update_credentials', token, form=fields, files=files, key=prefix + ':profile')
    save(prefix, {**credentials, 'token': token, 'id': account['id']})
    return i


def upload(user, filename, key):
    p = MEDIA / filename
    for attempt in range(3):
        upload_key = key if attempt == 0 else key + f':retry:{attempt}'
        if get(upload_key + ':failed'):
            continue
        result = api('POST', '/api/v2/media', user['token'], form={'description': f'本地上传样例：{filename}。摄影来自 Lorem Picsum，音视频来自 Samplelib；格式转换用于兼容性测试。', 'focus': '0.15,-0.1'}, files={'file': p}, key=upload_key)
        try:
            for _ in range(120):
                if result.get('url'):
                    return result['id']
                time.sleep(1)
                result = api('GET', '/api/v1/media/' + result['id'], user['token'])
        except RuntimeError as exc:
            if '422' not in str(exc):
                raise
            save(upload_key + ':failed', {'id': result['id'], 'error': str(exc)})
            time.sleep(2)
    raise RuntimeError('Media processing timeout: ' + filename)


def media_names(kind, i):
    photos = sorted(p.name for p in MEDIA.glob('photo-*.jpg'))
    if kind == 1:
        return [photos[i % len(photos)]]
    if kind == 2:
        return [photos[(i + n * 17) % len(photos)] for n in range(4)]
    return {3: ['photo.png'], 4: ['photo.webp'], 5: ['motion.gif'], 6: ['clip.mp4'],
            7: ['clip.webm'], 8: ['clip.mov'], 9: ['sample.mp3'], 10: ['audio.wav'],
            11: ['audio.ogg'], 12: ['audio.flac'], 13: ['audio.m4a'], 14: ['audio.aac']}.get(kind, [])


def post(user, key, text, kind=0, **extra):
    cached = get(key)
    if cached:
        return cached
    payload = {'status': text, 'visibility': 'public', 'language': 'zh-CN', **extra}
    names = media_names(kind, int(user['username'][-4:]))
    if names:
        payload['media_ids'] = [upload(user, name, f'{key}:media:{n}') for n, name in enumerate(names)]
    return api('POST', '/api/v1/statuses', user['token'], body=payload, key=key)


def daily_posts(i):
    user = get(f'user:{i}')
    deadline = time.monotonic() + 1800
    while not user and time.monotonic() < deadline:
        time.sleep(2)
        user = get(f'user:{i}')
    if not user:
        raise RuntimeError(f'account {i} is not ready')
    topic, place, story, question = TOPICS[i % len(TOPICS)]
    for slot in range(3):
        rng = random.Random(i * 13 + slot)
        when = rng.choice(['今天午后', '清早出门时', '上个周末', '刚才', '昨天下班后', '晚饭之后', '休息的间隙'])
        detail = rng.choice(['手机先放进口袋，让自己安静一会儿。', '下次想约朋友一起，慢一点也没关系。', '随手记下来，过一阵子再回头看。', '没有特别的安排，反而遇到了一点惊喜。', '做完才发现，原来已经过了半个小时。', '先把这件小事做好，就算今天的进度。'])
        text = f'{when}在{place}，{story}\n\n{detail}\n{question}\n#{topic} #生活碎片'
        kind = 0 if slot == 0 else ((i + slot * 7) % 20)
        extra = {}
        if slot == 2:
            extra['visibility'] = ['public', 'public', 'unlisted', 'private'][i % 4]
        if kind == 15:
            extra['poll'] = {'options': ['一个人慢慢来', '和朋友一起', '先看天气', '临时决定'], 'expires_in': 604800, 'multiple': i % 2 == 0, 'hide_totals': i % 3 == 0}
        elif kind == 16:
            extra.update(spoiler_text='一些比较长的个人感受，按需展开', sensitive=True)
            text += '\n\n' + '有时候不必急着给每一天打分。完成了一点点，休息了一会儿，认真和别人说了几句话，就已经很好。' * 3
        elif kind == 17:
            text += '\n延伸阅读：https://zh.wikipedia.org/wiki/摄影'
        elif kind == 18:
            text += '\nA small pause makes the day brighter. ☕🌿\n今日も、ゆっくり。'
        elif kind == 19:
            text += '\n小清单：\n① 留一点空白\n② 记住喜欢的细节\n③ 明天继续 ✨'
        post(user, f'post:{i}:{slot}', text, kind, **extra)
    return i


ROOT_TEXTS = [
 '周末散步相册｜一路上最喜欢的四个停留点。照片各有一点小遗憾，但放在一起，刚好是完整的一天。你会先点开哪张？ #城市漫步 #摄影',
 '动起来的小片段，比静止的画面多了一点呼吸感。你平时会用动图记录什么？ #动图 #生活碎片',
 '把街头的几秒钟留下来：车流、路人、风吹过的树。开声音和静音观看，感觉是不是很不一样？ #视频 #城市观察',
 '这段 WebM 视频的小细节很有意思，欢迎逐帧找找看。你注意到的第一件事是什么？ #视频分享 #观察',
 '今天的小小听音会：先闭眼听一遍，再说说你想到的画面。耳机和扬声器听起来有什么区别？ #音乐 #声音',
 '来做个轻松的周末投票：如果有半天空闲，你最想怎样度过？可以在评论里补充自己的选项。 #投票 #周末计划',
 '把最近关于生活节奏的想法写下来。忙的时候容易忽略休息，其实调整速度也是向前的一部分。欢迎分享各自的小办法。 #长文 #慢生活',
 'PNG 和 WebP 图片小展览：同样是记录画面，细节和色彩的感受也各不相同。你会怎样描述这张图？ #图片 #无障碍描述',
 '用无损音频留下一小段旋律。欢迎从节奏、音色、情绪或者播放体验聊聊，不懂乐理也完全没关系。 #音频 #倾听',
 '今晚的开放话题：分享最近学会的一件小事，可以带图、视频、声音，也可以只写一句话。我们在评论里接着聊。 #社区闲聊 #新发现',
]
ROOT_KINDS = [2, 5, 6, 7, 9, 0, 0, 3, 12, 4]


def roots():
    for j in range(10):
        user = get(f'user:{j}')
        extra = {'quote_approval_policy': 'public'}
        if j == 5:
            extra['poll'] = {'options': ['出门走走', '在家看书', '做点好吃的', '和朋友见面'], 'multiple': True, 'expires_in': 604800}
        if j == 6:
            extra.update(spoiler_text='长文：关于休息与节奏', sensitive=True)
        result = post(user, f'root:{j}', ROOT_TEXTS[j], ROOT_KINDS[j], **extra)
        api('POST', f"/api/v1/statuses/{result['id']}/pin", user['token'], key=f'root-pin:{j}')
    print('10 showcase roots created', flush=True)


OPENERS = ['我刚刚又看了一遍，', '换个角度想，', '看到这里想起一件小事，', '说说我的感受：', '这个话题很适合慢慢聊。', '我也来补充一点，', '午休时认真看完了，', '前面的讨论很有启发，', '刚好最近也在琢磨这个，', '先把自己的小经验放在这里：']
OBSERVATIONS = [
 ['第一张的层次很舒服', '角落里的光线很耐看', '四张一起看比单张更有故事', '留白让画面显得很安静', '树影比建筑本身更吸引我'],
 ['循环的节奏刚刚好', '动作停顿的那一刻很有意思', '短短几秒也能交代气氛', '动态细节让场景鲜活了', '多看几遍会发现新的变化'],
 ['环境声音让画面更立体', '行人的步调和车流形成了对比', '镜头没有急着移动，反而很舒服', '街头的日常总有细节值得看', '这一小段很有生活气息'],
 ['播放很顺畅', '前景和背景的变化值得留意', '同一段画面看两遍感觉不同', '这种短片很适合观察构图', '光线从边缘走过时很漂亮'],
 ['低声部比想象中丰富', '节奏让人自然放松', '戴耳机能听见一些细小的层次', '旋律让我想到傍晚散步', '停顿也是音乐的一部分'],
 ['我会优先选出门走走', '天气好的话想去公园', '有时候在家休息才是最好的安排', '想把时间分一半给朋友，一半给自己', '临时起意的安排也很有趣'],
 ['把事情拆成小步骤很有帮助', '休息之后再回来，往往更容易想明白', '不用每天都拿效率衡量自己', '找到适合自己的节奏，比跟着别人跑更重要', '认真吃饭和睡觉也是生活的一部分'],
 ['细节描述能让更多人理解图片', '色彩之间的关系很舒服', '背景里的纹理值得放大看', '同一张图可以有很多种解读', '补充拍摄环境会更容易想象'],
 ['音色的层次很清楚', '轻一点的声音也值得留意', '熟悉的旋律换设备听会有新感觉', '听完之后房间仿佛安静了一点', '节拍之外的小装饰很有意思'],
 ['学会一点点也很有成就感', '分享失败的过程同样有价值', '很多习惯都是慢慢积累出来的', '有人一起交流，就更愿意继续尝试', '不熟练的时候也可以先开始'],
]
ENDING = ['下次想照着试试看。', '你们会怎样选择呢？', '先记下来，周末再实践。', '欢迎补充不同的看法。', '慢慢来就好。', '谢谢大家把细节讲得这么清楚。', '这一点我以前确实没留意。', '期待后续的分享。', '我准备再观察几天。', '希望这条经验也能帮到别人。', '我可能还需要多尝试几次。', '今天又多了一个小灵感。']


def reply_thread(j):
    root = get(f'root:{j}')
    for k in range(400):
        user_index = (j * 97 + k * 7 + 20) % 1000
        parent = root if k < 300 else get(f'reply:{j}:{(k - 300) * 3 if k < 380 else 300 + k - 380}')
        user = get(f'user:{user_index}')
        if user['id'] in (root['account']['id'], parent['account']['id']):
            user_index = (user_index + 500) % 1000
            user = get(f'user:{user_index}')
        rng = random.Random(j * 10000 + k)
        text = f"@{parent['account']['acct']} " + OPENERS[k % len(OPENERS)] + OBSERVATIONS[j][(k // 10) % 5] + '。' + ENDING[(k // 50 + k % 7) % len(ENDING)]
        text += rng.choice([' 🌿', ' ☕', ' ✨', '', ' 🙂', ''])
        kind, extra = 0, {'in_reply_to_id': parent['id']}
        style = k % 40
        if style in (0, 5, 10, 15, 20, 25, 30):
            kind = {0: 1, 5: 5, 10: 6, 15: 9, 20: 2, 25: 4, 30: 11}[style]
            text += '\n附上一份样例，方便一起讨论。'
        elif style == 2:
            extra['poll'] = {'options': ['很有共鸣', '想再试试', '有不同体验'], 'expires_in': 604800, 'multiple': k % 2 == 0}
        elif style == 4:
            extra.update(spoiler_text='展开看详细想法', sensitive=True)
            text += '\n\n我的顺序是先观察，再记录，最后和别人交流。一次不一定就能得到答案，但是回头看会发现自己确实进步了一点。'
        elif style == 6:
            text += '\n我整理了三点：\n1. 先从简单的开始\n2. 保留当时的感受\n3. 给下次留一点空间'
        elif style == 8:
            text += '\nSmall details make a big difference. いいですね！🌱 #交流'
        elif style == 12:
            extra['quoted_status_id'] = root['id']
        elif style == 14:
            text += '\n参考资料：https://zh.wikipedia.org/wiki/声音'
        elif style == 16:
            text += '\n' + '回想了一下，从开始尝试到现在，最大的变化是没那么着急了。有问题就记下来，有进展也记下来。' * 4
        elif style == 18:
            text += ' :local_motion: :local_color:'
        result = post(user, f'reply:{j}:{k}', text, kind, **extra)
        if k % 25 == 0:
            api('POST', f"/api/v1/statuses/{result['id']}/favourite", get(f'user:{(user_index + 1) % 1000}')['token'], key=f'reply-like:{j}:{k}')
        if k % 100 == 99:
            print(f'thread {j + 1}: {k + 1}/400 replies', flush=True)
    return j


def relationships(i):
    user = get(f'user:{i}')
    for offset in (1, 7, 31):
        target = get(f'user:{(i + offset) % 1000}')
        api('POST', f"/api/v1/accounts/{target['id']}/follow", user['token'], body={'notify': offset == 1, 'reblogs': True}, key=f'follow:{i}:{offset}')
    for j in (i % 10, (i + 3) % 10):
        root = get(f'root:{j}')
        api('POST', f"/api/v1/statuses/{root['id']}/favourite", user['token'], key=f'like:{i}:{j}')
        if i % 3 == 0:
            api('POST', f"/api/v1/statuses/{root['id']}/bookmark", user['token'], key=f'bookmark:{i}:{j}')
        if i % 10 == 0:
            api('POST', f"/api/v1/statuses/{root['id']}/reblog", user['token'], key=f'boost:{i}:{j}')
        if root.get('poll') and i != j:
            api('POST', f"/api/v1/polls/{root['poll']['id']}/votes", user['token'], body={'choices': [i % 4]}, key=f'vote:{i}:{j}')
    return i


def run_parallel(fn, values, label, workers=4):
    failures = []
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, i): i for i in values}
        for n, future in enumerate(cf.as_completed(futures), 1):
            try:
                future.result()
            except Exception as exc:
                failures.append((futures[future], str(exc)))
                print(f'{label} FAILED {futures[future]}: {exc}', flush=True)
            if n % 25 == 0 or n == len(futures):
                print(f'{label}: {n}/{len(futures)}, failures={len(failures)}', flush=True)
    save('failures:' + label, failures)
    if failures:
        raise RuntimeError(f'{label}: {len(failures)} failures; rerun resumes completed operations')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['accounts', 'posts', 'roots', 'replies', 'social', 'all'])
    parser.add_argument('--count', type=int, default=1000)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if args.phase in ('accounts', 'all'):
        token = app_token()
        run_parallel(lambda i: register(i, token), range(args.count), 'accounts', args.workers)
    if args.phase in ('posts', 'all'):
        run_parallel(daily_posts, range(args.count), 'posts', args.workers)
    if args.phase in ('roots', 'all'):
        roots()
    if args.phase in ('replies', 'all'):
        run_parallel(reply_thread, range(10), 'replies', workers=4)
    if args.phase in ('social', 'all'):
        run_parallel(relationships, range(args.count), 'social', args.workers)


if __name__ == '__main__':
    main()
