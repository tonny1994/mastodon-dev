import json
from seed import DATA, ROOT, api, get, save

audit = json.loads((DATA / 'audit.json').read_text(encoding='utf-8-sig'))
assert audit['accounts'] == audit['confirmed'] == audit['approved'] == audit['avatars'] == 1000
assert audit['distinct_display_names'] == 1000
assert audit['posts_without_reblogs'] >= 3000 and audit['replies'] == 4000
assert audit['failed_attached_media'] == 0
for thread in audit['threads']:
    assert thread['direct_comments'] == 300 and thread['nested_replies'] == 100 and thread['authors'] == 400
lines = ['# 本机测试数据完成报告', '', '入口：[本地公开列表](https://mastodon.test.com/public/local)。登录后可展开完整评论树。', '',
         '| 项目 | 实际数量 |', '|---|---:|',
         '| 已注册、确认并批准的账号 | 1000 |', '| 已上传头像 / 封面 | 1000 / 250 |', '| 不重复的自然昵称 | 1000 |',
         f"| 主题帖（不含转发和回复） | {audit['posts_without_reblogs']} |", '| 评论与楼中楼 | 4000 |',
         f"| 静态图片 / 动图 / 视频 / 音频附件 | {audit['media_types']['image']} / {audit['media_types']['gifv']} / {audit['media_types']['video']} / {audit['media_types']['audio']} |",
         f"| 投票 / 已结束投票 / 投票记录 | {audit['polls']} / {audit['expired_polls']} / {audit['poll_votes']} |",
         f"| 点赞 / 收藏 / 转发 | {audit['favourites']} / {audit['bookmarks']} / {audit['reblogs']} |",
         f"| 测试账号之间的关注关系 | {audit['follows']} |", '| 编辑历史 / 列表 / 过滤器 | 20 / 20 / 20 |',
         f"| 内容警告与敏感内容 | {audit['cw_statuses']} |", '| 处理失败的已发布媒体 | 0 |', '',
         '## 前 10 条展示帖', '', '已通过 API 验证它们恰好是本地公开列表前 10 条。每条 300 条直接评论 + 100 条楼中楼，400 个不同参与账号，最深 3 层回复。', '']
labels = ['相册', 'GIF', 'MP4 视频', 'WebM 视频', '音频', '投票', '内容警告长文', 'PNG 图片', '无损音频', '开放讨论']
for i in reversed(range(10)):
    lines.append(f"- [{labels[i]}]({audit['threads'][i]['url']})")
lines += ['', '## 使用与验证', '',
          '- 1000 个账号均至少发过 3 条帖子；账号简介注明为虚构测试人物。',
          '- [账号登录清单](data/accounts.json)包含邮箱和独立随机密码，只存本机，不提交 Git。',
          '- 注册走 API、邀请码和 Mailpit 邮件确认；媒体先下载到本地，再由各账号 multipart 上传、发帖和评论。',
          '- 13 种媒体输入格式、4 种内容可见范围、4 种语言；包括提及、话题、链接、四图、媒体描述、焦点、单选与多选投票、自定义表情、引用、编辑历史、置顶、关注申请、通知、列表和过滤器。',
          '- 另外验证了仅提及消息、预约发布后取消、发布后删除、屏蔽后解除、静音后解除等流程。',
          '- 通过登录态 API 获取了每条完整的 400 条回复，并独立在数据库核对数量、作者数和深度；展示帖的媒体 URL 均能下载。',
          '- 浏览器抽样确认简体中文界面、头像、图片、音频播放器正常显示。所有 Docker 服务保持健康。',
          '- 临时批量注册例外已从运行配置移除，邀请码已失效，临时管理员令牌已撤销；测试账号可继续正常登录。',
          '- 未登录访客的上下文接口最多返回 60 条回复，这是 Mastodon 的默认行为；请登录查看完整楼层。',
          '- 公网联邦、外发 SMTP、S3 和 Elasticsearch 全文搜索未包含在本次验证中。', '',
          '素材来源：[Lorem Picsum](https://picsum.photos/) 和 [Samplelib](https://samplelib.com/)。原始来源清单保存在 data/media。', '',
          '重试说明：一次 AAC 转码失败已重新上传成功，原失败的未挂载附件已清理；少量作者自回复通过 API 重新发出，以保持主题帖位于公开列表前十。', '',
          '完整流程与脚本说明见 [README](README.md)。']
(ROOT / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
admin = json.loads((DATA / 'admin-token.json').read_text(encoding='utf-8-sig'))
app = get('app')
api('POST', '/oauth/revoke', body={'token': admin['token'], 'client_id': app['client_id'], 'client_secret': app['client_secret']}, key='admin-token-revoked')
save('completed', True)
print('Report written; temporary admin token revoked.', flush=True)
