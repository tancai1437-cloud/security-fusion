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

**宿主有 `fusion` 时，先 `route`，紧接 `execute`。** route 从当前宿主可见工具中匹配能力，返回当前专项的同源方法、实际工具 schema 和 route_id；不要重读整套目录。工具有多个候选时只选适合当前问题的一项。首次可在 route 一并提供目标与范围：

```text
fusion(action="route", request={
  "objective":"用户要回答的问题", "scope":"用户约定范围和限制", "target":"规范目标",
  "skill":"当前专项 ID", "capability":"该专项对应的能力 ID",
  "purpose":"这一步要取得什么证据", "work":{"key":"stable-check","conditions":{"resource":"具体资源","control":"当前对照条件"}},
  "tool":"已知时填当前宿主的实际工具名；未知则省略", "next":"这项复核通过后的下一未完成动作",
  "criteria":[{"id":"goal-question","question":"按用户原目标，怎样才算回答了关键问题？"}],
  "deliverables":["REPORT.md"]
})
fusion(action="execute", request={"route_id":"刚返回的 ROUTE-ID", "arguments":{按返回 schema 填实际参数}})
```

route_ready **尚未调用工具**，必须紧接 execute；tool_call_id、attempt_id 和 observed 才是实测回执。未准备就直接 execute 会先返回方法，不执行目标；按返回 route_id 继续，已填字段自动恢复。同一路由重复执行不重复返回方法；专项、能力、工具/schema 或方法版本变化会重新路由。没有已知绑定的自定义工具，用 tool_reason 说明适用性和局限，回执标记为模型选择的替代工具。真实工具缺失就返回缺口，不编造名称。具体方法可传 procedure，由程序绑定对应专项和能力，不允许矛盾组合。

新任务的目标检查必须提供 work；同一问题换 shell/MCP 仍沿用 key 与 conditions，不能用工具名当检查名。条件必须包含会影响结论的输入、身份引用或样本版本；变化才另建检查。文件整理、资料搜索用 evidence.persist，按实际调用参数查重，不按父问题的 work 合并不同文件或查询。next 是可选的未完成计划，执行前即落盘。

criteria 是原任务的可验证问题，复杂任务拆成少量具体条件，单点任务可直接用目标；不要扩大用户范围。阶段观察不等于最终回答。所有交付写到宿主给出的 case_path；write/edit 和 deliverables 的相对路径按本案解析，读取项目源码仍用明确路径。shell/MCP 写文件时显式使用本案绝对路径。依赖前一步产物的执行传 depends_on:[实际 check_id]，让版本变化能被检出。

后续 shell、搜索、MCP、读写文件都继续走 execute，省略不变的 objective/scope/target；可同时传 `review:{attempt:上一回执的attempt_id,summary:实际结论,verdict:"done"}`。route_id 绑定方法与工具，换工具先 route；每次传本次 arguments、purpose、work，不能无意沿用上次测试条件。证据、参数、调用 ID 与路由来源自动落盘，模型不补写原始回执。失败先看返回原因，不能判 done。当前专项的 guidance 已返回时不重读文件。每次调用都要推进具体问题，不能用大量“准备”替代执行。

capability 使用当前专项列出的 ID；联网查资料、保存报告等通用取证操作用 `evidence.persist`，不要臆造 web.search 等能力。单独复核旧回执可只传 `execute(request={review:{attempt,summary,verdict}})`，不必再读文件或重复目标调用；finish 返回未决 ID 时按该 ID 处理。

**保存报告和阶段文件优先用单层参数**：`fusion(action="save",file_path="REPORT.md",content="实际正文")`。content 是顶层普通字符串，不把整份文件再套进 JSON 字符串 request。程序仍路由到本案真实 write 工具、捕获版本；首次若返回 route_ready，紧接 execute(route_id) 完成写入。后续相同 writer 路由直接保存，无需反复准备。

用户要求暂停或实际受阻：`checkpoint` 的 request 填 summary 与下一未完成动作 next；交付时 `finish` 填 report、summary、最后的 review，以及 assessment:[{criterion,attempts:[实际 CALL-ID],summary:证据如何回答该条件}]；未解决条件保留缺口，partial 明确部分交付。新任务只分析或用户转去无关工作用 suspend(reason)；本案证据分析、整理和报告继续用 artifact/save/finish，suspend 不解除本案资源的调用约束。压缩后先按 next_action 处理未决调用，再读 results 复用前置结论，结合 acceptance 的缺口、continuation/checkpoint 推进。guidance 标 method_deferred 时按 source 读取当前方法，不能把省略当成已执行。宿主限制绕过并有限纠正过早结束；语义复核仍由当前 Agent 做。

**没有 `fusion` 工具才使用以下 CLI 流程。** 普通安装只复制 Skill；DSH 初次接入/升级宿主组件见 [宿主适配](references/host-adapter.md)。纯文本 Skill 没有拦截能力，不能声称已经启用执行约束。

1. **新任务**读 [快速执行](references/first-action.md)。HTTP 入口或本地二进制用 `start --execute-local` 合并建案、会话绑定和第一次读取；已有材料直接登记对应检查。Agent 维护案件与参数，用户不用逐步填表。
2. **选工具**：现成本地命令走 `run`；已建立显式目标 stdio 配置的 MCP 走 [mcp-run](references/mcp-execution.md)，程序完成连接、实际工具查询、调用及证据落盘。依赖当前浏览器/工程的 MCP 用宿主已连接工具，按 [执行路由](references/execution-router.md) 核对上下文。只查当前能力，缺项才 [补齐环境](references/environment-bootstrap.md)。
3. **读结果并推进**：取得输出后先判断实际响应；用 [advance](references/observation-routing.md#简化入口advance) 一次提交上一项复核结论与新事实，程序补齐来源和证据引用，返回下一具体方法。继续调用该方法所需工具。未匹配的问题按当前专项生成具体检查，不强凑标签。

每次下一步应回答一个明确问题，并给出可核对输出。连续准备却没有消除阻塞时，执行当前可用检查或转到独立可执行项。正常拒绝、登录壳、工具错误和结果未知分别处理；不能靠重复同一失败调用制造进展。缺身份只阻塞依赖身份的检查。

## 保留结果与恢复

运行命令显式携带 `--workspace / --session / --case`。同项目不同目标分案；压缩或重启后 `resume`，先处理未决调用与待复核证据；换会话按 [隔离协议](references/scoped-memory.md) 交接。`reuse` 不重发，`hold` 先核对。成功返回不等于检查完成，复核由当前 Agent 根据证据判断。

原始输出自动保存。阶段结束按当前 guidance 的 stage_outputs 整理产物；DSH 已有目标问题、回执和完成条件时，直接生成本次范围的报告并 finish。需要核实新的漏洞候选时才进入 [validate](specialists/fusion-validate/SKILL.md)，需要完整项目级报告时才进入 [report](specialists/fusion-report/SKILL.md)；单点观察沿当前专项交付。恢复材料优先用 query --kind artifacts --check ID 找目录，再 artifact --artifact E-ID --offset 0 --length 2048 取必要片段。evidence.persist 读取技能包/本案材料成功会自动标记“材料读取完成”，不用为读规则再单独 review；它不证明目标结论。DSH 恢复自动检索本项目当前专项的已审核方法经验，不将经验变成目标事实。恢复先放结论，完整方法按预算补入；CLI 默认 6,000 字符，DSH 单份当前工作集最多 8,000 字符并替换旧恢复块。详见 [运行协议](references/runtime.md) 和 [基础能力改造](references/foundations.md)。

Python >= 3.9，辅助程序只用标准库。执行约束需已验证的宿主组件；原生 MCP 与直接 stdio 连接的上下文不能互认。方法与许可取舍见 [融合记录](references/upstream-decisions.md)。
