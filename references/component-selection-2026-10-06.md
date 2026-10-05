# 每个环节的三个优先参考与落地改进

检索日期：2026-10-06。沿用 2026-10-02 的 84 项候选调查，重新核对本轮选中的 **32 个不同仓库、13 类、39 个参考席位**。

这里的“最好”指最适合 security-fusion 当前问题的三个优先参考，不是按 stars 排名，也不是声称对 GitHub 全部项目做了实测。综合方法明确程度、DSH 适配成本、可验证性、最近默认分支提交和维护状况筛选。三列按本环节借鉴优先级排列；小型 DSH 插件因接入相关性入选，不能据此称作大众热门。

所有入选仓库在核查时均未归档；最近默认分支提交落在 2026-07-23 至 2026-10-05。页面热度和提交时间不等于成熟度。取指定源码片段或官方文档核对，未安装/运行这些上游框架。只借鉴机制，保持标准库、现有 SQLite、单会话执行，不叠加另一套 Agent 控制器。

## 三选参考与对应改动

| 环节 | 参考 1 | 参考 2 | 参考 3 | 本轮实际落点 |
|---|---|---|---|---|
| 专业研究方法 | [trailofbits/skills](https://github.com/trailofbits/skills) | [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill) | [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) | 当前能力只展示最多三个具体方法及前提；使用当前专项作基线，不要求遍历目录。 |
| 技能与执行路由 | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill) | [Jueze-2019/dsh-redteam-mode](https://github.com/Jueze-2019/dsh-redteam-mode) | 当前路由可用本次 arguments+work 直接继续；切换方法、工具或 schema 重新准备。 |
| MCP 与工具适配 | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp) | [PortSwigger/mcp-server](https://github.com/PortSwigger/mcp-server) | 复用现有真实工具选择、同目标健康记录和 schema 校验；新增当前路由复用与 schema 变化回归。 |
| 上下文管理 | [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | [anomalyco/opencode](https://github.com/anomalyco/opencode) | [volcengine/OpenViking](https://github.com/volcengine/OpenViking) | 宿主恢复默认 focus：最多三条相关结果、两项排队工作、一条全局笔记；长方法指向原文，范围/身份/条件不裁剪。 |
| 执行与证据留存 | [google/adk-python](https://github.com/google/adk-python) | [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | [langfuse/langfuse](https://github.com/langfuse/langfuse) | 自动阶段 Markdown 直接引用真实回执、证据路径/哈希、用时和未决状态；保留原不可变证据副本。 |
| 项目、会话和工具隔离 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | [mem0ai/mem0](https://github.com/mem0ai/mem0) | 隐式路由仅取当前会话；另一会话不回退借用。partial 交付缺失文件也先验证案件内路径。 |
| 中断恢复与去重 | [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py) | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | [temporalio/sdk-python](https://github.com/temporalio/sdk-python) | checkpoint 自动导出可读阶段报告；恢复保留未决优先、真实工作条件与前置证据；不自动重放外部副作用。 |
| 节点复盘 | [trailofbits/skills](https://github.com/trailofbits/skills) | [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | next_check 绑定本案真实 pending 节点；拒绝外案/已完成检查，复盘不增加工具执行。 |
| 任务纵深推进 | [apache/caldera](https://github.com/apache/caldera) | [center-for-threat-informed-defense/attack-flow](https://github.com/center-for-threat-informed-defense/attack-flow) | [Jueze-2019/dsh-redteam-mode](https://github.com/Jueze-2019/dsh-redteam-mode) | 选择顺序为未决回执、有效绑定节点、已满足前置证据的链、其他待执行项；同级沿原顺序。 |
| 经验沉淀与检索 | [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | [mem0ai/mem0](https://github.com/mem0ai/mem0) | [getzep/graphiti](https://github.com/getzep/graphiti) | 恢复时用当前有效节点的问题和下一试验检索，最多取两张完整经验卡后按共享预算纳入；保留检索前项目/专项/有效期过滤。 |
| 报告交付 | [Syslifters/sysreptor](https://github.com/Syslifters/sysreptor) | [DefectDojo/django-DefectDojo](https://github.com/DefectDojo/django-DefectDojo) | [Jueze-2019/dsh-redteam-mode](https://github.com/Jueze-2019/dsh-redteam-mode) | deliver(summary) 自动生成 report/stage.md 并部分交付；列出真实回执和缺失产物，正式 finish/assess 保持验收。 |
| 效果评测 | [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench) | 增加离线 DSH trace 审计，分别识别已路由、实际子调用、未交付、报告声明和模型额度错误；不输出原始错误中的秘密。 |
| 实时漏洞情报与知识库 | [CVEProject/cvelistV5](https://github.com/CVEProject/cvelistV5) | [vulnerability-lookup/vulnerability-lookup](https://github.com/vulnerability-lookup/vulnerability-lookup) | [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei) | CVE 卡片显示受影响产品及版本片段/省略数；REJECTED 和 OSV withdrawn 标为非可操作候选，完整资料仍按哈希保存。 |

## 吸收内容、代码与验收

### 专业研究方法

- [trailofbits/skills](https://github.com/trailofbits/skills/blob/82fe8226252622fa807643bdca1710901198553a/plugins/audit-context-building/skills/audit-context-building/SKILL.md)：沿调用链核对前提与反证。核对层级：`selected_skill`。
- [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill/blob/cab634bd855fc287f6e420c1f36fd1a6b9245960/CTF-Sandbox-Orchestrator/competition-runtime-routing/SKILL.md)：明确专项到工具的入口。核对层级：`selected_skill`。
- [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter/blob/a590333b2f57fa9253b543e55daa0ecca9ad2b66/skills/hunt-dispatch/SKILL.md)：SRC 研究问题与分派机制。核对层级：`selected_skill`。

本轮：当前能力只展示最多三个具体方法及前提；使用当前专项作基线，不要求遍历目录。

代码：[adapters/dsh-routing.mjs](../adapters/dsh-routing.mjs)。

验收：[tests/dsh-routing.test.mjs](../tests/dsh-routing.test.mjs)。

保留缺口：专项深度仍需同模型实测；候选方法前提由证据判断，不能仅靠关键词选中。

### 技能与执行路由

- [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai/blob/c29102a8efe85e0598481fe19d5a8440ab00788e/docs/tools-advanced.md)：参数契约、错误反馈和有界重试的职责划分。核对层级：`documentation`。
- [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill/blob/cab634bd855fc287f6e420c1f36fd1a6b9245960/CTF-Sandbox-Orchestrator/competition-runtime-routing/SKILL.md)：问题到具体专项的路由。核对层级：`selected_skill`。
- [Jueze-2019/dsh-redteam-mode](https://github.com/Jueze-2019/dsh-redteam-mode/blob/c6d63d2e74c9269728df60a211c79cfcac47a66d/packages/redteam-tools/lib/index.js)：DSH 原生工具式管理入口。核对层级：`selected_source_fragments`。

本轮：当前路由可用本次 arguments+work 直接继续；切换方法、工具或 schema 重新准备。

代码：[adapters/dsh-routing.mjs](../adapters/dsh-routing.mjs)、[adapters/dsh.mjs](../adapters/dsh.mjs)。

验收：[tests/dsh-routing.test.mjs](../tests/dsh-routing.test.mjs)、[tests/dsh-schema.test.mjs](../tests/dsh-schema.test.mjs)。

保留缺口：省参数降低摩擦，不能保证模型一定选择正确的研究方法。

### MCP 与工具适配

- [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk/blob/91941ed4d3985d59def99e090baa3f880c626cc8/src/mcp/client/session.py)：协商、schema 与调用结果分离。核对层级：`selected_source_fragments`。
- [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp/blob/5baeacfe20eca735cb949564b4915f93a622b916/fastmcp_slim/fastmcp/client/client.py)：客户端生命周期和失败传播。核对层级：`selected_source_fragments`。
- [PortSwigger/mcp-server](https://github.com/PortSwigger/mcp-server/blob/642e6fa31c63db3886a353fcd7ed62037e0ceed5/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt)：真实 Burp 工具输入输出。核对层级：`selected_source_fragments`。

本轮：复用现有真实工具选择、同目标健康记录和 schema 校验；新增当前路由复用与 schema 变化回归。

代码：[adapters/dsh-routing.mjs](../adapters/dsh-routing.mjs)。

验收：[tests/dsh-routing.test.mjs](../tests/dsh-routing.test.mjs)、[tests/dsh-schema.test.mjs](../tests/dsh-schema.test.mjs)。

保留缺口：保留原工具优先逻辑；未知工具仍需实际接口说明，未遍测所有 MCP。

### 上下文管理

- [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents/blob/b643f6f34be0142fc3e33cd7402f171e62e69cc3/libs/deepagents/deepagents/middleware/filesystem.py)：大内容落盘、按需读取。核对层级：`selected_source_fragments`。
- [anomalyco/opencode](https://github.com/anomalyco/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/compaction.ts)：压缩保留已完成事实和接续方向。核对层级：`selected_source_fragments`。
- [volcengine/OpenViking](https://github.com/volcengine/OpenViking/blob/d9352f2a8bac78cbf4ed08b26543d22adcdd4c93/README.md)：分层文件组织和检索。核对层级：`documentation`。

本轮：宿主恢复默认 focus：最多三条相关结果、两项排队工作、一条全局笔记；长方法指向原文，范围/身份/条件不裁剪。

代码：[scripts/fusion_views.py](../scripts/fusion_views.py)、[adapters/dsh-runtime.mjs](../adapters/dsh-runtime.mjs)。

验收：[tests/test_recovery_progress.py](../tests/test_recovery_progress.py)、[tests/dsh-runtime.test.mjs](../tests/dsh-runtime.test.mjs)。

保留缺口：8000 字符为整条宿主恢复消息硬上限，不等于 token；必需约束过大仍明确报错。

### 执行与证据留存

- [google/adk-python](https://github.com/google/adk-python/blob/0f6a3d562a19d1a45d0d6755fb4ceaca13c50d11/src/google/adk/artifacts/base_artifact_service.py)：产物身份与版本。核对层级：`selected_source_fragments`。
- [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk/blob/39d34ec006f3f92f39863ca890afa5d90720a8ec/openhands-sdk/openhands/sdk/event/base.py)：不可变事件与只读消息投影。核对层级：`selected_source_fragments`。
- [langfuse/langfuse](https://github.com/langfuse/langfuse/blob/b1fc56a8fe1118ba64eb1127c9d8a9489ebceb85/README.md)：工具 trace 和评测分离。核对层级：`documentation`。

本轮：自动阶段 Markdown 直接引用真实回执、证据路径/哈希、用时和未决状态；保留原不可变证据副本。

代码：[scripts/fusion_delivery.py](../scripts/fusion_delivery.py)、[scripts/fusion_views.py](../scripts/fusion_views.py)。

验收：[tests/test_component_upgrade.py](../tests/test_component_upgrade.py)、[tests/dsh-routing.test.mjs](../tests/dsh-routing.test.mjs)。

保留缺口：捕获正确不等于研究解释正确；自动报告不生成漏洞结论。

### 项目、会话和工具隔离

- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph/blob/8e15e0d0bcffa6d3d5a776206e6e8163a3595463/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/__init__.py)：thread/checkpoint 命名空间。核对层级：`selected_source_fragments`。
- [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory/blob/194afe165b3e7676496aaa53b70e39a78ea5aa4f/src/basic_memory/mcp/tools/build_context.py)：显式 project context。核对层级：`selected_source_fragments`。
- [mem0ai/mem0](https://github.com/mem0ai/mem0/blob/c93420c49a6b14c3d446bdb156d96811908fd90a/mem0/memory/main.py)：记忆检索命名空间过滤。核对层级：`selected_source_fragments`。

本轮：隐式路由仅取当前会话；另一会话不回退借用。partial 交付缺失文件也先验证案件内路径。

代码：[adapters/dsh-routing.mjs](../adapters/dsh-routing.mjs)、[adapters/dsh-execution.mjs](../adapters/dsh-execution.mjs)。

验收：[tests/dsh-routing.test.mjs](../tests/dsh-routing.test.mjs)、[tests/dsh-runtime.test.mjs](../tests/dsh-runtime.test.mjs)。

保留缺口：保留现有项目/案件/会话绑定；这是应用约束而非操作系统沙箱。

### 中断恢复与去重

- [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py/blob/03fb5c92cde8e107ff333cd2b419f65e02719e99/dbos/_core.py)：持久状态与重复执行控制。核对层级：`selected_source_fragments`。
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph/blob/8e15e0d0bcffa6d3d5a776206e6e8163a3595463/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/__init__.py)：checkpoint 与 pending writes。核对层级：`selected_source_fragments`。
- [temporalio/sdk-python](https://github.com/temporalio/sdk-python/blob/769e7252c664e8f7484a235d0c5b620532ec4726/README.md)：历史回放和副作用边界。核对层级：`documentation`。

本轮：checkpoint 自动导出可读阶段报告；恢复保留未决优先、真实工作条件与前置证据；不自动重放外部副作用。

代码：[adapters/dsh-execution.mjs](../adapters/dsh-execution.mjs)、[scripts/fusion_views.py](../scripts/fusion_views.py)。

验收：[tests/dsh-runtime.test.mjs](../tests/dsh-runtime.test.mjs)、[tests/test_recovery_progress.py](../tests/test_recovery_progress.py)。

保留缺口：未知外部结果仍须对账，不能宣称跨工具 exactly-once。

### 节点复盘

- [trailofbits/skills](https://github.com/trailofbits/skills/blob/82fe8226252622fa807643bdca1710901198553a/plugins/audit-context-building/skills/audit-context-building/SKILL.md)：前提、调用链和紧凑结论。核对层级：`selected_skill`。
- [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill/blob/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/skills/security-audit/SKILL.md)：证据、信任边界和有效复现。核对层级：`selected_skill`。
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files/blob/dab9d16fbd9314448b319d112e99f497d7638d89/.agents/skills/planning-with-files/SKILL.md)：阶段计划/发现/进度分开落盘。核对层级：`selected_skill`。

本轮：next_check 绑定本案真实 pending 节点；拒绝外案/已完成检查，复盘不增加工具执行。

代码：[scripts/fusion_node_review.py](../scripts/fusion_node_review.py)、[adapters/dsh.mjs](../adapters/dsh.mjs)。

验收：[tests/test_node_review.py](../tests/test_node_review.py)。

保留缺口：本轮建立可执行接续指针；语义结论仍由当前 Agent 判断。

### 任务纵深推进

- [apache/caldera](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/utility/base_planning_svc.py)：事实前提约束规划。核对层级：`selected_source_fragments`。
- [center-for-threat-informed-defense/attack-flow](https://github.com/center-for-threat-informed-defense/attack-flow/blob/8b6ca28bc13beb871f3a4c5fa029b96c6394f874/README.md)：动作之间的顺序与关系。核对层级：`documentation`。
- [Jueze-2019/dsh-redteam-mode](https://github.com/Jueze-2019/dsh-redteam-mode/blob/c6d63d2e74c9269728df60a211c79cfcac47a66d/packages/redteam-tools/lib/index.js)：当前目标问题和研究阶段。核对层级：`selected_source_fragments`。

本轮：选择顺序为未决回执、有效绑定节点、已满足前置证据的链、其他待执行项；同级沿原顺序。

代码：[scripts/fusion_views.py](../scripts/fusion_views.py)、[scripts/fusion_progress.py](../scripts/fusion_progress.py)。

验收：[tests/test_node_review.py](../tests/test_node_review.py)、[tests/test_recovery_progress.py](../tests/test_recovery_progress.py)。

保留缺口：已解决接续优先级；信息增益排序、完整攻击路径图和专项能力盲测尚未完成。

### 经验沉淀与检索

- [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory/blob/194afe165b3e7676496aaa53b70e39a78ea5aa4f/src/basic_memory/mcp/tools/build_context.py)：Markdown 知识与有限上下文查询。核对层级：`selected_source_fragments`。
- [mem0ai/mem0](https://github.com/mem0ai/mem0/blob/c93420c49a6b14c3d446bdb156d96811908fd90a/mem0/memory/main.py)：命名空间和记忆生命周期。核对层级：`selected_source_fragments`。
- [getzep/graphiti](https://github.com/getzep/graphiti/blob/4083f51812d381d7ca28b887cfa3c3db188f576d/graphiti_core/search/search.py)：混合召回与关系上下文。核对层级：`selected_source_fragments`。

本轮：恢复时用当前有效节点的问题和下一试验检索，最多取两张完整经验卡后按共享预算纳入；保留检索前项目/专项/有效期过滤。

代码：[scripts/fusion_progress.py](../scripts/fusion_progress.py)、[scripts/fusion_scope_cli.py](../scripts/fusion_scope_cli.py)。

验收：[tests/test_node_review.py](../tests/test_node_review.py)、[tests/dsh-runtime.test.mjs](../tests/dsh-runtime.test.mjs)。

保留缺口：词法优先，可选已有真实向量；本轮不新增远程 embedding 或自动把任务事实晋升为经验。

### 报告交付

- [Syslifters/sysreptor](https://github.com/Syslifters/sysreptor/blob/85e0202be1e84282880f3e62de4e3e5a4b77886a/README.md)：内容与报告渲染分离。核对层级：`documentation`。
- [DefectDojo/django-DefectDojo](https://github.com/DefectDojo/django-DefectDojo/blob/8b12d80ae30904fed44f5a84ff71f28da14bebaf/dojo/engagement/models.py)：engagement 范围和发现管理。核对层级：`selected_source_fragments`。
- [Jueze-2019/dsh-redteam-mode](https://github.com/Jueze-2019/dsh-redteam-mode/blob/c6d63d2e74c9269728df60a211c79cfcac47a66d/packages/redteam-tools/lib/index.js)：报告中区分真实记录与推断。核对层级：`selected_source_fragments`。

本轮：deliver(summary) 自动生成 report/stage.md 并部分交付；列出真实回执和缺失产物，正式 finish/assess 保持验收。

代码：[scripts/fusion_delivery.py](../scripts/fusion_delivery.py)、[adapters/dsh-execution.mjs](../adapters/dsh-execution.mjs)。

验收：[tests/test_component_upgrade.py](../tests/test_component_upgrade.py)、[tests/dsh-routing.test.mjs](../tests/dsh-routing.test.mjs)。

保留缺口：自动交付只标 partial；完整漏洞结论和正式报告需要人工/Agent 解释证据。

### 效果评测

- [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai/blob/7390f041b89cb162a504715b1c0a8de71d68ed90/README.md)：多轮工具行为评测。核对层级：`documentation`。
- [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo/blob/fa605a9119fdf5ee94b1e7da847e287e197e66d4/README.md)：可复现评测矩阵。核对层级：`documentation`。
- [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench/blob/9a1f4dd5f7659f75707435da3ce854b6e48321d1/README.md)：Skill 使用与最终任务结果分别评估。核对层级：`documentation`。

本轮：增加离线 DSH trace 审计，分别识别已路由、实际子调用、未交付、报告声明和模型额度错误；不输出原始错误中的秘密。

代码：[scripts/evaluate_dsh_trace.py](../scripts/evaluate_dsh_trace.py)。

验收：[tests/test_component_upgrade.py](../tests/test_component_upgrade.py)。

保留缺口：宿主 trace 中的报告/回执仍需案件哈希核验；不从调用数推算漏洞能力或给虚假成功分。

### 实时漏洞情报与知识库

- [CVEProject/cvelistV5](https://github.com/CVEProject/cvelistV5/blob/a0e611645e0c4b37f8e39d60eb623222ca8005f6/README.md)：公开 CVE 状态与 affected 数据。核对层级：`documentation`。
- [vulnerability-lookup/vulnerability-lookup](https://github.com/vulnerability-lookup/vulnerability-lookup/blob/f688ebe6f68ea575cd4b45085ac8fdee9062d76c/README.md)：多来源情报关联。核对层级：`documentation`。
- [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei/blob/1884ed920f542aa54b2310dfb1c8e588a48a1506/README.md)：模板命中之后仍需验证。核对层级：`documentation`。

本轮：CVE 卡片显示受影响产品及版本片段/省略数；REJECTED 和 OSV withdrawn 标为非可操作候选，完整资料仍按哈希保存。

代码：[scripts/fusion_intel.py](../scripts/fusion_intel.py)、[scripts/fusion_knowledge.py](../scripts/fusion_knowledge.py)。

验收：[tests/test_intelligence.py](../tests/test_intelligence.py)、[tests/test_component_upgrade.py](../tests/test_component_upgrade.py)。

保留缺口：实时指按需取源并显示缓存时间；不是后台镜像全量库，候选不代表目标受影响。

## 活跃度与固定版本

以下为核查时的 GitHub 元数据快照，stars 仅反映可见热度。许可证为 API 返回字段；未知不代表可以复制代码。源码 URL 和 SHA256 见配套 JSON。

| 仓库 | Stars | 默认分支提交日期 | 固定提交 | 许可证标识 |
|---|---:|---|---|---|
| [CVEProject/cvelistV5](https://github.com/CVEProject/cvelistV5) | 3031 | 2026-10-05 | [a0e611645e](https://github.com/CVEProject/cvelistV5/commit/a0e611645e0c4b37f8e39d60eb623222ca8005f6) | 未识别 |
| [DefectDojo/django-DefectDojo](https://github.com/DefectDojo/django-DefectDojo) | 4983 | 2026-09-28 | [8b12d80ae3](https://github.com/DefectDojo/django-DefectDojo/commit/8b12d80ae30904fed44f5a84ff71f28da14bebaf) | BSD-3-Clause |
| [Jueze-2019/dsh-redteam-mode](https://github.com/Jueze-2019/dsh-redteam-mode) | 68 | 2026-09-30 | [c6d63d2e74](https://github.com/Jueze-2019/dsh-redteam-mode/commit/c6d63d2e74c9269728df60a211c79cfcac47a66d) | MIT |
| [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | 1202 | 2026-10-05 | [39d34ec006](https://github.com/OpenHands/software-agent-sdk/commit/39d34ec006f3f92f39863ca890afa5d90720a8ec) | MIT |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27295 | 2026-10-01 | [dab9d16fbd](https://github.com/OthmanAdi/planning-with-files/commit/dab9d16fbd9314448b319d112e99f497d7638d89) | MIT |
| [PortSwigger/mcp-server](https://github.com/PortSwigger/mcp-server) | 1215 | 2026-08-12 | [642e6fa31c](https://github.com/PortSwigger/mcp-server/commit/642e6fa31c63db3886a353fcd7ed62037e0ceed5) | GPL-3.0 |
| [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp) | 27980 | 2026-10-05 | [5baeacfe20](https://github.com/PrefectHQ/fastmcp/commit/5baeacfe20eca735cb949564b4915f93a622b916) | Apache-2.0 |
| [Syslifters/sysreptor](https://github.com/Syslifters/sysreptor) | 2594 | 2026-10-01 | [85e0202be1](https://github.com/Syslifters/sysreptor/commit/85e0202be1e84282880f3e62de4e3e5a4b77886a) | NOASSERTION |
| [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | 2939 | 2026-10-05 | [7390f041b8](https://github.com/UKGovernmentBEIS/inspect_ai/commit/7390f041b89cb162a504715b1c0a8de71d68ed90) | MIT |
| [anomalyco/opencode](https://github.com/anomalyco/opencode) | 211842 | 2026-10-03 | [907b3bc518](https://github.com/anomalyco/opencode/commit/907b3bc518fa48e90e8ec24dd327d13eee71c36c) | MIT |
| [apache/caldera](https://github.com/apache/caldera) | 7307 | 2026-08-27 | [cb8d6a8160](https://github.com/apache/caldera/commit/cb8d6a8160e0f4990af323a7c071d5e8482b42c7) | Apache-2.0 |
| [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | 4100 | 2026-10-02 | [194afe165b](https://github.com/basicmachines-co/basic-memory/commit/194afe165b3e7676496aaa53b70e39a78ea5aa4f) | AGPL-3.0 |
| [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench) | 1830 | 2026-07-23 | [9a1f4dd5f7](https://github.com/benchflow-ai/skillsbench/commit/9a1f4dd5f7659f75707435da3ce854b6e48321d1) | Apache-2.0 |
| [center-for-threat-informed-defense/attack-flow](https://github.com/center-for-threat-informed-defense/attack-flow) | 777 | 2026-09-24 | [8b6ca28bc1](https://github.com/center-for-threat-informed-defense/attack-flow/commit/8b6ca28bc13beb871f3a4c5fa029b96c6394f874) | Apache-2.0 |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 24668 | 2026-09-14 | [c1c8a8c147](https://github.com/cloudflare/security-audit-skill/commit/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8) | MIT |
| [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py) | 1607 | 2026-10-01 | [03fb5c92cd](https://github.com/dbos-inc/dbos-transact-py/commit/03fb5c92cde8e107ff333cd2b419f65e02719e99) | MIT |
| [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) | 4776 | 2026-10-05 | [a590333b2f](https://github.com/elementalsouls/Claude-BugHunter/commit/a590333b2f57fa9253b543e55daa0ecca9ad2b66) | MIT |
| [getzep/graphiti](https://github.com/getzep/graphiti) | 31450 | 2026-10-05 | [4083f51812](https://github.com/getzep/graphiti/commit/4083f51812d381d7ca28b887cfa3c3db188f576d) | Apache-2.0 |
| [google/adk-python](https://github.com/google/adk-python) | 21711 | 2026-10-05 | [0f6a3d562a](https://github.com/google/adk-python/commit/0f6a3d562a19d1a45d0d6755fb4ceaca13c50d11) | Apache-2.0 |
| [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | 29951 | 2026-10-05 | [b643f6f34b](https://github.com/langchain-ai/deepagents/commit/b643f6f34be0142fc3e33cd7402f171e62e69cc3) | MIT |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 42739 | 2026-10-05 | [8e15e0d0bc](https://github.com/langchain-ai/langgraph/commit/8e15e0d0bcffa6d3d5a776206e6e8163a3595463) | MIT |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | 35403 | 2026-10-05 | [b1fc56a8fe](https://github.com/langfuse/langfuse/commit/b1fc56a8fe1118ba64eb1127c9d8a9489ebceb85) | NOASSERTION |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 66598 | 2026-10-05 | [c93420c49a](https://github.com/mem0ai/mem0/commit/c93420c49a6b14c3d446bdb156d96811908fd90a) | Apache-2.0 |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | 24493 | 2026-10-05 | [91941ed4d3](https://github.com/modelcontextprotocol/python-sdk/commit/91941ed4d3985d59def99e090baa3f880c626cc8) | MIT |
| [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei) | 31745 | 2026-10-05 | [1884ed920f](https://github.com/projectdiscovery/nuclei/commit/1884ed920f542aa54b2310dfb1c8e588a48a1506) | MIT |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | 25722 | 2026-10-05 | [fa605a9119](https://github.com/promptfoo/promptfoo/commit/fa605a9119fdf5ee94b1e7da847e287e197e66d4) | MIT |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | 20417 | 2026-10-05 | [c29102a8ef](https://github.com/pydantic/pydantic-ai/commit/c29102a8efe85e0598481fe19d5a8440ab00788e) | MIT |
| [temporalio/sdk-python](https://github.com/temporalio/sdk-python) | 1209 | 2026-10-05 | [769e7252c6](https://github.com/temporalio/sdk-python/commit/769e7252c664e8f7484a235d0c5b620532ec4726) | MIT |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7372 | 2026-09-28 | [82fe822625](https://github.com/trailofbits/skills/commit/82fe8226252622fa807643bdca1710901198553a) | CC-BY-SA-4.0 |
| [volcengine/OpenViking](https://github.com/volcengine/OpenViking) | 39234 | 2026-10-05 | [d9352f2a8b](https://github.com/volcengine/OpenViking/commit/d9352f2a8bac78cbf4ed08b26543d22adcdd4c93) | AGPL-3.0 |
| [vulnerability-lookup/vulnerability-lookup](https://github.com/vulnerability-lookup/vulnerability-lookup) | 580 | 2026-10-05 | [f688ebe6f6](https://github.com/vulnerability-lookup/vulnerability-lookup/commit/f688ebe6f68ea575cd4b45085ac8fdee9062d76c) | AGPL-3.0 |
| [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill) | 39794 | 2026-09-22 | [cab634bd85](https://github.com/zhaoxuya520/reverse-skill/commit/cab634bd855fc287f6e420c1f36fd1a6b9245960) | MIT |

## 运行时的变化

1. route 后提交新的 arguments 和 work，即可沿当前路由执行；无目标/会话推断回退。
2. 节点可绑定 next_check；先对账，再接有效证据链，避免从头找方向。
3. 压缩恢复只装当前工作集；完整方法、长证据和历史按指针读。
4. checkpoint 自动导出阶段报告；deliver 自动提交 partial 阶段，缺失产物如实列出。
5. CVE/OSV 撤回状态与真实目标适用性分开；记忆检索围绕当前有效节点。
6. 使用离线 trace 评测器识别“零调用额度错误”和“执行过但没交付”，不推断成功率。

没有数据库迁移、没有新增生产依赖、没有把 32 个项目打包进 Skill。恢复与路由的严格边界仍由宿主代码执行；具体研究选择和最终语义判断保留给模型。

## 验证与回退

本轮验证结果见 [改造验收记录](component-validation-2026-10-06.md)。新机制先以离线回执、临时文件和 DSH SDK 做回归；旧模型 trace 只用于评测器的事实校验，不作为新版本实战成绩。

回退基线为 `99b66797eb6f04f9688605ce9dcd9ae8467ab10e`。可部署该版本的 Skill 与配套宿主模块；案件数据库结构未变，新增 node_review.next_check 只是事件字段。切换版本后重新准备 route，不复用旧方法指纹。回退不用删除案件或重置其他项目改动。
