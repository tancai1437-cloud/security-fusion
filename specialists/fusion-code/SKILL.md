---
name: fusion-code
description: 对提供的源码建立调用上下文，审查安全控制与跨函数假设，并对已确定根因寻找变体；不以模式命中直接确认漏洞。
---

**源码审计与变体**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：源码版本与范围；入口、依赖或候选问题。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先建立入口、信任边界、敏感操作与跨函数依赖摘要，再开始给出漏洞判断。
2. 对关键路径记录调用方保证、当前函数假设、被调用函数实际行为及未解决问题；沿调用链验证控制条件。
3. 存在候选根因后，先找到确定实例，再逐步放宽检索，按相同控制缺失和适用条件验证变体。
4. 保持问题覆盖与上下文文件关联；外观相似的代码不直接合并为同一漏洞。
5. 将已存在的Semgrep/CodeQL等结果作为线索，通过本专项回到当前源码证据；本包不假装新增了对应MCP。

执行路由：`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`code-context.md`、`trace-records.json`、`variant-candidates.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：关键假设和调用链可引用，候选/变体均附确认或否定依据。

宿主有 fusion 时继续 execute，以 review 提交上一回执的实际结论；阶段暂停用 checkpoint，交付用 finish。没有宿主组件才用 [advance](../../references/observation-routing.md#简化入口advance)。保存阴性、反证和阻塞；只在阶段结束整理产物，不等用户逐阶段选择。

**方法来源。**

- S21 [trailofbits/skills · plugins/audit-context-building/skills/audit-context-building/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/audit-context-building/skills/audit-context-building/SKILL.md)
- S08 [trailofbits/skills · plugins/variant-analysis/skills/variant-analysis/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/variant-analysis/skills/variant-analysis/SKILL.md)
- S07 [trailofbits/skills · plugins/fp-check/skills/fp-check/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/fp-check/skills/fp-check/SKILL.md)

方法改编参考 Trail of Bits skills（CC-BY-SA-4.0）；来源与文件指纹见sources.lock.json。本专项的相关方法文本按CC-BY-SA-4.0保留归属。
