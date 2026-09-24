# 一次调用并保存 MCP 证据

`mcp-run` 适用于已经安装、可用 stdio 启动，且每次调用显式携带目标的 MCP 工具。它真正运行 initialize → tools/list → tools/call；不请求模型采样、不创建子代理、不安装软件、不修改宿主 MCP 配置。

已有宿主连接的浏览器、IDA/Ghidra 工程、登录会话，或 HTTP/SSE/OAuth 服务继续使用 [原生调用协议](execution-router.md)。新 stdio 连接不能沿用“当前页面/当前工程”。不要为了用此命令给有状态工具虚构 target 字段。

## 一次配置，多次复用

Agent 从当前实际安装与工具 schema 生成私有配置，放在 Skill 目录之外；下面只是格式，名字与路径不是已接通的工具。`command` 必须是已安装服务的真实 argv，不是下载/安装命令。`bindings` 只登记已核对为显式目标语义的接口，每项能力先绑定一个合适工具。

```json
{
  "transport": "stdio",
  "context_mode": "explicit-target",
  "provider": "burp",
  "command": ["/absolute/path/to/runtime", "/absolute/path/to/installed-server"],
  "bindings": {
    "http.request": {"tool": "actual_tool_name", "target_argument": "actual_target_field"}
  }
}
```

提供者必须属于当前能力映射。配置存在只代表选择了适配方式；每次调用都从该连接的实时 tools/list 核对名称、目标字段及必填参数，然后由服务器验证完整 schema。支持分页，不根据上游候选名编造工具。第一次失败保留原因，修好前不把配置当成可用索引。

需要环境变量时使用 `env_refs: {"SERVER_ENV_NAME": "EXISTING_ENV_NAME"}`，值从当前进程环境读取。不能在配置、命令或参数文件里明文存密钥；需要认证且工具只能接受明文凭据参数时用宿主的安全凭据通道。配置可设置绝对 `cwd`，默认是配置所在目录。

## 执行当前检查

Agent 按真实 schema 写本次 `arguments.json`。配置的目标字段必须等于检查的规范 target。非匿名身份还必须配置 `identity_argument`，并传入与检查一致的身份引用；没有这种接口时沿用宿主上下文协议。其他参数也必须对应本项检查的 resource、操作、条件与 inputs，程序不独立理解任意第三方工具的业务语义或副作用。

```bash
python3 "$FUSION_ROOT/scripts/fusion.py" mcp-run \
  --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" \
  --check "$CHECK" --profile "$MCP_PROFILE" --arguments arguments.json --timeout 60
```

这一次命令完成查重、登记、连接、调用、捕获、记录。保存 `tool.json`、完整 `result.json`、stderr 和回执；输出只返回路径与短状态，不把全量工具 schema/结果塞进上下文。参数或配置变化时不能复用旧检查，须更新检查输入或方法版本。

| 返回 | 下一步 |
|---|---|
| `review` | 读取实际结果，判断完成条件，然后 review 或 advance |
| `failed` | 工具明确返回 isError；记录工具失败，不当作目标阴性 |
| `blocked` | 启动、协议协商、工具发现或必填参数失败，尚未发工具调用 |
| `unknown` | 发送后超时、断连、协议错误或未完成的任务结果，先 reconcile，不能自动重发 |
| `reuse` / `hold` | 未启动新 MCP 进程；复用已测证据或处理待复核/未决项 |

此次成功仅证明这一次连接和调用；不会伪造 DSH/Pi/OpenCode 的 ready 索引。进程停止不保证远端副作用撤销。当前客户端只处理同步 CallToolResult；异步任务结果原样保存并标记 unknown，使用该服务真实任务查询接口核对。

协议依据：[stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)、[lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)、[tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)。
