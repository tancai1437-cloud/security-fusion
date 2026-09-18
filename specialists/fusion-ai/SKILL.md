---
name: fusion-ai
description: 评估LLM应用、RAG与Agent的身份、检索和工具权限边界，使用受控测试数据判断真实影响。
---

**AI应用与工具边界**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：AI应用范围与数据/工具边界；测试身份和合成标记。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先画出用户输入、检索内容、系统指令、工具调用及数据存储的信任边界。
2. 使用受控数据和测试身份，区分模型文本、实际读取的数据和真实工具动作。模型声称拿到信息不能单独成为证据。
3. 对关键行为重复观察并设置负例，记录模型/应用版本与状态，避免把一次随机输出推导为稳定漏洞。
4. 跨身份/租户结果回fusion-api核对；涉及工具权限的结果绑定实际请求和服务端状态，再交统一验证。

执行路由：`browser.observe`、`http.history`、`http.request`、`ai.boundary`、`code.inspect`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 执行 fusion.py catalog --capability <id> 按需选择工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

输出：`ai-boundaries.json`、`controlled-observations.json`、`ai-candidates.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：每个候选都指向可复查的边界影响，模型措辞与实际行为分开报告。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S28 [elementalsouls/Claude-BugHunter · skills/hunt-llm-ai/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-llm-ai/SKILL.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
