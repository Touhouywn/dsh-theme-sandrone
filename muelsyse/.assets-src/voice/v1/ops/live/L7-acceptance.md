# L7 收尾：延迟表 + 抽听包 + 签字

## 目标
数值收口，产出延迟表与抽听包；听感终审与发布留用户。

## 步骤
1. 延迟表：三组长句（≥3 句/组）实测 TTFB、句间隔、降级触发率、缓存命中率 →
   写 `muelsyse\.assets-src\voice\v1\03-tagged\live-report.md`。
2. 抽听包：合成样段 ≥3 段 + 全部异常段 + 思考音 3 条，落
   `muelsyse\.assets-src\voice\v1\live-listen\*.wav` + 清单 tsv（段 id + 差异点）。
3. 全链 smoke 重跑（L1 断言 + test_client + test_think + test_events）。
4. 写 `live-state.json`（阶段、产物、未决项）。

## 断言
- TTFB ≤5s/句；降级触发率 ≤20%；smoke 全过。
- 数字全落文件，chat 只回 gate 表。

## P2（分两次签字，不合并）
1. 听感终审：合成质量 + 思考音打扰度（用户，用抽听包）；
2. 发布与权利：对外发布、07 人格安装、v1 冻结（用户）。
未签字前不发布；全部产物只在工作区内。
