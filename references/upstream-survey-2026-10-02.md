# GitHub 分类选型与蒸馏 · 2026-10-02

快照时间：2026-10-02T07:36:58.399628+00:00。84 个候选、83 个取得公开元数据，选读 37 个项目的 60 份固定版本源码/文档。1 个候选获取失败；没有把无法读取当成停更。

这是有边界的代表性调查，不是 GitHub 全量遍历或最优排名。10 组检索各取 stars 排序前 5 个，再加入用户指定项目及相关代表实现。源码选读覆盖与 README 级参考分开；未执行上游代码，没有移植其效果分数。完整查询、时间、SHA、文件哈希与取舍见 [机器可核查快照](upstream-survey-2026-10-02.json)。

## 选择原则

文件 SHA-256 按 GitHub CLI 解码后的 UTF-8 文本、LF 换行计算，60 份本地研究副本均已按该规则核验；固定 commit 与 blob URL 保留原仓库版本身份，不将文本指纹称作传输原始字节哈希。

任务适配与可验证机制优先，其次看上下文/部署成本、隔离边界、维护情况、许可与测试。stars 是关注度；默认分支最近提交是活跃线索，都不证明实战效果。近 90 天提交且未归档只标为近期维护，不声称每次提交都是有效改进。仓库 SPDX 是元数据快照，采用具体文件仍需核对其许可。

采用一项机制可以只改本地实现，不等于安装整套框架。runtime 不伪装成需要模型反复调用的 Skill，MCP 服务不伪装成已验证的专业方法。原始外部文件仅留本地研究目录，不随技能发布。

## 按需求分别融合

| 需求 | 优先借鉴 | 本包选择与剩余边界 |
|---|---|---|
| 专业方法 | Trail of Bits、reverse-skill、Claude-BugHunter、aimy | 保留具体问题/前提/反证/转向；未扩写成未经实测的全领域专家 |
| MCP/工具 | 官方 MCP SDK、Burp、IDA、Playwright、jshook、HexStrike | 使用真实接口与当前上下文，工具注册/健康/有效证据分开 |
| 少占上下文 | DeepAgents、OpenCode、Pi、OpenViking | 方法只载一项，大输出落盘，摘要/索引/原文分层 |
| 留痕与产物 | OpenHands SDK、ADK、Langfuse | 调用事件与产物版本独立；保留本地账本，不外传案件 |
| 同项目多目标 | LangGraph、Basic Memory、Mem0、OpenSandbox | 案件/会话先过滤；强沙箱是备选，当前逻辑隔离不能冒充 OS 隔离 |
| 中断恢复 | DBOS、LangGraph；Temporal 作架构备选 | 重用已捕获步骤；未知外部副作用先核对，不能宣称 exactly-once |
| 节点复盘 | ToB 反证、DeepAgents rubric、planning-with-files | 新增证据关联节点；同 Agent 顺序复核，不再加平行状态文件 |
| 长任务纵深 | CALDERA、Attack Flow | 事实/前提/路径与下一试验；完整动态调度和路径图仍未实现 |
| 经验检索 | Basic Memory、Mem0、Graphiti、OpenViking | 案件事实与脱敏方法分开；本地词法默认，真实向量可选 |
| 报告/复测 | Cloudflare audit、DefectDojo、Atomic Red Team | 结论状态与证据分开；统一遥测、清理和复测仍有缺口 |
| 效果评测 | Inspect、Promptfoo、SkillsBench、Phoenix | 同条件对照和真实结果评分；仓库测试不当作实战成功率 |

## 37 个重点项目的取舍

`source`=源码/技能正文选读；`docs/schema_docs`=机制文档或规格；`readme`=项目自述级，仅作候选依据。三者都不是已完成本地集成。

| 项目（固定来源） | stars | 默认分支提交 | 采用的机制 | 不采纳/边界 | 阅读层级 |
|---|---:|---|---|---|---|
| [trailofbits/skills](https://github.com/trailofbits/skills/blob/82fe8226252622fa807643bdca1710901198553a/plugins/audit-context-building/skills/audit-context-building/SKILL.md) | 7,333 | 2026-09-28 | 调用上下文、反证、先精确实例再找变体 | 保留方法和案例级证据；不导入其子代理委派要求 | source |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill/blob/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/skills/security-audit/SKILL.md) | 23,681 | 2026-09-14 | 发现状态、证据复核、从最终记录生成报告 | 采用状态语义；严格文件提升规则须按本运行环境实现，不能只抄要求 | source |
| [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill/blob/cab634bd855fc287f6e420c1f36fd1a6b9245960/skills/routing.md) | 39,290 | 2026-09-22 | 目标类型×意图×工具链分流；以结构化路由为准 | 采用按需专项和跨专项返回；不继承固定环境地址、预置范围或整套目录 | source |
| [Prohao42/aimy-skill](https://github.com/Prohao42/aimy-skill/blob/195da56295e44edc72b63723ef64200bf2524769/ai-mian/hack-skills/skills/api-authorization-and-bola/SKILL.md) | 254 | 2026-09-28 | 问题卡包含遗漏面和下一路由 | 采用方法卡结构；不把示例输入、宽泛漏洞目录或作者自述当验证 | source |
| [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter/blob/66e171cffd54de448fa8d10af415b60763b03edc/skills/hunt-dispatch/SKILL.md) | 4,744 | 2026-10-01 | 按现场特征分流；候选逐项 triage | 使用当前范围；不从调用技能本身推断授权，不固定照搬平台规则 | source |
| [0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai/blob/d689933ff579d839c676c82b231f8e98326c5f04/hexstrike_mcp.py) | 12,280 | 2026-08-03 | 将本地工具暴露为明确 MCP 接口 | 作为可选执行器；不接管任务规划，不全量安装工具集 | source |
| [PortSwigger/mcp-server](https://github.com/PortSwigger/mcp-server/blob/642e6fa31c63db3886a353fcd7ed62037e0ceed5/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt) | 1,205 | 2026-08-12 | 代理历史与请求工具的实际参数和数据访问边界 | 已有 Burp 工程时按接口选用；不会因仓库存在而标就绪 | source |
| [mrexodia/ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp/blob/c133c3853faa111a9b00ee615c013b720d0c4acd/src/ida_pro_mcp/ida_mcp/api_core.py) | 12,432 | 2026-09-26 | 当前 IDB 状态、健康接口、函数与引用分析 | 需要实际样本/工程绑定；安装及授权条件单独核验 | source |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp/blob/f183dad4a52965583e3cc1d59b88cdc279e2e57d/README.md) | 37,752 | 2026-09-28 | 浏览器状态、按需可访问性快照；MCP/CLI 使用取舍 | 按任务和已连接上下文选择，不强制浏览器工具替换 HTTP 通道 | readme |
| [vmoranv/jshookmcp](https://github.com/vmoranv/jshookmcp/blob/39313f797bb93b4d825014220bc6555a58b1a937/src/server/MCPServer.tools.ts) | 2,019 | 2026-09-28 | 工具 schema 与元工具发现/调用分离 | 沿当前浏览器会话；不把工具发现当运行采样 | source |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk/blob/17aaf2557205c3768ed61831398a4e074b21e96d/src/mcp/client/session.py) | 24,451 | 2026-10-01 | 实际协议会话、能力查询与调用生命周期 | 借接口边界；当前标准库 stdio 路径不新增 SDK 依赖 | source |
| [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp/blob/d7a3c93877fae50919bdf9e06274220f04cbc6e6/fastmcp_slim/fastmcp/client/client.py) | 27,955 | 2026-10-02 | 统一 MCP 客户端及会话生命周期 | 备选适配实现；不同时引入多套客户端状态源 | source |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph/blob/157a06dda988d85afeb8751ff27b35ab3f4f8bf4/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/__init__.py) | 42,596 | 2026-10-01 | thread/namespace/checkpoint 组合主键与持久状态 | 保留本地 SQLite；借检查点边界，不更换主 Agent 框架 | source |
| [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents/blob/7bc94742bb503772e207a46d29bbd7cea13e7129/libs/deepagents/deepagents/middleware/filesystem.py) | 29,901 | 2026-10-02 | 大结果落盘、摘要与完整事件分离、有限 rubric 评估 | 吸收按需读取和节点条件；不启用外部子代理/额外 grader 服务 | source |
| [anomalyco/opencode](https://github.com/anomalyco/opencode/blob/1ddb0873aee50d209d1a8d7f91b89c5daf692d49/packages/core/src/session/compaction.ts) | 211,383 | 2026-10-02 | 截断输出保留文件路径；压缩保留目标、约束与更新 | 采用预算和回读指针；当前不宣称已接入 OpenCode hook | source |
| [earendil-works/pi](https://github.com/earendil-works/pi/blob/7fbbd5f4a1d982bb02d63472dde0774fa639f99b/packages/coding-agent/docs/compaction.md) | 111,432 | 2026-10-01 | 会话树、压缩事件和分支摘要 | 学习可追溯视图；Pi 适配仍需独立联调 | docs |
| [letta-ai/letta](https://github.com/letta-ai/letta/blob/5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a/README.md) | 25,004 | 2026-09-10 | 持久 Agent 身份与记忆运行产品 | 仅 README 级备选；不把产品宣称当精读实现或引入整套服务器 | readme |
| [mem0ai/mem0](https://github.com/mem0ai/mem0/blob/abb81c88e1f738a8117d8293530fbc31a5ef8fd9/mem0/memory/main.py) | 66,456 | 2026-10-01 | user/agent/run 范围字段独立于自由元数据 | 先作用域过滤再召回；不让模型文本覆盖租户或案件身份 | source |
| [getzep/graphiti](https://github.com/getzep/graphiti/blob/3c427640abf909f12f71f963fce15eb514a3c493/graphiti_core/search/search.py) | 31,371 | 2026-09-30 | group_id 限定检索及图检索接口 | 复杂关系召回备选；不增加图数据库，不默认跨案融合事实 | source |
| [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory/blob/194afe165b3e7676496aaa53b70e39a78ea5aa4f/src/basic_memory/mcp/tools/build_context.py) | 4,076 | 2026-10-02 | Markdown 资料、项目解析和受限上下文构建 | 人读 MD、程序维护索引；明确案件范围，不按最近项目猜测 | source |
| [volcengine/OpenViking](https://github.com/volcengine/OpenViking/blob/df32bf6e50a40843438f9491a26069ca4bd08f1f/README.md) | 39,118 | 2026-10-02 | L0 摘要/L1 概览/L2 原文的分层读取 | 吸收分层读取；自报 token/准确率不作为本包效果证据 | readme |
| [mksglu/context-mode](https://github.com/mksglu/context-mode/blob/928bdf104bca04da977fc6e6095dc3d0328939df/README.md) | 24,864 | 2026-10-02 | MCP-only 与带宿主 hook 的能力分开 | 采纳接入能力分级；README 压缩收益未经本包复验 | readme |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files/blob/dab9d16fbd9314448b319d112e99f497d7638d89/.agents/skills/planning-with-files/SKILL.md) | 27,255 | 2026-10-01 | 命名任务目录与磁盘计划/发现/进展 | 节点复盘写入既有事件源；避免另建三份可漂移状态真源 | source |
| [langfuse/langfuse](https://github.com/langfuse/langfuse/blob/9a29212e855c60ffb86d1989b62918b3781d9652/README.md) | 35,293 | 2026-10-01 | 调用链追踪、实验和成本观察 | 学习 trace/证据/评价分离；不部署 ClickHouse 等服务、不外传案情 | readme |
| [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix/blob/7ea5dc10be15a283f8a25b87b24516e0b66c7b7f/README.md) | 11,677 | 2026-10-02 | OpenTelemetry 跟踪、版本化数据集与实验 | 作为外接观察候选；先维持本地评测，不把 LLM 评分当唯一裁判 | readme |
| [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk/blob/53a4bc5014902ca84bb21fff30eac606ff4905aa/openhands-sdk/openhands/sdk/context/condenser/README.md) | 1,192 | 2026-10-01 | 加锁持久事件日志与压缩视图分离 | 复用本包事件表；保留原始记录，仅替换模型工作视图 | source |
| [google/adk-python](https://github.com/google/adk-python/blob/f33343fbfe7bac9d99b977bf3f59b51908ab996e/src/google/adk/artifacts/base_artifact_service.py) | 21,690 | 2026-10-02 | 产物版本、canonical URI 与会话归属 | 采用版本化指针和归属；不增加 ADK 框架 | source |
| [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py/blob/03fb5c92cde8e107ff333cd2b419f65e02719e99/dbos/_core.py) | 1,601 | 2026-10-01 | 持久步骤返回值及恢复时复用已记录结果 | 本地模拟同类恢复语义；不把外部副作用承诺为 exactly-once | source |
| [temporalio/temporal](https://github.com/temporalio/temporal/blob/79c467689b592727762da92c7e7a0d7bb2384595/README.md) | 23,414 | 2026-10-02 | 持久执行平台的运行模型 | 架构备选；这里只读 README，语义细节不据此作保证，不加常驻服务 | readme |
| [apache/caldera](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/utility/base_planning_svc.py) | 7,302 | 2026-08-27 | 事实满足前提后才形成动作，计划过滤未满足关系 | 吸收依赖/事实驱动；不部署其控制基础设施，不新增攻击能力 | source |
| [center-for-threat-informed-defense/attack-flow](https://github.com/center-for-threat-informed-defense/attack-flow/blob/8b6ca28bc13beb871f3a4c5fa029b96c6394f874/docs/usage_guides/red-team.rst) | 777 | 2026-09-24 | 动作、条件与结果的路径表达；红蓝结果对照 | 用于节点/路径设计；完整图引擎与防守遥测仍是缺口 | schema_docs |
| [redcanaryco/atomic-red-team](https://github.com/redcanaryco/atomic-red-team/blob/388942adbd9641f4dfdcf079d7efe9a75ec0ac43/atomics/T1082/T1082.yaml) | 12,602 | 2026-09-05 | 单项测试的输入、依赖与清理声明 | 借测试契约；不复制或执行原子测试，统一清理验收尚未实现 | source |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo/blob/94119b67648756bf475a950885b2799c1694f1c2/README.md) | 25,635 | 2026-10-01 | 用版本化评测比较提示、模型与应用行为 | 候选评测工具；未安装、未运行其红队测试 | readme |
| [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai/blob/c05398d897affcb85bd4cb9d10a7c03e1779a18e/README.md) | 2,911 | 2026-10-02 | 独立评测框架与可复查评分接口 | 基准候选；需增加领域任务集，README 不证明本技能提升 | readme |
| [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench/blob/9a1f4dd5f7659f75707435da3ce854b6e48321d1/README.md) | 1,827 | 2026-07-23 | 将技能效果与 Agent 行为作为独立评测目标 | 吸收有/无技能对照；其成绩不迁移成本包成绩 | readme |
| [DefectDojo/django-DefectDojo](https://github.com/DefectDojo/django-DefectDojo/blob/8b12d80ae30904fed44f5a84ff71f28da14bebaf/dojo/engagement/models.py) | 4,976 | 2026-09-28 | engagement 与 finding 独立归属，发现有多种业务状态 | 沿本案输出；不部署 Django 平台或迁移数据结构 | source |
| [opensandbox-group/OpenSandbox](https://github.com/opensandbox-group/OpenSandbox/blob/c7dc78a4090e5de2b9119e9bd93952cae24f87bd/README.md) | 15,645 | 2026-10-01 | 每次实验独立执行环境与生命周期 | 强隔离备选；本轮无 Docker/K8s 部署，不能写成已启用沙箱 | readme |

## 候选全集与筛选边界

没有进入重点选读的项目只完成元数据筛查，不据此作技术优劣判断。搜索也可能返回课程、清单、旧书和相邻领域项目；这些不会因 stars 高自动并入运行路径。

| 仓库 | stars | 默认分支提交 | 许可证元数据 | 状态 |
|---|---:|---|---|---|
| [0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai) | 12,280 | 2026-08-03 | MIT | 重点选读 |
| [0xSteph/pentest-ai](https://github.com/0xSteph/pentest-ai) | 1,713 | 2026-09-13 | MIT | 仅元数据 |
| [anomalyco/opencode](https://github.com/anomalyco/opencode) | 211,383 | 2026-10-02 | MIT | 重点选读 |
| [anthropics/skills](https://github.com/anthropics/skills) | 179,359 | 2026-09-29 | 未声明 | 仅元数据 |
| [apache/caldera](https://github.com/apache/caldera) | 7,302 | 2026-08-27 | Apache-2.0 | 重点选读 |
| [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | 11,677 | 2026-10-02 | NOASSERTION | 重点选读 |
| [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | 4,076 | 2026-10-02 | AGPL-3.0 | 重点选读 |
| [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench) | 1,827 | 2026-07-23 | Apache-2.0 | 重点选读 |
| [berabuddies/Semia](https://github.com/berabuddies/Semia) | 608 | 2026-06-05 | Apache-2.0 | 仅元数据 |
| [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp) | 4,090 | 2026-09-29 | Apache-2.0 | 仅元数据 |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | 116,980 | 2026-10-02 | MIT | 仅元数据 |
| [bytedance/deer-flow](https://github.com/bytedance/deer-flow) | 83,328 | 2026-10-01 | MIT | 仅元数据 |
| [center-for-threat-informed-defense/attack-flow](https://github.com/center-for-threat-informed-defense/attack-flow) | 777 | 2026-09-24 | Apache-2.0 | 重点选读 |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 23,681 | 2026-09-14 | MIT | 重点选读 |
| [ComposioHQ/composio](https://github.com/ComposioHQ/composio) | 30,394 | 2026-10-02 | MIT | 仅元数据 |
| [conductor-oss/conductor](https://github.com/conductor-oss/conductor) | 32,254 | 2026-10-01 | Apache-2.0 | 仅元数据 |
| [dataelement/bisheng](https://github.com/dataelement/bisheng) | 12,019 | 2026-09-23 | Apache-2.0 | 仅元数据 |
| [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py) | 1,601 | 2026-10-01 | MIT | 重点选读 |
| [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | 241,946 | 2026-09-29 | MIT | 仅元数据 |
| [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 26,638 | 2026-10-01 | Apache-2.0 | 仅元数据 |
| [DefectDojo/django-DefectDojo](https://github.com/DefectDojo/django-DefectDojo) | 4,976 | 2026-09-28 | BSD-3-Clause | 重点选读 |
| [doobidoo/mcp-memory-service](https://github.com/doobidoo/mcp-memory-service) | 1,978 | 2026-10-02 | Apache-2.0 | 仅元数据 |
| [earendil-works/pi](https://github.com/earendil-works/pi) | 111,432 | 2026-10-01 | MIT | 重点选读 |
| [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) | 4,744 | 2026-10-01 | MIT | 重点选读 |
| [evidentlyai/evidently](https://github.com/evidentlyai/evidently) | 7,956 | 2026-09-10 | Apache-2.0 | 仅元数据 |
| [getzep/graphiti](https://github.com/getzep/graphiti) | 31,371 | 2026-09-30 | Apache-2.0 | 重点选读 |
| [google/adk-python](https://github.com/google/adk-python) | 21,690 | 2026-10-02 | Apache-2.0 | 重点选读 |
| [H-mmer/pentest-agents](https://github.com/H-mmer/pentest-agents) | 981 | 2026-05-06 | 未声明 | 仅元数据 |
| [hatchet-dev/hatchet](https://github.com/hatchet-dev/hatchet) | 8,043 | 2026-10-01 | MIT | 仅元数据 |
| [IBM/AssetOpsBench](https://github.com/IBM/AssetOpsBench) | 2,326 | 2026-09-25 | Apache-2.0 | 仅元数据 |
| [iosre/iOSAppReverseEngineering](https://github.com/iosre/iOSAppReverseEngineering) | 4,423 | 2015-09-17 | MIT | 仅元数据 |
| [jacob-bd/gemini-notebook-mcp-cli](https://github.com/jacob-bd/gemini-notebook-mcp-cli) | 6,205 | 2026-10-01 | MIT | 仅元数据 |
| [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | 29,901 | 2026-10-02 | MIT | 重点选读 |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 42,596 | 2026-10-01 | MIT | 重点选读 |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | 35,293 | 2026-10-01 | NOASSERTION | 重点选读 |
| [letta-ai/letta](https://github.com/letta-ai/letta) | 25,004 | 2026-09-10 | Apache-2.0 | 重点选读 |
| ljagiello/ctf-skills | 未取得 | 未取得 | 未取得 | 获取失败，未判断 |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 66,456 | 2026-10-01 | Apache-2.0 | 重点选读 |
| [memgraph/memgraph](https://github.com/memgraph/memgraph) | 4,589 | 2026-10-01 | NOASSERTION | 仅元数据 |
| [memvid/memvid](https://github.com/memvid/memvid) | 16,572 | 2026-07-14 | Apache-2.0 | 仅元数据 |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | 37,752 | 2026-09-28 | Apache-2.0 | 重点选读 |
| [mksglu/context-mode](https://github.com/mksglu/context-mode) | 24,864 | 2026-10-02 | NOASSERTION | 重点选读 |
| [mlflow/mlflow](https://github.com/mlflow/mlflow) | 28,224 | 2026-10-02 | Apache-2.0 | 仅元数据 |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | 24,451 | 2026-10-01 | MIT | 重点选读 |
| [mrexodia/ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp) | 12,432 | 2026-09-26 | MIT | 重点选读 |
| [muratcankoylan/Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) | 18,060 | 2026-10-01 | MIT | 仅元数据 |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 29,799 | 2026-10-02 | MIT | 仅元数据 |
| [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | 89,769 | 2026-10-02 | MIT | 仅元数据 |
| [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | 1,192 | 2026-10-01 | MIT | 重点选读 |
| [opensandbox-group/OpenSandbox](https://github.com/opensandbox-group/OpenSandbox) | 15,645 | 2026-10-01 | Apache-2.0 | 重点选读 |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27,255 | 2026-10-01 | MIT | 重点选读 |
| [OWASP/wstg](https://github.com/OWASP/wstg) | 9,933 | 2026-09-30 | CC-BY-SA-4.0 | 仅元数据 |
| [P4nda0s/reverse-skills](https://github.com/P4nda0s/reverse-skills) | 2,216 | 2026-05-06 | 未声明 | 仅元数据 |
| [panaversity/learn-agentic-ai](https://github.com/panaversity/learn-agentic-ai) | 4,386 | 2025-10-26 | MIT | 仅元数据 |
| [PortSwigger/mcp-server](https://github.com/PortSwigger/mcp-server) | 1,205 | 2026-08-12 | GPL-3.0 | 重点选读 |
| [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp) | 27,955 | 2026-10-02 | Apache-2.0 | 重点选读 |
| [Prohao42/aimy-skill](https://github.com/Prohao42/aimy-skill) | 254 | 2026-09-28 | MIT | 重点选读 |
| [prompt-security/clawsec](https://github.com/prompt-security/clawsec) | 1,110 | 2026-09-28 | AGPL-3.0 | 仅元数据 |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | 25,635 | 2026-10-01 | MIT | 重点选读 |
| [raga-ai-hub/RagaAI-Catalyst](https://github.com/raga-ai-hub/RagaAI-Catalyst) | 16,172 | 2025-05-16 | Apache-2.0 | 仅元数据 |
| [raroque/vibe-security-skill](https://github.com/raroque/vibe-security-skill) | 1,076 | 2026-03-15 | MIT | 仅元数据 |
| [redcanaryco/atomic-red-team](https://github.com/redcanaryco/atomic-red-team) | 12,602 | 2026-09-05 | MIT | 重点选读 |
| [ruvnet/RuVector](https://github.com/ruvnet/RuVector) | 4,531 | 2026-09-30 | MIT | 仅元数据 |
| [shinthink/blitzstrike](https://github.com/shinthink/blitzstrike) | 493 | 2026-10-02 | MIT | 仅元数据 |
| [SimoneAvogadro/android-reverse-engineering-skill](https://github.com/SimoneAvogadro/android-reverse-engineering-skill) | 7,949 | 2026-09-08 | Apache-2.0 | 仅元数据 |
| [tanweai/wooyun-legacy](https://github.com/tanweai/wooyun-legacy) | 1,777 | 2026-07-14 | NOASSERTION | 仅元数据 |
| [temporalio/temporal](https://github.com/temporalio/temporal) | 23,414 | 2026-10-02 | MIT | 重点选读 |
| [TencentCloud/TencentDB-Agent-Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory) | 27,633 | 2026-09-29 | NOASSERTION | 仅元数据 |
| [THUDM/AgentBench](https://github.com/THUDM/AgentBench) | 3,761 | 2026-02-08 | Apache-2.0 | 仅元数据 |
| [topoteretes/cognee](https://github.com/topoteretes/cognee) | 31,298 | 2026-10-01 | Apache-2.0 | 仅元数据 |
| [totec448-spec/chat-on-steroids](https://github.com/totec448-spec/chat-on-steroids) | 4,231 | 2026-10-02 | MIT | 仅元数据 |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7,333 | 2026-09-28 | CC-BY-SA-4.0 | 重点选读 |
| [triggerdotdev/trigger.dev](https://github.com/triggerdotdev/trigger.dev) | 16,455 | 2026-10-02 | Apache-2.0 | 仅元数据 |
| [trycua/cua](https://github.com/trycua/cua) | 27,720 | 2026-10-02 | MIT | 仅元数据 |
| [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | 2,911 | 2026-10-02 | MIT | 重点选读 |
| [uphiago/recon-skills](https://github.com/uphiago/recon-skills) | 1,285 | 2026-09-01 | MIT | 仅元数据 |
| [vercel/workflow](https://github.com/vercel/workflow) | 2,444 | 2026-10-01 | Apache-2.0 | 仅元数据 |
| [vmoranv/jshookmcp](https://github.com/vmoranv/jshookmcp) | 2,019 | 2026-09-28 | AGPL-3.0 | 重点选读 |
| [volcengine/OpenViking](https://github.com/volcengine/OpenViking) | 39,118 | 2026-10-02 | AGPL-3.0 | 重点选读 |
| [wasmerio/wasmer](https://github.com/wasmerio/wasmer) | 21,112 | 2026-10-01 | MIT | 仅元数据 |
| [Xnhyacinth/Awesome-LLM-Long-Context-Modeling](https://github.com/Xnhyacinth/Awesome-LLM-Long-Context-Modeling) | 2,175 | 2026-08-17 | MIT | 仅元数据 |
| [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill) | 39,290 | 2026-09-22 | MIT | 重点选读 |
| [zhizhuodemao/js-reverse-mcp](https://github.com/zhizhuodemao/js-reverse-mcp) | 2,870 | 2026-09-03 | Apache-2.0 | 仅元数据 |
| [zinja-coder/jadx-mcp-server](https://github.com/zinja-coder/jadx-mcp-server) | 791 | 2026-09-23 | Apache-2.0 | 仅元数据 |

## 本次落地及不作的承诺

已新增 12 类组件索引、按事件选择的组合入口，以及写入既有事件表的节点复盘。DSH route 通过组合入口取当前方法和能力；resume 恢复有证据的节点，证据变更会标记。主入口只指导当前动作，详细宿主参数按需读取。验证结果见 [本轮验证](composition-validation-2026-10-02.md)。

没有安装任何上游服务、模型或新生产依赖；没有将检索结果和项目自报成绩写成本包能力。跨模型盲测、Kali/Pi/OpenCode 宿主验证、深度收益调度、完整路径图、防守遥测与清理复测仍需后续实现和实际验收。

后续选型固定比较当前方案与候选方案在同模型/同工具/同预算下的结论正确性、误报、有效试验成本、重复率、压缩续接和完整交付；同一项目内部的运行模式应分开比较。默认按需召回前三条以内方法经验，不把整个调查目录注入任务。
