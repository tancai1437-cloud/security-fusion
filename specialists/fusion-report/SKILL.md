---
name: fusion-report
description: 根据案件的实际检查、证据和验证结论生成摘要、报告、覆盖及续跑记录；适用于完整、部分或零发现任务的交付。
---

**覆盖、报告与经验**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：计划版本、检查项与状态；证据索引、确认和未确认结论。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先运行 fusion.py report 导出账本覆盖、证据索引与 delivery.json，按真实证据补齐缺失专项产物，再生成技术报告。ledger_status=completed 仅限已登记检查，status=review_required 也只表示等待内容复核；须另核对完整适用面、对照是否充分以及宿主动作是否漏记，不在写报告时补造影响。
2. 核对引用、文件存在和hash，注明实际使用的Skill/MCP与工具失败；缺失必要证据的项不能通过确认校验。
3. 按固定计划版本报告完成、受阻、未执行和不适用项。零确认发现仍交付真实覆盖和局限。
4. 输出恢复位置、下一项与依赖；经验写入脱敏候选区，去重和回归后才晋级正式规则。

阶段结束时按 [隔离与经验协议](../../references/scoped-memory.md) 将值得复用的方法保存为 memory-add 候选，引用已经完成且有证据的来源笔记，保留适用条件和失败反例。核对来源、脱敏及实际验证后才 memory-review accept，默认 project 范围；general 只放可跨项目的方法。原始报告不进入共享索引，不自动改写 SKILL.md。

**经验保留增量。** 沉淀前核对能否跨同类目标使用、相比已有方法新增什么、是否有已复核来源及反例；没有新增条件的重复成功留在案件。阴性、误判识别和中低风险方法也可有价值。已有同类只形成必要修订，按 supersedes 和审核机制保留历史。详细准则见 [经验筛选](../../references/field-methods.md#learning)。报告保留原始证据引用，正文使用脱敏值，不复制完整凭据或会话值。

执行路由：`report.compose`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`report/summary.md`、`report/report.md`、`report/coverage.md`、`report/findings.json`、`resume.md`、`learning/candidates.md`。这些交付产物位于当前案件根目录对应路径；运行程序生成的 report/ledger.md、report/coverage.json 是技术报告的输入，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：报告与原始记录一致，所有未完成项可解释，业务负责人可直接验收。

宿主有 fusion 时继续 execute，以 review 提交上一回执的实际结论；阶段暂停用 checkpoint，交付用 finish。没有宿主组件才用 [advance](../../references/observation-routing.md#简化入口advance)。保存阴性、反证和阻塞；只在阶段结束整理产物，不等用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S10 [cloudflare/security-audit-skill · skills/security-audit/VALIDATION-AND-REPORTING.md](https://github.com/cloudflare/security-audit-skill/blob/HEAD/skills/security-audit/VALIDATION-AND-REPORTING.md)
- S01 [GreyDGL/PentestGPT · pentestgpt_agent/README.md](https://github.com/GreyDGL/PentestGPT/blob/HEAD/pentestgpt_agent/README.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
