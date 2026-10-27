# 缪尔赛思语气

`dsh-plugin-muelsyse-persona` 往系统提示里加一段可开关的「缪尔赛思」人格：短句、轻快的尾音、爱逗博士；对话与推理都带她的语气，技术内容仍然精确。

## 安装

```powershell
pwsh -File .\install.ps1
```

装完即生效（下一次模型步骤开始），无需重启。

## 控制

```text
GET  /muelsyse-persona/status
POST /muelsyse-persona/enabled   {"enabled": true|false}
POST /muelsyse-persona/toggle
```

`/enabled` 是幂等的：调用方声明目标状态，重复请求不会把开关翻来翻去。

## 覆盖

在 patch 条目里给 `config.persona` 传自己的提示文本即可完全替换；`config.language: "en"` 使用英文版。`config.enabled: false` 则默认关闭。

## 切换

同一时间只应启用一个同伴人格（多个「你是××」段落会互相冲突）。切换方式：在 profile 的 `cordis.patch.yml` 里给旧人格条目加 `disabled: true`、给新人个条目去掉 `disabled`。条目保留不删，随时可逆。
