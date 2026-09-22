---
name: fusion-validate
description: 复核其他专项提交的候选问题，检查成立条件、反例、影响和根因去重；此专项结束后任务继续覆盖剩余检查面。
---

**候选验证与反证**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：候选结论与引用证据；成立条件及最小验证目标。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 把候选重述为主体、输入、缺失控制与实际结果；声明不清楚时先定位缺失事实。
2. 检查上游控制、现实前提、范围归属及业务预期；选择一个能推翻结论的对照并记录结果。
3. 根据真实证据给出validated、false_positive或仍为candidate及blocker；原有accepted_risk保持独立业务含义。
4. 按根因和资产/路径去重，保留所有影响位置；验证一个候选失败只结束该候选，不停止整个任务。
5. 当前主会话顺序复核，记录review_mode=sequential_same_agent，不标成独立代理验证。

**把反例说具体。** 每个候选交代触发事实、适用前提、成立结果和替代解释。一次现场失败只否定该条件下的主张，不能否定整类方法；统一页面、自有对象、无效身份、错误包装和不稳定差异要各自判断。检查完成、确认漏洞及采样覆盖含义不同，见 [验证与覆盖判定](../../references/field-methods.md#validate)。

执行路由：`code.inspect`、`http.history`、`http.request`、`evidence.persist`。已有本地工具直接 start/run；需要 MCP 且工具选择不明确时，按 [执行路由规则](../../references/execution-router.md) 只查当前能力。能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`findings.json`、`refutation-records.json`、`unresolved-validation.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：每个候选有结论或最小缺失事实，确认项有可复核执行/代码证据。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S07 [trailofbits/skills · plugins/fp-check/skills/fp-check/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/fp-check/skills/fp-check/SKILL.md)
- S23 [elementalsouls/Claude-BugHunter · skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)
- S10 [cloudflare/security-audit-skill · skills/security-audit/VALIDATION-AND-REPORTING.md](https://github.com/cloudflare/security-audit-skill/blob/HEAD/skills/security-audit/VALIDATION-AND-REPORTING.md)

方法改编参考 Trail of Bits skills（CC-BY-SA-4.0），并融合MIT来源的流程；本专项相关方法文本按CC-BY-SA-4.0保留归属，来源见sources.lock.json。
