---
name: security-fusion
description: 对获准目标执行渗透、SRC、逆向、源码审计或 AI 安全评估；根据页面、接口、身份与样本证据选择专项方法，调用 MCP 或本地工具，保存结果并继续未完成检查。
---

主路由 → 当前专项的方法 → 实际工具，由当前会话执行，不创建子代理。分析、比较或方案请求只分析资料；有明确执行任务时，先取得一份能回答问题的目标证据。

## 选择一个当前专项

| 当前任务或已有材料 | 立即进入 | 起手证据 |
|---|---|---|
| 渗透 / SRC 新目标，已有 URL | [recon](specialists/fusion-recon/SKILL.md) | 入口的实际响应、业务入口与跳转 |
| 已知 Web 输入、XFF/代理信任、上传下载或浏览器边界 | [web](specialists/fusion-web/SKILL.md) | 正常请求与对应输出 |
| API、登录/密码重置、对象 ID、角色或租户关系 | [api](specialists/fusion-api/SKILL.md) | 正常请求、身份或恢复凭证的归属 |
| 订单、额度、多阶段交易、一次性操作 | [business](specialists/fusion-business/SKILL.md) | 当前流程与服务端状态 |
| JS、签名、请求构造 | [js](specialists/fusion-js/SKILL.md) | 请求发起位置与相关源码 |
| 源码审计 | [code](specialists/fusion-code/SKILL.md) | 输入入口、调用方与控制检查 |
| APK / 移动应用；DLL、PE/ELF、.NET、崩溃日志 | [mobile](specialists/fusion-mobile/SKILL.md) / [binary](specialists/fusion-binary/SKILL.md) | 样本标识、格式与当前分析工程 |
| 云 / 容器；网络服务 / 身份基础设施 | [cloud](specialists/fusion-cloud/SKILL.md) / [infra](specialists/fusion-infra/SKILL.md) | 指定资源的配置与实际状态 |
| AI 应用 / Agent 边界 | [ai](specialists/fusion-ai/SKILL.md) | 输入、检索、工具参数与实际结果 |

明确问题直接进入对应专项；不为单点任务遍历主目录。完整任务类型或红队约定路径不明确时才读 [主路由](references/main-router.md)。只载当前专项，返回的 guidance 已含同源方法时不重复读文件。

## 从方法走到调用

**宿主有 `fusion` 时，直接用 `execute` 调当前真实工具。** 不先写 task.json、清点全部 MCP、查 CLI 帮助或初始化账本。读过当前专项就发第一项有用调用：

```text
fusion(action="execute", request={
  "objective":"用户要回答的问题", "scope":"用户约定范围和限制", "target":"规范目标",
  "skill":"当前专项 ID", "capability":"该专项对应的能力 ID",
  "purpose":"这一步要取得什么证据", "tool":"当前宿主的实际工具名", "arguments":{实际参数},
  "deliverables":["用户要求的交付文件"]
})
```

后续 shell、搜索、MCP、读写文件都继续走 execute，省略不变的 objective/scope/target；可同时传 `review:{attempt:上一回执的attempt_id,summary:实际结论,verdict:"done"}`。证据、参数、调用 ID 自动绑定落盘，模型不补写原始回执。失败先看返回原因，不能判 done。当前专项的 guidance 已返回时不重读文件。每次调用都要推进具体问题，不能用大量“准备”替代执行。

capability 使用当前专项列出的 ID；联网查资料、保存报告等通用取证操作用 `evidence.persist`，不要臆造 web.search 等能力。单独复核旧回执可只传 `execute(request={review:{attempt,summary,verdict}})`，不必再读文件或重复目标调用；finish 返回未决 ID 时按该 ID 处理。

用户要求暂停或实际受阻：`checkpoint` 的 request 填 summary 与下一未完成动作 next；交付时 `finish` 填 report 文件、summary 和最后的 review，程序核对账本和文件；仅分析或用户切换任务用 `suspend(reason)`，不把暂停标成完成。压缩后 `resume`，沿 checkpoint/current/guidance 继续；不要重复基线。宿主会阻止裸工具绕过并在未交付就结束时有限纠正。文件存在不代表结论正确，仍要做任务对应的实测对照。

**没有 `fusion` 工具才使用以下 CLI 流程。** 普通安装只复制 Skill；DSH 初次接入/升级宿主组件见 [宿主适配](references/host-adapter.md)。纯文本 Skill 没有拦截能力，不能声称已经启用执行约束。

1. **新任务**读 [快速执行](references/first-action.md)。HTTP 入口或本地二进制用 `start --execute-local` 合并建案、会话绑定和第一次读取；已有材料直接登记对应检查。Agent 维护案件与参数，用户不用逐步填表。
2. **选工具**：现成本地命令走 `run`；已建立显式目标 stdio 配置的 MCP 走 [mcp-run](references/mcp-execution.md)，程序完成连接、实际工具查询、调用及证据落盘。依赖当前浏览器/工程的 MCP 用宿主已连接工具，按 [执行路由](references/execution-router.md) 核对上下文。只查当前能力，缺项才 [补齐环境](references/environment-bootstrap.md)。
3. **读结果并推进**：取得输出后先判断实际响应；用 [advance](references/observation-routing.md#简化入口advance) 一次提交上一项复核结论与新事实，程序补齐来源和证据引用，返回下一具体方法。继续调用该方法所需工具。未匹配的问题按当前专项生成具体检查，不强凑标签。

每次下一步应回答一个明确问题，并给出可核对输出。连续准备却没有消除阻塞时，执行当前可用检查或转到独立可执行项。正常拒绝、登录壳、工具错误和结果未知分别处理；不能靠重复同一失败调用制造进展。缺身份只阻塞依赖身份的检查。

## 保留结果与恢复

运行命令显式携带 `--workspace / --session / --case`。同项目不同目标分案；压缩或重启后 `resume`，先处理未决调用与待复核证据；换会话按 [隔离协议](references/scoped-memory.md) 交接。`reuse` 不重发，`hold` 先核对。成功返回不等于检查完成，复核由当前 Agent 根据证据判断。

原始输出自动保存，阶段结束再整理专项产物，经 [validate](specialists/fusion-validate/SKILL.md) 核对并由 [report](specialists/fusion-report/SKILL.md) 交付已测、未测、受阻与依据。账本完成不代表整个评估完成。经验按需检索，阶段结束再审核沉淀；恢复默认最多 6,000 字符。详细命令按需查 [运行协议](references/runtime.md)。

Python >= 3.9，辅助程序只用标准库。执行约束需已验证的宿主组件；原生 MCP 与直接 stdio 连接的上下文不能互认。方法与许可取舍见 [融合记录](references/upstream-decisions.md)。
