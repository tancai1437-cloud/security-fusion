---
name: fusion-validate
description: 复核其他专项提交的候选问题，检查成立条件、反例、影响和根因去重；此专项结束后任务继续覆盖剩余检查面。
---

**候选验证与反证**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：候选结论与引用证据；成立条件及最小验证目标。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 把候选重述为主体、输入、缺失控制与实际结果；声明不清楚时先定位缺失事实。
2. 检查上游控制、现实前提、范围归属及业务预期；选择一个能推翻结论的对照并记录结果。
3. 根据真实证据给出validated、false_positive或仍为candidate及blocker；原有accepted_risk保持独立业务含义。
4. 按根因和资产/路径去重，保留所有影响位置；验证一个候选失败只结束该候选，不停止整个任务。
5. 当前主会话顺序复核，记录review_mode=sequential_same_agent，不标成独立代理验证。

**把反例说具体。** 每个候选交代触发事实、适用前提、成立结果和替代解释。一次现场失败只否定该条件下的主张，不能否定整类方法；统一页面、自有对象、无效身份、错误包装和不稳定差异要各自判断。检查完成、确认漏洞及采样覆盖含义不同，见 [验证与覆盖判定](../../references/field-methods.md#validate)。

执行路由：`code.inspect`、`http.history`、`http.request`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`findings.json`、`refutation-records.json`、`unresolved-validation.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：每个候选有结论或最小缺失事实，确认项有可复核执行/代码证据。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S07 [trailofbits/skills · plugins/fp-check/skills/fp-check/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/fp-check/skills/fp-check/SKILL.md)
- S23 [elementalsouls/Claude-BugHunter · skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)
- S10 [cloudflare/security-audit-skill · skills/security-audit/VALIDATION-AND-REPORTING.md](https://github.com/cloudflare/security-audit-skill/blob/HEAD/skills/security-audit/VALIDATION-AND-REPORTING.md)

方法改编参考 Trail of Bits skills（CC-BY-SA-4.0），并融合MIT来源的流程；本专项相关方法文本按CC-BY-SA-4.0保留归属，来源见sources.lock.json。
