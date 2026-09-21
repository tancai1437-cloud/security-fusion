---
name: fusion-web
description: 评估已识别Web入口的输入、文件、客户端策略及服务暴露问题；根据入口类型选择检查方法并形成候选结论。
---

**Web检查面评估**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：入口及基线；适用检查面与身份引用。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**起手动作。** 从已有具体入口选一个输入/输出或文件行为问题，先取得正常请求与响应作为对照；已有证据则直接补缺。每次结果决定是否补对照、否定假设或转到下一入口，不先读完所有 Web 检查方法。

1. 按真实输入点建立检查项：输入/输出、文件上传下载、服务配置和浏览器边界；先核对既有基线，再选工具。
2. 模板扫描用于缩小候选集合，保存模板与原始匹配；后续使用对应请求和对照确认。
3. 响应200、错误页、页面回显或技术栈匹配不能单独确认为漏洞；检查是否只是统一兜底或自有数据展示。
4. 认证/权限问题交给fusion-api；交易状态交给fusion-business；前端调用链问题交给fusion-js，并把工作项返回主控安排。

执行路由：`http.history`、`http.request`、`web.templates`、`browser.observe`、`evidence.persist`。已有本地工具直接 start/run；需要 MCP 且工具选择不明确时，按 [执行路由规则](../../references/execution-router.md) 只查当前能力。能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`web-checks.json：逐项结果与证据`、`candidates.json：待验证问题与缺失条件`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：所有约定适用检查有完成或受阻依据，候选问题已交统一验证。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S09 [elementalsouls/Claude-BugHunter · skills/hunt-dispatch/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-dispatch/SKILL.md)
- S23 [elementalsouls/Claude-BugHunter · skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)
- S05 [PortSwigger/mcp-server · src/main/kotlin/net/portswigger/mcp/tools/Tools.kt](https://github.com/PortSwigger/mcp-server/blob/HEAD/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
