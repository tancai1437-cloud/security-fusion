---
name: fusion-web
description: 评估已识别Web入口的输入、文件、客户端策略及服务暴露问题；根据入口类型选择检查方法并形成候选结论。
---

**Web检查面评估**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：入口及基线；适用检查面与身份引用。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**起手动作。** 从已有具体入口选一个输入/输出或文件行为问题，先取得正常请求与响应作为对照；已有证据则直接补缺。每次结果决定是否补对照、否定假设或转到下一入口，不先读完所有 Web 检查方法。

| 现场特征 | 具体方法与首个工具动作 |
|---|---|
| 文本进入实际业务响应 | `input-context`：HTTP 正常请求后用无害标记定位输出位置；保留 request_ref、parameter，确认 `response.business` |
| 上传、下载、分享 | `file-boundary`：用受控文件和已验证身份比较归属/访问结果，记录 identity_refs、object_refs、operation |
| URL 字段或 Webhook | `url-origin`：先查询真实流量区分浏览器跳转、服务器获取与异步处理；有受控回调证据再下结论 |
| 浏览器跨源或缓存 | `browser-boundary`：用当前浏览器和实际身份核对脚本是否读到内容；HTTP 头不能代替浏览器行为 |
| 统一登录壳 / 认证拒绝 | 转请求定位或身份前提；先停止依赖业务响应的输入变体 |

1. 按真实输入点建立检查项：输入/输出、文件上传下载、服务配置和浏览器边界；先核对既有基线，再选工具。
2. 模板扫描用于缩小候选集合，保存模板与原始匹配；后续使用对应请求和对照确认。
3. 响应200、错误页、页面回显或技术栈匹配不能单独确认为漏洞；检查是否只是统一兜底或自有数据展示。
4. 认证/权限问题交给fusion-api；交易状态交给fusion-business；前端调用链问题交给fusion-js，并把工作项返回主控安排。

**现场判定。** 先区分正常业务响应、统一登录 HTML 和鉴权拒绝。已有业务接口被同一身份前提阻挡时，记录受阻并处理独立项，不对同一拒绝响应反复开展下游输入检查。超时、500 和空列表分别核对，不能混成漏洞或无漏洞；具体反例见 [Web 判定](../../references/field-methods.md#web)。不知道下一面选什么时才查 [特征路由](../../references/field-methods.md#features) 的相关行。

执行路由：`http.history`、`http.request`、`web.templates`、`browser.observe`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`web-checks.json：逐项结果与证据`、`candidates.json：待验证问题与缺失条件`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：所有约定适用检查有完成或受阻依据，候选问题已交统一验证。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S09 [elementalsouls/Claude-BugHunter · skills/hunt-dispatch/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-dispatch/SKILL.md)
- S23 [elementalsouls/Claude-BugHunter · skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)
- S05 [PortSwigger/mcp-server · src/main/kotlin/net/portswigger/mcp/tools/Tools.kt](https://github.com/PortSwigger/mcp-server/blob/HEAD/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
