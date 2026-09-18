---
name: security-fusion
description: 编排获准的渗透、SRC、逆向、源码审计、红队路径和AI应用评估任务，自动路由专项Skill与执行工具/MCP，持续保存证据并交付报告与续跑记录。
---

**三层入口：主路由 → 专项 Skill 路由 → 执行路由。**

当用户请求完整任务时由本入口持有主控；明确的单点任务可直接加载对应专项。仅方案、解释、调研不进入目标执行。当前主会话完成编排与调用，不创建子代理。

1. 从用户请求和已有材料确定目标、有效范围、交付要求及材料类型。复用本次已提供的授权，不重复索取。
2. 读取 [主路由](references/main-router.md) 与 [任务模板](manifests/missions.json)，选择任务类型并确定唯一案件目录。
3. 根据真实事实和前提从 [专项登记](manifests/specialists.json) 生成工作项，分别记录适用、受阻、未执行和完成条件。
4. 选择当前可执行项，只加载它的 SKILL.md。专项沿用本任务上下文，不重新解释整项任务。
5. 专项提出所需能力后，按 [执行路由](references/execution-router.md) 和 [MCP匹配表](manifests/execution-routes.json) 选择实际工具、准备参数、执行并获取完整结果。
6. 按 [证据契约](references/evidence-contract.md) 保存动作、结果、产物与结论。新事实可能增加后续检查项；保留变更理由。
7. 专项完成或受阻后返回本入口，继续其他可执行项。对结果不明的外部动作先核对，避免重复执行。
8. 由 fusion-validate 复核候选；fusion-report 根据真实证据与覆盖交付摘要、报告、未完成项和续跑记录。零确认发现也应完成报告。

实施含义：此包提供可供Agent读取的融合指令、路由清单与输出契约。MCP由当前宿主提供实际调用；本包不内置MCP客户端、后台执行服务或自动安装器。

来源与取舍见 [融合决策](references/upstream-decisions.md)，具体文件指纹见 [来源锁定](sources.lock.json)。
