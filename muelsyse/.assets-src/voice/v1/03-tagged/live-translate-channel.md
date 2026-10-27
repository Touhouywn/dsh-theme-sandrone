# L2 翻译通道 · Pro 预探记录（2026-10-27）

Pro 侧预探结论（flash 在 L2 步骤 0 继续，不必从头试）：

| 探测 | 结果 |
| --- | --- |
| GET /api/models（60596） | `unauthorized`（接口存在，需凭证） |
| POST /api/chat（60596） | `unauthorized` |
| POST /api/chat/completions（60596） | `unauthorized` |
| GET /openapi.json（60596） | 空 |
| ~/.dsh/llm-deepseek | 只有 `files-v3.json`（会话存档，不是 key 文件） |

flash 下一步：
1. 带 DSH 会话凭证重探上述 /api/* 端点（凭证来源：GUI 会话 token 或 profile 配置，只读查）；
2. 探测插件宿主是否有模型调用服务（参照 persona/voice 插件的 inject 名单方式试探）；
3. 都没有 → HOLD 回 Pro，贴原始响应，不自行接第三方 API。

红线：不把任何 key 写进仓库或 ops 文件；凭据只从既有配置读。
