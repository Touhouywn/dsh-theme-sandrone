# L6 muelsyse:voice 事件契约 v1

## 目标
浏览器半边发声与思考过程收敛为版本化事件契约：`speak-start` / `segment-start` / `speak-end` /
`thinking-phase` / `level`；字段只增不改，消费方按 `v` 协商。

## 步骤
1. 写 `EVENTS-SPEC.md`（唯一真源，参照 columbina 版改命名空间）：
   事件表、版本规则、顺序保证、已知缺口、适配器指引。
2. client.js 按 spec 实现：`emitEvent`（统一注入 v/at）、五类事件、fallback 继承 index。
3. `tools\test_events.mjs`：7 断言（参照 columbina）。

## 参数冻结
| 项 | 值 |
| --- | --- |
| 命名空间 | `muelsyse:voice:` |
| v | 恒 1；消费方先校验 |
| 顺序 | speak-start < segment-start(0..n) < speak-end |
| level | dBFS；synth 流按块、wav 播前一次、clip 段 v1 不发（记录在案） |
| fallback | 继承被替换 synth 段的 index |
| 破坏性变更 | 新事件名加 `-v2`，旧名保留一个发布周期 |

## 评审
Pro 按 spec 全读一次（本稿已按 Pro 等级评审）；v1 冻结签字 = P2 用户。

## 降级表
| 情况 | 动作 |
| --- | --- |
| 事件 API 不可用 | emitEvent 静默跳过，发声不受影响 |
| 消费方校验 v≠1 | 按版本规则协商 |
