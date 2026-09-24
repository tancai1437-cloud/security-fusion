---
name: fusion-infra
description: 在指定网络和身份范围内梳理服务、身份边界与可验证路径，为红队评估形成证据和后续工作项。
---

**网络与身份基础设施**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：服务/网络范围；测试身份、环境与路径目标。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先建立资产、服务和身份边界关系，使用明确的单项观察任务；每个步骤包含目标和完成证据。
2. 借用HexStrike的Nmap、枚举及NetExec接口执行适用检查，参数由本次目标与范围生成。
3. 将路径分解为可验证的边，分别记录前提和观察；一个端口可达、一次枚举成功不等于获得完整权限路径。
4. 遇到云或Web控制条件交对应专项；发现新事实后回主控更新计划。用于检测验证时记录预期信号与实际观测，不能以动作返回成功代替检测有效。

执行路由：`service.inventory`、`infra.observe`、`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`infra-map.json`、`path-hypotheses.json`、`observed-controls.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：路径的每条边有已验证/待验证/受阻状态，没有依据的边不串成成功链。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

**方法来源。**

- S03 [AIPentest/CyberStrikeAI · agents/orchestrator-plan-execute.md](https://github.com/AIPentest/CyberStrikeAI/blob/HEAD/agents/orchestrator-plan-execute.md)
- S06 [0x4m4/hexstrike-ai · hexstrike_mcp.py](https://github.com/0x4m4/hexstrike-ai/blob/HEAD/hexstrike_mcp.py)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
