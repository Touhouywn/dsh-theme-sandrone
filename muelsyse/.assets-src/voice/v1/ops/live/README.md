# 缪尔赛思实时语音 · live 执行稿总纲

> 给 flash。依据 `docs\voice-live-muelsyse-plan.md`。用户已确认五项：
> 无麦克风输入、中文正文中译日、官方切片可做 TTS 参考、插件放新包、思考音要切。
> 07 人格未定，本链不碰 cordis.patch.yml。
> 顺序 L1→L7，每份 brief 独立可重跑；Pro 出 brief 与听感初判，flash 只执行，用户做终审。

## 1. 推理等级（写死）

| 角色 | 默认 | 上限 | 规则 |
| --- | --- | --- | --- |
| flash | low | medium | P0 数值、脚本、按 brief 写码 = low；无先例代码骨架 = medium（每阶段仅一次）；开 high 即违规退回 |
| Pro | medium | high | 审查（gate 表、diff、异常段）= medium；设计（契约字段、分相映射、降级梯、新参数）= high；抽听 = high |
| 用户 | — | — | 听感终审、权利、发布 |

flash → Pro 升级触发：参数无先例；降级触发率 >20%；断言失败是设计问题；任何听感判定。

## 1.5 质量与 token（用户定调：质量优先，节 token 只在质量锚点之内）

省 token 措施：A1 指令外置、A2 回报 ≤8 行 + 全量落文件、A3 state.json 快照、A4 定向读；
音频不可 diff 一律数值化（延迟 ms、片长、分贝、触发率）；DOM 以快照 JSON 回报；契约 spec 唯一真源。

质量锚点（以下不省）：合成抽听每阶段 ≥3 段 + 全部异常段；契约 Pro 完整读 spec 一次；
发布 smoke 断言全跑；听感终审与发布签字分两次（新链路首次，不合并）。


## 2. 路径与环境（写死）

| 项 | 值 |
| --- | --- |
| 新插件源 | `E:\AI-theme\muelsyse\dsh-plugin-muelsyse-voice\`（L1 建） |
| 参照实现 | `E:\AI-theme\columbina\dsh-plugin-columbina-voice\` |
| 语音库 | `E:\AI-theme\muelsyse\.assets-src\voice\v1\`（catalog 源 = `03-tagged\aligned.tsv` + `07-release\`） |
| 准备件 | `muelsyse\.assets-src\voice\v1\live-prep.md`（术语表/参考音频/思考音/架构事实，只读） |
| GUI 端口 | 会变（历史 61212→60596）；先 `curl /columbina-voice/status` 定端口，全程用命中端口 |
| 红线 | 参考音频只许缪尔赛思官方切片；不做跨角色回退；不对外发布（P2） |

## 3. 命名（全部替换，勿混用）

ROUTE=`/muelsyse-voice`；环境变量 `MUELSYSE_TTS_*`；事件命名空间 `muelsyse:voice:`；
插件包名 `dsh-plugin-muelsyse-voice`；patch id `muelsyse-voice`；缓存目录 `%TEMP%\muelsyse-voice-cache\`。

## 4. 回报格式（每阶段回一次）

```
verdict: PASS|HOLD|STOP
changed: <每行一个文件>
diff: <≤10 行>
anomalies: <id 列表或 []>
reports: <落盘路径>
```

## 5. gate 表模板（每阶段只回这张表）

```
阶段 | 产物路径 | 指标 vs 门槛 | 异常 id | 未决项(≤3)
```

## 6. 阶段索引

| 稿 | 内容 |
| --- | --- |
| L1-catalog.md | 插件骨架 + catalog/templates/剪辑复制 |
| L2-speak.md | /speak 混合路由 + 翻译通道探测 + 检索 |
| L3-tts.md | synth.js 适配 + 引擎拉起 + 参考档 |
| L4-client.md | 浏览器半边：watcher + 混合播放 |
| L5-thinking.md | 思考 watcher + 切 3 条短音 + thinking.json |
| L6-events.md | muelsyse:voice 事件契约 v1 |
| L7-acceptance.md | 延迟表 + 抽听包 + 签字 |
