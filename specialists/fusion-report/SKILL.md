---
name: fusion-report
description: 根据案件的实际检查、证据和验证结论生成摘要、报告、覆盖及续跑记录；适用于完整、部分或零发现任务的交付。
---

**覆盖、报告与经验**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：计划版本、检查项与状态；证据索引、确认和未确认结论。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先运行 fusion.py report 导出账本覆盖与证据索引，再从结构化结论生成技术报告，不在写报告时改变结论或补造影响。ledger.md 的 completed 仅限已登记检查，须另核对完整任务的适用面。
2. 核对引用、文件存在和hash，注明实际使用的Skill/MCP与工具失败；缺失必要证据的项不能通过确认校验。
3. 按固定计划版本报告完成、受阻、未执行和不适用项。零确认发现仍交付真实覆盖和局限。
4. 输出恢复位置、下一项与依赖；经验写入脱敏候选区，去重和回归后才晋级正式规则。

阶段结束时按 [隔离与经验协议](../../references/scoped-memory.md) 将值得复用的方法保存为 memory-add 候选，引用已经完成且有证据的来源笔记，保留适用条件和失败反例。核对来源、脱敏及实际验证后才 memory-review accept，默认 project 范围；general 只放可跨项目的方法。原始报告不进入共享索引，不自动改写 SKILL.md。

执行路由：`report.compose`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 执行 fusion.py catalog --capability <id> 按需选择工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

输出：`report/summary.md`、`report/report.md`、`report/coverage.md`、`report/findings.json`、`resume.md`、`learning/candidates.md`。这些交付产物位于当前案件根目录对应路径；运行程序生成的 report/ledger.md、report/coverage.json 是技术报告的输入，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：报告与原始记录一致，所有未完成项可解释，业务负责人可直接验收。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S10 [cloudflare/security-audit-skill · skills/security-audit/VALIDATION-AND-REPORTING.md](https://github.com/cloudflare/security-audit-skill/blob/HEAD/skills/security-audit/VALIDATION-AND-REPORTING.md)
- S01 [GreyDGL/PentestGPT · pentestgpt_agent/README.md](https://github.com/GreyDGL/PentestGPT/blob/HEAD/pentestgpt_agent/README.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
