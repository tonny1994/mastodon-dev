# 本机测试社区数据

目标：1000 个虚构账号，每人至少 3 条帖子；最新 10 条公开主题帖每条有 300 条直接评论和 100 条多层回复。

所有账号简介都注明为本机测试人物。用户名、密码、访问令牌及下载媒体仅保存在被 Git 忽略的 `data/` 中。

## 实际流程

- `POST /api/v1/apps` 创建客户端，取得客户端令牌。
- `POST /api/v1/accounts` 携带本次专用邀请码注册。
- 从本机 Mailpit API 读取对应邮件，访问邮件中的 HTTPS 确认链接。
- 以每个账号自己的 OAuth 令牌调用 `PATCH /api/v1/accounts/update_credentials`，上传头像和部分封面，填写昵称、简介和自定义字段。
- 将本地文件通过 multipart 上传至 `POST /api/v2/media`，轮询处理状态，再通过 `POST /api/v1/statuses` 发帖、回复。
- 通过 API 完成投票、引用、编辑、点赞、转发、收藏、关注、列表和过滤器等操作。

账号、帖子、评论没有通过 SQL 批量插入。Rails 管理操作只用于创建邀请码、签发临时管理员测试令牌、最终审计和清理。表情包通过官方 `tootctl emoji import` 导入。

`movie-ending-comments.py` 使用现有测试账号经发帖 API 给[电影结尾话题](https://mastodon.test.com/@lin_days_0993/117347485737253727)补充 100 条一级评论及 45 条嵌套回复，用于反复验证 20 条一页的续载，以及 2、3、4、36 条子回复的展开规则。脚本使用固定操作键和幂等请求，可安全重试；不要对别的站点或重建后的数据库复用旧状态。

`compose.seed.yml` 是临时覆盖配置：仅持有随机密钥的注册请求可跳过注册频率限制，其他请求继续使用原有限流。结束后运行普通 `compose.local.yml`，移除运行中的例外并使邀请码失效。站点原本关闭注册的设置保持不变。

## 文件

- `media.py`：下载图片和样例音视频，使用本机已有 FFmpeg Docker 镜像准备格式变体。
- `seed.py`：断点续跑注册、帖子、主题帖、评论和互动。
- `extras.py`、`edge-posts.py`：编辑、权限、短期投票、字数、语言等场景。
- `report.py`、`audit.rb`：分别从公开 API 与数据库只读统计校验结果。
- `data/accounts.json`：1000 个账号的登录邮箱、密码和昵称。
- `data/state.sqlite3`：逐项操作结果和访问令牌，勿公开。
- `data/audit.json`：服务器独立统计。
- `REPORT.md`：最终数量、展示帖入口和覆盖范围。

脚本以确定的操作键保存结果，帖子使用 Idempotency-Key。它们针对本次运行设计；不要在删除数据库或更换域名后沿用旧的 state.sqlite3。重建全新数据时需要新邀请码和新的状态目录。不要把密钥或状态文件提交到 Git。

## 素材来源

摄影头像和照片来自 [Lorem Picsum](https://picsum.photos/)，作者和原图链接保存在 `data/media/photo-sources.json`。100 张源照片在账号间复用，头像并不代表真实人物身份。

音视频及部分格式样例来自 [Samplelib](https://samplelib.com/)，该站说明这些样例可用于测试。具体来源保存在 `data/media/sample-sources.json`。GIF、MOV、OGG、FLAC、M4A、AAC 等部分文件由已下载素材转码而来。上传始终读取本地文件，不使用远程 URL 代替上传。

## 范围

输入覆盖 JPEG、PNG、WebP、GIF、MP4、WebM、MOV、MP3、WAV、OGG、FLAC、M4A、AAC。Mastodon 会将部分输入转为标准 MP4/MP3，因此最终存储格式不一定与上传文件扩展名相同。

覆盖中文为主的多语言文本、长文、链接、话题、提及、四图相册、媒体描述及焦点、内容警告、敏感媒体、单选/多选/隐藏结果/已结束投票、公开/不列出/粉丝/仅提及可见范围、引用、编辑历史、置顶、自定义表情、通知、关注请求、列表、过滤器及预约取消、删除恢复正常列表的流程。

本次没有验证公网联邦互通、真实外发邮件、S3 或 Elasticsearch 全文搜索；这些服务不属于当前本机部署。未登录查看回复时 Mastodon 本身只返回最多 60 条，登录后可看到完整评论树。
