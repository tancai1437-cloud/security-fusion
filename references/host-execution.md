# DSH 调用参数与执行约定

仅在参数不明确、工具返回错误或宿主接入调试时读取；route 已提供的方法不重复读取。

## 从方法走到调用

**宿主有 `fusion` 时，先 `route`，紧接 `execute`。** route 从当前宿主可见工具中匹配能力，返回当前专项的同源方法、实际工具 schema 和 route_id；不要重读整套目录。工具有多个候选时只选适合当前问题的一项。首次可在 route 一并提供目标与范围：

```text
fusion(action="route", request={
  "mission":"src", "objective":"用户要回答的问题", "scope":"用户约定范围和限制", "target":"规范目标",
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

目标操作及 shell/MCP 继续走 execute，省略不变的 objective/scope/target；可同时传 `review:{attempt:上一回执的attempt_id,summary:实际结论,verdict:"done"}`。本案或 Skill 内的绝对文件路径可直接 read/grep；目录遍历、其他目标材料仍需按实际用途路由。route_id 绑定方法与工具，换专项或工具先 route；每次传本次 arguments、purpose、work，不能无意沿用上次测试条件。证据、参数、调用 ID 与路由来源自动落盘，模型不补写原始回执。失败先看返回原因，不能判 done。当前专项的 guidance 已返回时不重读文件。

capability 使用当前专项列出的 ID；联网查资料、保存报告等通用取证操作用 `evidence.persist`，不要臆造 web.search 等能力。单独复核旧回执可只传 `execute(request={review:{attempt,summary,verdict}})`，不必再读文件或重复目标调用；finish 返回未决 ID 时按该 ID 处理。

**保存报告和阶段文件用单层参数**：`fusion(action="save",file_path="REPORT.md",content="实际正文")`。content 是顶层普通字符串。程序在一次调用内准备本案 writer 路由、实际写入并核对字节；不再让模型重新拼写权限参数。完整目标检查仍先取得方法，再 execute。

## 严格归属与灵活调度

目标/身份、会话归属、证据版本、实际回执和完成条件保持严格；专项、等效工具、只读材料整理允许切换。route 优先在已暴露工具中选择，参考同目标最近五分钟的实际执行结果、目标绑定、宿主配置和上下文连续性。HTTP 拒绝响应不是工具故障。候选仍可能尚未验证；路由本身不做探测，也不自动重试写操作。明确指定的等效工具可以覆盖默认选择，未知能力匹配需 tool_reason。

安装器默认 requireMission=true，首次声明任务类型后不能静默改为另一个类型。URL 仅规范化等价表示，保留非根路径、查询和片段差异，不扩大目标范围。

宿主可选配置 `toolPriority: {"能力 ID":["实际工具名", ...]}` 表达偏好；`capabilityTools` 继续映射实际能力。没有这些扩展时仍使用宿主已有工具和原来的名称匹配路径。

执行路由可在清单中声明 `http_methods`；当前 web.crawl 只接受结构化参数中明确的 GET/HEAD/OPTIONS，POST 等操作转 api/web/business 的 http.request 并复用已有工具。此校验不解析任意 shell/浏览器脚本，也不证明 GET 是无副作用或验证方法正确；它只纠正可明确识别的采集路由误用。

压缩摘要中的 E-ID 若缩短，可用至少 8 位十六进制的前缀读取：仅在本案唯一匹配时解析并返回完整 ID，仍验证文件哈希；重名或未知时用 query --kind artifacts 查本案索引，不猜磁盘路径。

报告中的 CALL-ID 也可用本案唯一且至少 8 位十六进制的前缀；finish 对照真实回执解析为完整 ID，歧义或虚构引用仍拒绝。review、assessment 等执行状态操作仍使用实际完整 ID。

MCP 可选返回 `artifacts:[{"path":"实际绝对文件路径","sha256":"64位哈希"}]`。只有宿主显式声明 `toolArtifactRoots:{"实际工具名":"该工具的专属目录"}` 才导入；每次最多四个、每个不超过 8 MiB，检查真实路径与哈希后复制到本案。未提供该协议的 MCP 照常调用，不强制改造第三方服务。不同会话/目标使用不同工件目录。

原始回执与导入文件都会取得 E-ID。`fusion(action="artifact",artifact_id="E-…",query="literal text")` 在本案完整工件内搜索，只返回少量片段；用返回的 offset 继续。搜索是字面量、ASCII 大小写不敏感，不把所有正文塞进上下文。也可直接读取回执中本案的文件路径。

阶段性 `finish(status="partial")` 可以保留未复核观察，返回 unresolved 计数，账本不会被改成 done；真正 submitted 仍要求未决检查清零、交付和验收成立。运行中且没有完整回执的调用仍不能冒充已记录结果。

用户要求暂停或实际受阻：`checkpoint` 的 request 填 summary 与下一未完成动作 next；交付时 `finish` 填 report、summary、最后的 review，以及 assessment:[{criterion,attempts:[实际 CALL-ID],summary:证据如何回答该条件}]；未解决条件保留缺口，partial 明确部分交付。新任务只分析或用户转去无关工作用 suspend(reason)；本案证据分析、整理和报告继续用 artifact/save/finish，suspend 不解除本案资源的调用约束。压缩后先按 next_action 处理未决调用，再读 results 复用前置结论，结合 acceptance 的缺口、continuation/checkpoint 推进。guidance 标 method_deferred 时按 source 读取当前方法，不能把省略当成已执行。宿主限制绕过并有限纠正过早结束；语义复核仍由当前 Agent 做。


阶段结论/转向/阻塞可用 [节点复盘](node-review.md)，保存当前问题与下一试验。组件维护者查看 [分类组合](composition.md)；普通任务不遍历组件表。
