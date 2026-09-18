# 环境初始化、补齐与能力索引

此流程由加载 security-fusion 的当前 Agent 执行。用户安装/初始化本 Skill 或开始实际任务即进入流程；不能在输出待办、安装教程或未连接配置后结束。只处理目标运行机器，不在协助发布 Skill 的开发机安装安全软件。保留主路由 → 专项 → 执行三层结构。

## 触发与完成条件

- 普通 `skills@1.7.0 add` 复制/链接 Skill 文件，没有本包可用的通用 post-install 执行钩子。因此安装后首次加载 Skill 自动初始化；若用户让 Agent 执行安装，安装完成立即加载本节继续初始化。单独在终端运行安装命令不会启动一个模型替用户安装全部外部软件。
- 用户只说“初始化环境”时，先盘点全部 8 个 MCP 提供者和宿主能力，再根据现有连接接入、验收。没有给出任务时，默认完成宿主文件能力、JS 浏览器观察和 HexStrike 服务清单能力；其余专项登记为待按需启用。用户明确要求全量补齐时，对全部适用提供者循环执行，并报告真实阻塞。
- 实际任务按当前专项/检查所需能力补齐，不默认启用全部替代品。已有可用 Ghidra 不必再装 IDA；已有可用 JS Reverse 不必再装 jshook。
- 当前所需能力全部 ready，或每项有明确外部阻塞/不适用原因，才交付环境结果。已安装、已配置、能列工具、真实调用成功是不同状态。

## 私有目录与首次盘点

选定安装包实际路径 FUSION_ROOT；环境目录 ENV_ROOT 放在 Skill 之外，例如 Linux 的 `~/.local/share/security-fusion/environments/<machine>/<agent>`。HOST_INSTANCE 使用实际宿主进程/实例标识；无法取得时用当前会话唯一 ID，新会话重新验收，不能写死为 default。环境索引不含目标完成状态或跨案件身份，案件仍走独立 workspace/session/case 绑定。

```bash
python3 "$FUSION_ROOT/scripts/fusion_bootstrap.py" scan --root "$ENV_ROOT" --agent dsh
python3 "$FUSION_ROOT/scripts/fusion_bootstrap.py" plan --root "$ENV_ROOT" --agent dsh --instance "$HOST_INSTANCE" --capability browser.observe
```

scan 仅检查 PATH 和少量明确目录，输出检测到/未检测到的命令与入口候选，不执行发现的程序。对于非标准路径，加 --search-root；Agent 再用本机包管理器查询、当前 Agent 配置和用户指定路径补充发现。不要把“PATH 未找到”当作“系统没有”。不搜索密钥、不遍历整个磁盘，不合并其他 Agent 的配置。容器/远程服务的工具在实际执行端查询，不能从 Kali 的 PATH 推断。

当前 Agent 实际暴露的工具优先：先验证已有工具，即使不知道其安装路径也不重复安装。MCP 连接存在时登记该连接；不需要外部 MCP 的本地文件能力登记 native。仅用 `recipe --provider <id>` 读取当前需要的安装/验收方法，[提供者清单](../manifests/environment-providers.json)覆盖所有路由提供者。

## 自动执行补齐循环

对 plan 返回的 providers_to_reconcile 逐一执行，当前主会话负责到底：

1. **复用**：查当前宿主 MCP 工具、配置和明确的已有安装目录。调用现有只读/本地样例能力，确定软件版本、入口、后台、插件、实际执行机器及缺失项。
2. **补缺**：读取该提供者上游安装说明，选择兼容的具体发布版本/提交；用宿主命令工具完成下载、独立环境安装和缺失运行依赖补齐。优先用户目录、专用 venv/npm prefix，不升级用户无关环境。Kali 系统包先查询实际仓库是否提供，使用已有权限安装；需要交互密码、账号、许可证或付费时只阻塞该项。不要因此暂停整个初始化。
3. **落盘**：在 ENV_ROOT/setup/<provider>/ 保存版本/提交、来源、执行命令（密钥用环境变量）、退出码、安装输出、软件/插件位置和恢复方式。失败读取日志诊断，修正后续跑；不能对未知结果无限重试，也不能把失败命令写成成功。使用环境变量传凭据，不把值写进索引、配置模板或日志。
4. **接入**：登记实际连接，生成当前宿主格式，然后由 Agent 将这些条目合并到自己正在使用的配置。先备份原文件及 SHA256；保留模型、权限、其他 MCP、已有同名连接和用户改动。同名配置已经可用则复用，不再加一个重复连接。
5. **验收**：通过当前 Agent 实际调用需要路由的工具，使用环境目录里的小型本地样例/回环测试服务，或当前任务已有授权的上下文。检查预期输出、后台所需命令与插件实际可用；仅 tools/list、健康接口或退出码 0 不代替业务能力测试。元工具先发现/加载，再调用真正需要的工具。
6. **索引**：保存真实工具 schema、原始结果及语义验收记录，执行 verify。再次 plan；剩余缺项继续补齐或验证适用替代项。不要要求用户手写配置或逐个决定已有清单中的常规实现。

需要重启当前宿主且没有可用热重载方式时，保存配置、进度和精确重启命令，状态留为 registered_not_verified；让用户执行这一项必要重启。恢复后自动从未验收步骤继续，不能自称“已接通”。

## 连接登记和宿主配置

连接输入为 JSON，仅描述当前提供者。示例（路径须替换为实际检测结果）：

```json
{
  "transport": "stdio",
  "command": "/absolute/path/to/node",
  "args": ["/absolute/path/to/installed/server.js"],
  "cwd": "/absolute/path/to/provider",
  "watch_files": ["/absolute/path/to/current-agent-config"]
}
```

command 必须存在，args 不经过 shell、不展开 ~/$HOME。登记解释器、入口、实际宿主配置、版本锁文件与相关底层命令作为 watch_files，变化会使验收失效。原生工具用 `{"transport":"native"}`，也可 watch_files 绑定当前宿主配置。已由宿主管理但不暴露命令/URL 的连接，先从该宿主实际配置获取；无法获取就明确记录限制，不编造路径。

stdio 可用 `env_refs: {"API_KEY":"SERVICE_API_KEY"}`；HTTP 可用 `header_refs: {"Authorization":"SERVICE_AUTH_HEADER"}`，值仅是环境变量名。streamable-http 使用真实 url，不接受含凭据/查询串的 URL。Burp 的旧 SSE 通过其官方 stdio proxy 转接，不能伪装成 streamable-http。

```bash
python3 "$FUSION_ROOT/scripts/fusion_bootstrap.py" register --root "$ENV_ROOT" --agent dsh --provider js-reverse --input connection.json
python3 "$FUSION_ROOT/scripts/fusion_bootstrap.py" configure --root "$ENV_ROOT" --agent dsh --provider js-reverse
```

configure 只写自己的 managed 文件、保留上一个版本，检测到人为修改时拒绝覆盖；**生成文件还不代表宿主已经加载**。Agent 接着完成当前宿主配置合并和热重载/重启：

| 宿主 | 接入方式 |
|---|---|
| DSH | managed/dsh-mcp.cordis.yml 是官方 Cordis insert patch。把条目合并到当前 profile 的 cordis.patch.yml，或在既有启动命令加 --patch；当前 MCP 客户端支持 stdio/streamable-http。保留用户已有 patch。 |
| OpenCode | managed/opencode-mcp.json 中的 mcp 字段合并到当前实际配置；保留现有 JSONC 注释与其他设置。 |
| Pi | 先检查是否已有可用 MCP adapter；确实缺失才安装 pi-mcp-adapter。managed/pi-mcp.json 的 mcpServers 条目合并到当前项目 .mcp.json 或已选全局配置；带凭据的服务使用当前 adapter 文档中的认证机制，不猜测变量插值。 |

生成器不决定宿主配置位置，不跨客户端自动导入。更新实际配置后重新 register（watch_files 已变），使用返回的新 connection_sha256 做验收。

## 实际验收与索引

下面是验收收据的**结构示例，不是已经执行的结果**。tools 必须来自当前宿主真实暴露的 schema；checks 每项对应一次已经成功的实际工具调用，result_file 在 ENV_ROOT 内，含原始 MCP CallToolResult。原生工具保留原输出并包装为 content，不能自己编写成功结果。fixture_ref 指向所用样例/已授权上下文，validation 描述检查了哪些实际输出。observed_at 为实际观察的 Unix 时间。

```json
{
  "instance": "actual-host-instance",
  "observed_at": 0,
  "connection_sha256": "digest-returned-by-register",
  "tools": [
    {"name":"mcp__js-reverse__navigate_page","inputSchema":{"type":"object"}}
  ],
  "checks": [
    {
      "capability":"browser.observe",
      "tool":"mcp__js-reverse__navigate_page",
      "result_file":"/absolute/environment/probes/navigation.json",
      "outcome":"pass",
      "scope":"local_fixture",
      "fixture_ref":"local-browser-fixture",
      "validation":"实际导航到本地测试页，页面 URL 与测试标记均符合预期"
    }
  ]
}
```

宿主文件工具名不同于能力别名时，tools 条目增加 native_alias（read_file/search_files/write_file/hash_file），同时保留真实 name。一个实际调用确实覆盖多个能力时可复用结果文件，无须为了索引重复执行。只验证真实所需的路由工具；未测过的其他工具保持不可用。

```bash
python3 "$FUSION_ROOT/scripts/fusion_bootstrap.py" verify --root "$ENV_ROOT" --agent dsh --instance "$HOST_INSTANCE" --provider js-reverse --input receipt.json
python3 "$FUSION_ROOT/scripts/fusion.py" catalog --capability browser.observe --environment "$ENV_ROOT" --agent dsh --instance "$HOST_INSTANCE"
```

verify 校验当前连接摘要、宿主实例、300 秒内的真实观察、所选路由匹配、实际结果 envelope、错误标志和证据哈希，默认验收有效期 1 小时，最大 24 小时。结果的业务含义仍由执行 Agent 检查；收据是可信调用方协议，不是独立审计器或身份认证。安装存在、schema 存在、健康检查通过均不能产生未调用工具的 ready 绑定。

索引按「机器 + Agent + 宿主实例 + 提供者 + 能力 + 实际工具 + 连接/文件版本」约束。环境与目标案件分开：ready 表示在记录的验收上下文中可调用，不继承任何其他目标的授权、登录态、数据库或完成状态。新任务仍按 [隔离协议](scoped-memory.md) 登记实际上下文。

## 失效、续跑与回退

- 每次只查当前能力，不将完整安装日志、全部工具 schema 填入模型上下文。默认命令响应不超过 6,000 字符，明细保留在文件。
- 新宿主实例、TTL 过期、入口/配置文件变化、路由定义变化、结果文件丢失/改写都会使绑定失效；重新验收需要的能力，不重复安装已存在的软件。
- 实际调用失败立即执行 `invalidate --provider <id> --reason <实际原因>`；这也支持尚未安装的提供者。按日志修复，再验收，不能靠修改状态绕过。
- 失败/阻塞只影响相关能力。缺 IDA 许可证可验证 Ghidra；缺浏览器显示环境不阻塞已有命令行工具。
- 回退前比较当前宿主配置与本次写入后的哈希，一致才恢复备份；已有其他修改就只撤回本次条目。仅清理本次创建且路径核对过的专用目录，不卸载原有软件。managed/backups 用于本包生成文件的恢复，宿主主配置备份由执行 Agent 在合并前另存。

来源：[固定安装器实现](https://github.com/vercel-labs/skills/blob/v1.7.0/src/installer.ts)、[DSH MCP](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md)、[DSH patch](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/mcp-memory.md)、[OpenCode MCP](https://opencode.ai/docs/mcp-servers/)、[Pi adapter](https://github.com/nicobailon/pi-mcp-adapter)。各安全提供者安装细节以清单链接的当前官方文档为准。
