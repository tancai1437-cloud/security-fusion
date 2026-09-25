---
name: fusion-ai
description: 评估LLM应用、RAG与Agent的身份、检索和工具权限边界，使用受控测试数据判断真实影响。
---

**AI应用与工具边界**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：AI应用范围与数据/工具边界；测试身份和合成标记。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先画出用户输入、检索内容、系统指令、工具调用及数据存储的信任边界。
2. 使用受控数据和测试身份，区分模型文本、实际读取的数据和真实工具动作。模型声称拿到信息不能单独成为证据。
3. 对关键行为重复观察并设置负例，记录模型/应用版本与状态，避免把一次随机输出推导为稳定漏洞。
4. 跨身份/租户结果回fusion-api核对；涉及工具权限的结果绑定实际请求和服务端状态，再交统一验证。

**执行与文本分开。** 分别保存模型输出、实际工具请求和工具结果，只有真实越界结果支持相应结论。看见工具名只触发能力/身份核对，模型声称执行成功不算证据；按需读 [AI 工具边界](../../references/field-methods.md#ai)。

执行路由：`browser.observe`、`http.history`、`http.request`、`ai.boundary`、`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`ai-boundaries.json`、`controlled-observations.json`、`ai-candidates.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：每个候选都指向可复查的边界影响，模型措辞与实际行为分开报告。

宿主有 fusion 时继续 execute，以 review 提交上一回执的实际结论；阶段暂停用 checkpoint，交付用 finish。没有宿主组件才用 [advance](../../references/observation-routing.md#简化入口advance)。保存阴性、反证和阻塞；只在阶段结束整理产物，不等用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S28 [elementalsouls/Claude-BugHunter · skills/hunt-llm-ai/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-llm-ai/SKILL.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
