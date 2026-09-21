---
name: security-fusion
description: 执行获准的渗透、SRC、逆向、源码审计、红队路径和 AI 应用评估；按现场证据路由专项与 MCP/本地工具，保存检查结果、恢复进度并交付报告。
---

**主路由 → 专项 Skill → 执行工具，由当前主会话完成。** 不创建子代理。方案、解释和调研只分析资料；实际任务要取得目标证据，安装和记账本身不算测试进展。

**先完成一个具体检查，再按结果展开。** 有目标、范围和现成工具时，起手选一个能回答实际问题的检查；不先编写全量计划、读取所有协议或盘点全部 MCP。已有材料足够时直接验证问题，不重复侦察。范围或身份缺失仅阻塞依赖它的检查。

**直接选当前专项。** 渗透/SRC → `pentest`/`src`，已有入口从 [recon](specialists/fusion-recon/SKILL.md) 获取基线；已知 Web 问题直接 [web](specialists/fusion-web/SKILL.md)，接口/权限走 [api](specialists/fusion-api/SKILL.md)，交易流程走 [business](specialists/fusion-business/SKILL.md)。源码审计 → `audit` + [code](specialists/fusion-code/SKILL.md)；逆向 → `reverse`，按样本选 [JS](specialists/fusion-js/SKILL.md)、[移动端](specialists/fusion-mobile/SKILL.md) 或 [二进制](specialists/fusion-binary/SKILL.md)；AI 评估 → `ai-assessment` + [ai](specialists/fusion-ai/SKILL.md)。云/容器、网络身份、约定红队路径等不明确时才 `catalog --mission <id>` 查候选；完整映射见 [主路由](references/main-router.md)，无需逐层遍历 catalog。

**新任务只读当前专项和 [快速执行](references/first-action.md)。** 生成一个任务 JSON，`fusion.py start` 一次完成注册库复用/创建、建案、会话绑定和首项登记；追加 `-- <真实命令及参数>` 可在同次调用执行本地检查并捕获输出。不要以健康检查、打印示例字符串或建目录冒充目标证据。后续检查按新事实增量 plan，不把所有专项预先登记为待办。完整任务持续覆盖已识别的适用面；首项成功不算任务完成，交付时逐项说明已测、未测、受阻和不适用的依据。

**按眼前问题准备工具。** 已有本地命令、文件或检索能力可直接走 `run`，无需先为宿主能力生成 MCP 验收收据。有可用 MCP 时按 [执行路由](references/execution-router.md) 只查所需能力；确有缺项才进入 [环境补齐](references/environment-bootstrap.md)。需要接入的 MCP 仍须真实验收后入索引，未知名称与静态候选不能当成已接通。补齐某个提供者不阻塞现成工具能完成的独立检查。用户明确要求安装/初始化时按环境流程完成，不受“先做目标检查”的顺序约束。

**每个检查形成短循环：实际调用 → 读必要证据 → 判断结果 → 选择下一项。** 本地走 `run`；MCP 先核对真实目标/身份并登记共享上下文，再 `begin → 宿主调用 → record`。仅 `decision=execute` 才调用；`reuse` 复用，`hold` 核对未决结果。退出码 0 仅进入 review，核对完成条件后才 `review --verdict done`。阴性、反例和阻塞同样记录。正在取得有效证据时不为重写计划中断；连续两次只做 catalog/plan/读规则且没有消除具体阻塞时，回到当前检查执行，或给出真实阻塞并处理独立项，不继续扩写准备材料。

**隔离与恢复。** 所有执行命令显式携带 `--workspace / --session / --case`；目标和案件不可凭最近使用选择。已有案件、压缩或重启后 `resume`，不要再次初始化；换会话用 handoff。具体操作按需读 [运行协议](references/runtime.md) 和 [隔离协议](references/scoped-memory.md)。这些程序协调可信 Agent 的记录和共享上下文，不能拦截绕过 CLI 的调用。

**交付与经验。** 当前检查的记录足以续跑，不逐步重写全套报告；阶段结束导出 `report`，必要时加载 [validate](specialists/fusion-validate/SKILL.md) 和 [report](specialists/fusion-report/SKILL.md) 复核结论与覆盖。原始输出落盘，默认只返回最多 6,000 字符的恢复包；按需查具体证据。经验检索用于当前方法受阻或确需历史经验时，提炼与审核放在阶段结束，不作为首个工具调用的前置条件。零发现、部分完成也按实际结果交付。

Python >= 3.9，辅助程序只用标准库。MCP 调用由宿主提供；字段与证据要求见 [证据契约](references/evidence-contract.md)。来源与取舍见 [融合决策](references/upstream-decisions.md)，不需要为执行任务重读来源清单。
