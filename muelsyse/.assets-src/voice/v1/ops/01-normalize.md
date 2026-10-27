# 01 转码

## 目标
48k 母带 + 16k 工作轨，loudnorm 单遍，写 meta 与校验。

## 输入 / 输出
- 输入：`sources\BV17z421U71V.m4a`
- 输出：`00-normalized\youngbranch\` 下 `source.wav`、`source-16k.wav`、`meta.json`、`source.sha256`

## 步骤
1. 确认预备（README §3）已做。
2. 跑：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     "E:\AI-theme\muelsyse\.assets-src\voice\v1\pipeline\step01_normalize.py" youngbranch
   ```
3. 断言（脚本内置，失败即退出）：48k/16k 时长与源差 ≤ ±0.1s；peak ≤ -1.5 dBFS。

## 降级表
- 48k 失败 → 看 `logs\youngbranch\01-master.log` 尾部，贴错误。
- 16k 失败 → 看 `logs\youngbranch\01-wav16k.log`。

## 回报
reports：`00-normalized\youngbranch\meta.json`；diff 里贴 duration 与 peak 数值。
