# 03 转写 + 双模型互校

## 目标
SenseVoice 主转写 + faster-whisper 逐片复听，算出每片 asrScore。

## 输入 / 输出
- 输入：`01-slices\youngbranch\clips\`
- 输出：`02-asr\youngbranch.json`（SenseVoice，含 textClean）、`02-asr\youngbranch.cross.json`（互校 + asrScore）

## 步骤
1. 主转写：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     "E:\AI-theme\muelsyse\.assets-src\voice\v1\pipeline\step04_asr.py" youngbranch
   ```
2. 互校：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     "E:\AI-theme\muelsyse\.assets-src\voice\v1\pipeline\step04b_crosscheck.py" youngbranch
   ```
3. 回报贴：p10/p50/p90、<0.55 计数、failed 数、emptyGuess 数。

## 断言
- 两份 json 的 items 数与 clips 数一致。
- cross.json 的 model 字段注明 medium 或 small。
- textClean 不含 `<|...|>` 标签；含 → STOP 贴样例。

## 降级表
- medium 权重下载失败 → HF_HOME 指向 `E:\AI-theme\muelsyse\.cache\hf` 再跑；仍失败退 small 并注明。
- 个别片 crosscheck 失败（failed 列表）不拖垮整源；失败片在 cross.json 记 failed。

## 回报
reports：两份 json 路径 + 统计行。
