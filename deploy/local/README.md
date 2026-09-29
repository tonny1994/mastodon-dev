# 本机 Docker 部署

地址：https://mastodon.test.com

本项目今后所有需要修改 Mastodon 上游源码的定制功能，都按仓库根目录 `AGENTS.md` 的约定制作成独立补丁包，以便跟随官方版本升级。

默认界面语言为简体中文（`DEFAULT_LOCALE=zh-CN`、`FORCE_DEFAULT_LOCALE=true`），不随浏览器语言切换。管理员账号已设为简体中文；用户仍可在个人偏好中选择其他语言。

默认落地页为本地实时动态（`Setting.landing_page=local_feed`）。热门页 `/explore` 只展示达到热度门槛且审核通过的内容；本次 9 条符合条件的展示帖已批准推荐。带内容警告的展示帖按系统规则不会进入热门。

基础服务使用仓库指定的 Mastodon v4.7.2 官方镜像。前端定制位于 `deploy/local/frontend/`，不会修改上游 `app/` 源码。

## 启动与查看状态

在仓库根目录执行：

```powershell
docker compose -f compose.local.yml up -d
docker compose -f compose.local.yml ps
docker compose -f compose.local.yml logs --tail 100 web streaming sidekiq
```

上面的基础 Compose 命令使用官方 Web 镜像。需要定制界面时，再运行下文的 `patch.ps1 Apply`；重新执行基础 `up` 命令也会恢复官方 Web 镜像。

本机 hosts 已包含 `127.0.0.1 mastodon.test.com`。80/443 由相邻 `misskey-dev` 项目的 Nginx 提供，按域名转发。该项目的 `compose.yml` 已挂载本目录的 `nginx.conf` 与 `tls`；Mastodon 的 web/streaming 通过 `misskey-local_external` 网络与代理连接。因此需要保留并运行该代理：

```powershell
docker compose -f ../misskey-dev/compose.yml up -d --no-deps nginx
```

## 证书与密钥

`tls/certificate.pem` 和 `tls/private.key` 是 mastodon.test.com 的本地 HTTPS 证书与私钥，由本机现有、已受 Windows 信任的 mkcert CA 签发，有效期一年。仅用于本机环境；其他设备需另外信任该 CA 才能无警告访问。CA 私钥没有复制到项目或容器。

`.env.production`、`.env.db.local`、证书私钥和 `admin-credentials.txt` 均被 Git 忽略。备份数据库时须同时安全保存 `.env.production` 中的加密密钥。

## 本地邮件和管理员

邮件收件箱：http://localhost:8026 。应用邮件保存在本机 Mailpit，不向外部邮箱投递。

管理员登录凭据保存在本目录的 `admin-credentials.txt`。

## 数据与停止

数据库、Redis、媒体和邮件分别保存在 `mastodon-local_*` Docker 命名卷中。

```powershell
docker compose -f compose.local.yml stop
```

不要使用 `down -v`，除非确实需要删除这些数据。

## “实况”前端补丁

`/explore/live` 在原来的探索标签栏中展示本服务器公开时间线，复用原生分页、访问权限及登录后的实时连接。访客与原生本地时间线一样，通过刷新获取最新内容。

帖子列表、帖子详情和回复链的“回复”操作使用评论气泡图标，避免与转发箭头混淆；实际回复行为不变。

帖子详情页按直接父评论组织回复：子回复缩进呈现。只调整前端显示，不改变嘟文、回复关系或数据库。

评论区用缩进和较小头像区分一级评论与回复，不再显示贯穿整组的线程线；正文中的提及显示回复对象，不再额外重复显示“回复某某”标签。手机和桌面的操作入口保持可用。

一级评论先渲染 20 条，滚动到底部时每次再渲染 20 条，也可点击底部按钮继续；每组二级及更深层回复不超过 3 条时直接展示，超过 3 条时先折叠，首次展开显示 5 条，以后每次再显示 10 条。“收起回复”位于回复组底部，点击后从上往下平滑收起。当前官方 `/context` 接口仍会一次返回整条讨论链，因此这里的“加载”是前端分批渲染，不是服务端分页；未登录访问仍受官方接口最多 60 条后代内容的限制。

回复帖子或评论时，编辑器只自动提及所回复内容的作者；不再把那条内容已提及的其他账号一并带入。回复自己的内容时不预填自己。

根地址 `/` 直接展示同一个实况组件，地址栏保持 `/`，登录用户也适用；新用户必要的引导流程保留。这是前端路由调整，不包含嘟文的服务端渲染。

Mastodon 没有用于替换这些页面路由的主题或插件入口。因此补丁只在构建时修改**官方发布镜像**的前端源码，再生成独立 Web 镜像；数据库、媒体和其他服务保持官方版本。补丁文件及构建上下文都放在 `deploy/local/frontend/`，上游 `app/` 目录保持干净。

在仓库根目录运行以下命令。`Test` 只构建镜像，并检查源码定位、ESLint 和生产编译；失败时不会切换正在运行的网站。`Apply` 先做同样的检查，成功后才切换 Web 容器；`Restore` 一键切回官方 Web 镜像。切换不会清空数据库或媒体。

```powershell
./deploy/local/frontend/patch.ps1 Test
./deploy/local/frontend/patch.ps1 Apply
./deploy/local/frontend/patch.ps1 Restore
```

升级前也可以用 `./deploy/local/frontend/patch.ps1 Test -Version 4.7.3` 对目标官方版本做兼容性检查，而不改变运行中的版本。正式升级时先按 Mastodon 的升级要求更新 `compose.local.yml` 中的官方镜像版本和数据库，再运行 `Test`。只有测试通过才运行 `Apply`；如果源码定位失效或编译失败，先调整补丁，不要强行套用。需要长期保持补丁时，重建 Web 容器应使用 `Apply`，而不是单独执行基础 Compose 的 `up` 命令。
