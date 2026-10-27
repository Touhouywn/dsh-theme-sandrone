# 06 发布（P0 自动 + P2 签字）

## 目标
usable 行（status=ok 且 asrScore ≥ 0.55）的切片进发布库。

## 输入 / 输出
- 输入：`03-tagged\aligned.tsv`、`01-slices\youngbranch\clips\*.wav`
- 输出：`07-release\clips\CN_<prts_idx>.wav`、`07-release\manifest.json`；旧版先备份 `backup\release-pre-<ts>\`

## 步骤
1. 命名：按 skeleton 的 cn_audio 列（CN_001.wav … CN_044.wav，三位零填充；只出现骨架中存在的 38 个）。
2. 复制到 `07-release\clips\`；manifest.json 含 aligned.tsv 全字段 + 文件 sha256。
3. 07-release 已存在 → 先备份 `backup\release-pre-<ts>\` 再覆盖。
4. smoke：
   - 文件数 = usable 行数；
   - 每文件存在且 volumedetect max_volume > -60；
   - manifest 可解析且 id 无重复。
5. smoke 任一失败 → 用备份回滚，报 STOP。

## P2（用户，不自动做）
素材授权确认、抽听签字（05 清单）、发布。本阶段 verdict 到 PASS 为止，发布动作等用户。

## 回报
reports：manifest.json + smoke 结果。
