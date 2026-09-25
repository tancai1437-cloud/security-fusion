---
name: fusion-recon
description: 识别获准目标的资产、服务、入口与技术栈，建立后续评估所需清单；适用于完整渗透或SRC任务的初始观察。
---

**资产与入口侦察**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：目标集合与范围；已有资产/流量/技术材料。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**起手动作。** 用户已给 URL 时，先用已有工具读取该入口或已有流量，保留状态、跳转和业务入口证据；已有基线直接补缺。此项不以安装 HexStrike、域名测绘或生成完整资产清单为前提。根据观察到的页面/API/身份条件再安排下一项。

| 实际观察 | 现在做什么 / 选什么工具 | 下一方法 |
|---|---|---|
| 有页面，未知业务入口 | 读取当前页面链接/表单及实际网络请求；已有浏览器用观察接口，静态材料用本地检索 | 实际 API → `api.operation`；相关脚本 → `js.bundle` |
| 不同路径返回同一登录 HTML | 从已有流量和入口脚本定位真实请求，不继续批量猜路径 | `http.login-shell` → JS 的请求定位 |
| 真实 API 返回，身份未知 | 从历史请求核对方法、字段和认证位置，不凭 URL 猜功能 | `api.operation` → API 请求梳理 |
| 只有跳转、拒绝或工具报错 | 分别核对新目标范围、身份前提、工具连接；独立可用入口继续 | 没有新证据不创建下游输入检查 |

1. 先复用已有入口与流量，新增侦察按信息缺口选择。先记录每个主机与重要路径层级的正常响应、不存在资源响应以及重定向基线。
2. 指纹按资产保存，不能将一个主机的框架推广到所有资产；技术栈信号决定后续专项。
3. 域名、服务、URL、接口分别去重，保留每条发现的来源与身份条件。新资产与范围比对后才进入执行清单。
4. 发现登录/API/上传/业务状态/源码/移动端线索时，向主控提交适用性事实；不自行切换整项任务。

**现场推进。** 先处理当前业务面中能取得有效证据的未完成项，再扩大采集；响应里的新接口、对象和地址带来源记入案件，核对范围和绑定后排队。去重保留路径、方法、身份和参数差异；同类页面的采样不能把其他实例直接记成 done。只有这些情况需要细化时才读 [入口与去重](../../references/field-methods.md#recon)。

执行路由：`asset.domains`、`service.inventory`、`web.crawl`、`browser.observe`、`http.history`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`assets.json：资产、入口、来源与范围`、`baselines.json：基线和采样边界`、`surface-facts.json：触发后续专项的事实`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：本次约定资产和入口已记录，未知或受阻项可定位；侦察完成不代表渗透完成。

宿主有 fusion 时继续 execute，以 review 提交上一回执的实际结论；阶段暂停用 checkpoint，交付用 finish。没有宿主组件才用 [advance](../../references/observation-routing.md#简化入口advance)。保存阴性、反证和阻塞；只在阶段结束整理产物，不等用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S09 [elementalsouls/Claude-BugHunter · skills/hunt-dispatch/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-dispatch/SKILL.md)
- S06 [0x4m4/hexstrike-ai · hexstrike_mcp.py](https://github.com/0x4m4/hexstrike-ai/blob/HEAD/hexstrike_mcp.py)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
