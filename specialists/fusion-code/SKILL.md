---
name: fusion-code
description: 对提供的源码建立调用上下文，审查安全控制与跨函数假设，并对已确定根因寻找变体；不以模式命中直接确认漏洞。
---

**源码审计与变体**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：源码版本与范围；入口、依赖或候选问题。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先建立入口、信任边界、敏感操作与跨函数依赖摘要，再开始给出漏洞判断。
2. 对关键路径记录调用方保证、当前函数假设、被调用函数实际行为及未解决问题；沿调用链验证控制条件。
3. 存在候选根因后，先找到确定实例，再逐步放宽检索，按相同控制缺失和适用条件验证变体。
4. 保持问题覆盖与上下文文件关联；外观相似的代码不直接合并为同一漏洞。
5. 将已存在的Semgrep/CodeQL等结果作为线索，通过本专项回到当前源码证据；本包不假装新增了对应MCP。

执行路由：`code.inspect`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 执行 fusion.py catalog --capability <id> 按需选择工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

输出：`code-context.md`、`trace-records.json`、`variant-candidates.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：关键假设和调用链可引用，候选/变体均附确认或否定依据。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S21 [trailofbits/skills · plugins/audit-context-building/skills/audit-context-building/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/audit-context-building/skills/audit-context-building/SKILL.md)
- S08 [trailofbits/skills · plugins/variant-analysis/skills/variant-analysis/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/variant-analysis/skills/variant-analysis/SKILL.md)
- S07 [trailofbits/skills · plugins/fp-check/skills/fp-check/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/fp-check/skills/fp-check/SKILL.md)

方法改编参考 Trail of Bits skills（CC-BY-SA-4.0）；来源与文件指纹见sources.lock.json。本专项的相关方法文本按CC-BY-SA-4.0保留归属。
