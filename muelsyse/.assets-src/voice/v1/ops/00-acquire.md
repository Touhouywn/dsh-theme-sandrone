# 00 获取素材

## 目标
拿到 `sources\BV17z421U71V.m4a`，探测参数、记录 sha256。

## 输入 / 输出
- 输入：B 站 BV17z421U71V（网页已确认标题，时长未知）
- 输出：`sources\BV17z421U71V.m4a`、`sources\probe.json`、`sources\source.sha256`

## 步骤
1. 若 `sources\BV17z421U71V.m4a` 已存在：跳过 2–3，直接做 4。
2. 装 yt-dlp（不要建 venv，用 --target）：
   ```powershell
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     -m pip install --disable-pip-version-check --timeout 20 --retries 2 `
     -i https://pypi.tuna.tsinghua.edu.cn/simple `
     --target E:\AI-theme\muelsyse\.pip-lib yt-dlp
   ```
   清华源失败 → 加 `--proxy http://127.0.0.1:7892` 重试一次；再失败 → HOLD。
3. 下载（音频流优先、m4a 优先）：
   ```powershell
   $env:PYTHONPATH = "E:\AI-theme\muelsyse\.pip-lib"
   & "C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
     -m yt_dlp -f "ba[ext=m4a]/ba/b" `
     -o "E:\AI-theme\muelsyse\.assets-src\voice\v1\sources\BV17z421U71V.%(ext)s" `
     "https://www.bilibili.com/video/BV17z421U71V/"
   ```
   超时 → 加 `--proxy http://127.0.0.1:7892` 重试。落盘扩展名不是 m4a →
   用 ffmpeg 转封装成 `.m4a`（`-c copy`，不重编码）。仍失败 → HOLD。
4. 探测与记账：用 ffmpeg `-i` 取 duration/codec/sampleRate/channels，写 `probe.json`；
   sha256 写 `source.sha256`。断言 duration > 0。
5. 清理：删除 `E:\AI-theme\muelsyse\.venv`（若存在，是废弃产物）。

## 降级表
见 README §8 第 1 行。

## 回报
按 README §7。reports：probe.json 与 source.sha256 的路径；diff 里贴探测到的时长与编码。
