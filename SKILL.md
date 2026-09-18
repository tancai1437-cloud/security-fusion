---
name: security-fusion
description: 编排获准的渗透、SRC、逆向、源码审计、红队路径和AI应用评估，按需路由专项Skill与工具/MCP；用持久化账本查重、恢复长任务并生成证据与报告。
---

**三层入口：主路由 → 专项 Skill 路由 → 执行路由。**

当用户请求完整任务时由本入口持有主控；明确的单点任务可直接加载对应专项。仅方案、解释、调研不进入目标执行。当前主会话完成编排与调用，不创建子代理。

1. 确定目标、有效范围、交付要求和唯一案件路径；沿用本次已有授权。案件数据放在 Skill 安装目录之外。
2. 执行 `python3 <skill-root>/scripts/fusion.py catalog`，再用 `catalog --mission <id>` 取当前任务候选。意图含混时才补读 [主路由](references/main-router.md)；不默认读取全套清单。
3. 新执行任务按 [运行协议](references/runtime.md) 的“建案与计划”初始化；已有任务先 `resume --case <path>`。上下文压缩、重启或切换案件后必须重新恢复；记住路径不能代替读取账本。
4. 选择依赖满足的检查，用 `catalog --skill <id>` 定位并只读当前专项。新增检查前按需查询同目标的既有检查和否定结论，避免改写措辞后重复做；主控保持不变。
5. 专项提出能力后用 `catalog --capability <id>` 查询候选，依据 [执行路由](references/execution-router.md) 匹配当前宿主真实工具。仅取本次所需 schema，不扫描、合并其他 Agent 的配置。
6. 本地命令走 `run`；原生 MCP 走 `begin → 宿主调用 → record`。只在 decision=execute 时发起对应动作；reuse 复用结果，hold 先处理依赖或待核对调用。结果未知不盲目重发。
7. 原始输出存文件，模型只读必要片段。证据充分才 `review --verdict done`；失败、阴性结果、被否定假设和简明决策用 `note` 保存。文件落盘并不等于模型每轮要读取它。
8. 持续调度其他适用检查。由 fusion-validate 复核候选；阶段结束/交付时运行 `report` 生成账本覆盖，再由 fusion-report 完成业务总结与技术报告。零确认发现和部分完成也要交付。

默认上下文包上限 6,000 字符；省略项有计数，按需分页查询。目标、范围、约束、当前检查和相关记录放不下时明确报错，不能静默裁掉；不把字符数当 token 数。不要反复加载完整历史、全部专项或全部 MCP schema。

Python >= 3.9，标准库运行辅助程序；MCP 调用仍由宿主提供。未通过本协议的直接调用无法由 Skill 拦截，远端动作不能保证 exactly-once。账本状态及证据规则见 [证据契约](references/evidence-contract.md)，命令与故障处理见 [运行协议](references/runtime.md)。

来源与取舍见 [融合决策](references/upstream-decisions.md)，具体文件指纹见 [来源锁定](sources.lock.json)。
