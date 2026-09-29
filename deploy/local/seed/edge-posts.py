from seed import api, get, post

for i in range(10):
    user = get(f'user:{i + 70}')
    post(user, f'edge-short-poll:{i}', '五分钟小投票：现在最想来一杯什么？投票结束后一起看结果。 #投票', poll={'options': ['清水', '茶', '咖啡', '果汁'], 'expires_in': 300, 'multiple': False, 'hide_totals': True})
    post(user, f'edge-cw-media:{i}', '分享一段需要展开后播放的小视频。 #视频', 6, spoiler_text='媒体播放演示', sensitive=True)
    post(user, f'edge-emoji:{i}', '给今天留一点颜色 :local_color: 也留一点动感 :local_motion: 🌈🎉 #小确幸')
    post(user, f'edge-filter:{i}', '这条包含折叠演示词，用于体验关键词过滤后的提示效果。 #功能体验', visibility='unlisted')
user = get('user:90')
for code, text in [('en', 'An ordinary afternoon, a warm cup of tea, and a few quiet moments. What small thing made you smile today? #SlowLiving'), ('ja', '今日は少し遠回りして帰りました。いつもの道にも、小さな発見がありますね。 #日常'), ('zh-TW', '今天沿著河邊慢慢走，發現熟悉的風景也會因為光線不同而改變。 #生活筆記')]:
    post(user, 'edge-language:' + code, text, language=code)
post(user, 'edge-near-limit', ('把日常的小事认真记下来，有光、有风，也有片刻安静。' * 19)[:480] + '\n#长文')
print('Short polls, sensitive video, custom emoji, filters and multilingual posts ready', flush=True)
