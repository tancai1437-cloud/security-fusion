# DSH 宿主恢复与原生工具

Skill 提供方法，`AGENTS.md` 可提供发现入口。两者都不能代替宿主恢复机制。本适配器针对 DSH 0.1.2-rc.1：通过原生 `fusion` 工具运行既有 CLI，宿主自动提供案件和会话参数；使用 `agent/pre-step` 在首次激活、新轮次以及恢复消息被压缩移除后，从磁盘重新获取状态。

## 接入方式

普通 `skills add` 只安装文件。本适配器是可选的 DSH profile 插件，须在目标机接入；不会因为 Skill 安装成功而自动生效，也不修改 DSH 系统提示词。

1. 把 [dsh.mjs](../adapters/dsh.mjs) 与 [dsh-runtime.mjs](../adapters/dsh-runtime.mjs) 复制到所用 DSH profile 目录，两者放在一起。插件依赖 DSH 已提供的包，不另外安装 npm 依赖。
2. 在该 profile 的 `cordis.patch.yml` 数组中追加以下一项。替换为目标机实际绝对路径，保留既有配置：

```yaml
- insert:
    - id: security-fusion-host
      name: ./dsh.mjs
      config:
        skillRoot: /home/kali/.agents/skills/security-fusion
        stateDir: /home/kali/security-fusion-private/host
        python: python3
```

3. 重启此 profile，在新会话中加载 `security-fusion`。实际工具列表应出现 `fusion`；首次工具返回含 `host_binding`，DSH 日志中应出现 `security-fusion-state` 来源的消息。缺任何一项都不能宣称宿主接入完成。

`stateDir` 保存在技能目录外，不提交到 GitHub。Windows 的 python 可以设为 `python` 或解释器绝对路径。旧 DSH 版本、Pi 和 OpenCode 尚未验证此插件 API，仍使用原 CLI；不可直接复制 DSH patch 宣称兼容。

## 执行与恢复

已有 `task.json` 时：

```json
{"action":"start","args":["--input","task.json","--execute-local"]}
```

`args` 是 `fusion.py` 子命令参数数组，不带脚本路径和 `--workspace/--case/--session`。`input_json` 可省去临时配置文件：start/plan/route 使用完整输入；advance 使用方法特定 inputs；mcp-run 使用真实工具参数。其余命令沿用 [运行协议](runtime.md)。

一次 DSH 会话自动绑定一个独立案件，键来自宿主真实 session ID。同一项目两个会话不共享“最近案件”。不同目标使用不同会话；旧 CLI 案件继续走原显式绑定协议，本适配器不自动接管。相同 session ID 更换 cwd 会拒绝恢复。

连续执行时沿工具回执推进。宿主只在恢复信息缺席、新轮次或工具故障状态改变时追加恢复包，不每步重复注入全包；原始结果仍保存在案件中，模型只得到最多 1,600 字符的 stdout 预览。未决调用优先恢复，已完成检查不会因恢复而自动重发。工具故障只保留错误摘要，修复并实际调用成功后清除。

## 能保证和不能保证的边界

- 宿主负责恢复触发、参数绑定、CLI 实际执行和已有证据落盘，不依赖模型从摘要猜案件路径。
- 检查含义、方法选择、范围变化与最终结论仍需模型判断。工具返回成功不等于评估完成。
- 原生搜索、浏览器或 MCP 仍由原宿主工具执行。此插件不修复网页工具的依赖，也不把搜索列表当成已验证正文。
- 插件不拦截任意 Bash/PowerShell 命令，不是隔离沙箱，不能保证模型绝不会绕过 Skill。需要根据实际宿主调用记录验收；不得将“恢复消息已注入”写成“全部方法已遵循”。

`AGENTS.md` 保持简短入口即可，例如：安全执行任务加载 security-fusion；有 fusion 工具时使用其自动绑定；继续旧案先恢复状态；以工具回执与证据交付。不要把整套 Skill 再复制一份进 AGENTS.md。

真实模型、两次压缩及已知失败见 [联调记录](agent-integration-2026-09-25.md)。回退时移除 profile 中 `security-fusion-host` 的插入项并重启；保留 stateDir 中的案件与原始证据，原 CLI 仍可显式绑定读取。
