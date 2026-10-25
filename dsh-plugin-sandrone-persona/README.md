# Sandrone · 语气

让 DSH 的对话带上「桑多涅」的语气。宿主插件只做一件事：向系统提示里注册一个可配置的段落。

- 不注册工具、不联网、不写文件；
- 段落文本每次模型步都会重新求值，所以改开关后**下一条回复**就生效；
- 技术内容（命令、路径、代码、报错）在提示里被要求保持精确，角色扮演不改变事实。

## 安装

```powershell
pwsh -File .\install.ps1
```

然后完整退出 DSH 再打开一次。发行包根目录的 `install.ps1` 会一并安装。

## 开关

`cordis.patch.yml` 里的条目：

```yaml
- insert:
    - id: sandrone-persona
      name: dsh-plugin-sandrone-persona
      config:
        enabled: true
        language: zh        # zh（默认）| en
        # persona: |       # 可选：完全替换内置人格文本
        #   ...
```

临时关掉可以把 `enabled` 改成 `false`，或给条目加 `disabled: true`。

运行中也可以直接切换：

```text
GET http://127.0.0.1:<GUI端口>/sandrone-persona/status    # 读取状态
GET http://127.0.0.1:<GUI端口>/sandrone-persona/toggle    # 切换开/关
```

## 注意

- 段落是全局的，会同时作用于子代理 / 工作流；这是 DSH `systemPrompt` 的现有行为，没有「只作用于主代理」的开关。
- 人格文本会进入每次请求的系统提示，请保持简短。
- 中途切换会改写系统消息并让前缀缓存从改动处失效；这是可接受的，但不是零成本。
- 非官方同人道具，与 HoYoverse / COGNOSPHERE、DeepSeek 无隶属或背书关系。

代码 MIT，见仓库根目录 [LICENSE](../LICENSE)。
