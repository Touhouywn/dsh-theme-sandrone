# 公开发布检查清单

公开之前，按这个顺序过一遍。任何一项没确认，就先停在私有仓库。

## 1. 权利

- [ ] 角色美术、开屏视频、语音、配乐是否有公开再分发的许可或明确授权？
- [ ] 如果不用第三方素材，是否已移除 `assets/` 中的角色图、`opening-art.webp`、`trace.mp4`、`opening.json`、语音配乐和含角色形象的截图？
- [ ] `ASSET-LICENSE.md`、`PROVENANCE.json`、`CREDITS.md` 与实际文件一致？

## 2. 账号

- [ ] GitHub 账号已开启 2FA，恢复码已保存。
- [ ] Settings → Sessions 没有不认识的登录。
- [ ] Settings → Applications 里没有不认识的 Authorized OAuth Apps。
- [ ] Settings → Developer settings → Personal access tokens 里没有多余、无期限的 token。
- [ ] 自动化使用最小权限、带过期时间的凭据，不把 token 写进脚本或仓库。

## 3. 仓库

- [ ] 公开仓库的 Secret Scanning 已启用。
- [ ] Push Protection 已启用。
- [ ] `main` 分支有保护规则（至少禁止强推、要求审查）。
- [ ] 如果添加 GitHub Actions：固定 action 到 SHA、最小 `permissions`、要求工作流审批、不在 `pull_request_target` 里检出 PR 代码。
- [ ] 没有不必要的 deploy key、webhook、协作者或 fork。

## 4. 隐私

- [ ] 提交邮箱使用 GitHub noreply，不是真实邮箱；旧提交是否要改写历史？
- [ ] 截图里没有工作区名、会话标题、本机路径、聊天内容或个人数据。
- [ ] `PROVENANCE.json` / README / 脚本里没有绝对路径、账号、Cookie 或本机用户名。
- [ ] 安装日志、`cordis.patch.yml.bak-*`、`.research/` 没有被一起提交。

## 5. 内容与构建

```powershell
node dsh-theme-sandrone/tools/smoke.mjs
node dsh-theme-sandrone/tools/audit-tokens.mjs <DSH 客户端包> [theme.css] [app.css]
python tools/build-release.py
```

- [ ] 工作树、提交历史、悬空 blob、issue/评论/Release/Gist 都做过密钥扫描。
- [ ] `dist/dsh-theme-sandrone-<version>.zip` 里没有 `.env`、Token、私钥、数据库连接串。
- [ ] 从 zip 在一个空的 DSH 目录里装一遍、卸一遍。
- [ ] 开屏预览跑一遍：`python preview/serve-opening.py`。
- [ ] `SHA256SUMS-v<version>.txt` 与 zip 对应。

## 6. 发布

- [ ] 版本号在 `dsh-theme-sandrone/package.json` 与 `CHANGELOG.md` 一致。
- [ ] Release 说明写清安装步骤、兼容版本、素材权利提示。
- [ ] 上传 zip 与 SHA-256，下载后核对哈希。
- [ ] 公开后 24 小时内检查一次 Secret Scanning / Dependabot / 新 Issue。

## 7. 事后

- [ ] 订阅仓库通知，密钥类告警第一时间处理。
- [ ] 任何曾经进过公开仓库的 Key，都先轮换，再清历史。
- [ ] 把本次发布用到的 token / 临时脚本从本机清掉。
