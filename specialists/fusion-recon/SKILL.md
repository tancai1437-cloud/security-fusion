---
name: fusion-recon
description: 识别获准目标的资产、服务、入口与技术栈，建立后续评估所需清单；适用于完整渗透或SRC任务的初始观察。
---

**资产与入口侦察**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：目标集合与范围；已有资产/流量/技术材料。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**起手动作。** 用户已给 URL 时，先用已有工具读取该入口或已有流量，保留状态、跳转和业务入口证据；已有基线直接补缺。此项不以安装 HexStrike、域名测绘或生成完整资产清单为前提。根据观察到的页面/API/身份条件再安排下一项。

1. 先复用已有入口与流量，新增侦察按信息缺口选择。先记录每个主机与重要路径层级的正常响应、不存在资源响应以及重定向基线。
2. 指纹按资产保存，不能将一个主机的框架推广到所有资产；技术栈信号决定后续专项。
3. 域名、服务、URL、接口分别去重，保留每条发现的来源与身份条件。新资产与范围比对后才进入执行清单。
4. 发现登录/API/上传/业务状态/源码/移动端线索时，向主控提交适用性事实；不自行切换整项任务。

执行路由：`asset.domains`、`service.inventory`、`web.crawl`、`browser.observe`、`http.history`、`evidence.persist`。已有本地工具直接 start/run；需要 MCP 且工具选择不明确时，按 [执行路由规则](../../references/execution-router.md) 只查当前能力。能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`assets.json：资产、入口、来源与范围`、`baselines.json：基线和采样边界`、`surface-facts.json：触发后续专项的事实`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：本次约定资产和入口已记录，未知或受阻项可定位；侦察完成不代表渗透完成。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S09 [elementalsouls/Claude-BugHunter · skills/hunt-dispatch/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-dispatch/SKILL.md)
- S06 [0x4m4/hexstrike-ai · hexstrike_mcp.py](https://github.com/0x4m4/hexstrike-ai/blob/HEAD/hexstrike_mcp.py)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
