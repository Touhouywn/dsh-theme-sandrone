# 02 切分（词帽链）

## 目标
句级切片。顺序固定：先词时间戳 → vad → 规则 → 切。

## 输入 / 输出
- 输入：`00-normalized\youngbranch\source-vocals.wav`（没有就用 `source.wav`，见 01.5）
- 输出：`01-slices\youngbranch\` 下 `vad.json`、`segments.json`、`clips\*.wav`、`clips\index.json`；`02-asr\youngbranch.words.json`

## 步骤（每步可单独重跑）
1. 词时间戳（必须先于规则）：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     "E:\AI-theme\muelsyse\.assets-src\voice\v1\pipeline\step02a2_words.py" youngbranch
   ```
   若下载 medium 权重失败：`$env:HF_HOME = "E:\AI-theme\muelsyse\.cache\hf"` 再跑一次；仍失败退 small 并注明。
2. VAD：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     "E:\AI-theme\muelsyse\.assets-src\voice\v1\pipeline\step02a_vad.py" youngbranch
   ```
3. 规则：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     "E:\AI-theme\muelsyse\.assets-src\voice\v1\pipeline\step02b_rules_v4.py" youngbranch
   ```
4. 切：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     "E:\AI-theme\muelsyse\.assets-src\voice\v1\pipeline\step03_cut.py" youngbranch
   ```

## 断言
- tailOverrun 空（rules 的 stdout 统计行）。
- 片长 0.4–10s；0.4–0.6s 标 filler。
- 抽 3 段跑 volumedetect：max_volume > -38 dB。

## 降级表
- tailOverrun 非空 → STOP，贴溢出段清单。
- 静音片 → STOP，贴清单（检查是否复现 v2 的 afade 时间戳问题）。
- whisper medium 单源超 30 分钟 → 改 small 重跑 1 与 03 的 cross。

## 回报
reports：`01-slices\youngbranch\{vad.json,segments.json,clips\index.json}`；diff 里贴片数、时长区间、filler 数。
