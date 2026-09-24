---
name: fusion-api
description: 评估REST、GraphQL等接口的身份、会话、对象/功能/租户边界及数据字段控制；使用指定测试身份与可复查对照。
---

**API与身份权限**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：接口集合；测试身份及角色/租户关系；预期允许和拒绝的行为。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**起手动作。** 先检查一条真实请求及当前测试身份，确认正常请求能到达业务处理；使用现有对照，不先填写全量身份矩阵。无身份只阻塞需要该身份的检查；不要用参数格式错误替代权限验证。

| 当前证据 | 本次具体动作与工具 | 分支 |
|---|---|---|
| 接口文档或已捕获请求 | 从 Burp/浏览器历史取一条原始请求与响应，核对方法、字段、实际操作 | `api.operation` → `api-contract` |
| 测试身份已提供，尚未确认有效 | 用实际 HTTP 请求接口重放已知正常请求，核对当前用户/租户及资源归属 | `identity.available` + request_ref → `identity-baseline` |
| 身份与受控对象已确认 | 同一操作分别保留允许与应拒绝对照，比较实际对象内容/服务端状态 | `api.object` + `identity.verified` + `objects.controlled` → `object-boundary` |
| 请求依赖前端签名或序列化 | 沿请求发起位置读取相关源码；只在静态资料不足时运行采样 | 转 JS，带原请求引用；不重新侦察 |

受控对照使用实际拥有的 A/B 对象；结果只改变一个条件。200、字段缺失、空列表、参数报错分别解释，不能直接当作允许或拒绝。记录另一种能解释差异的原因并排除它。

1. 先确认每个测试身份实际生效及角色，再建立身份×对象×动作矩阵；账号无效则记录受阻，不能得出无权限问题。
2. 围绕同一个接口和资源设置正常与拒绝对照，保留身份引用、输入、返回和服务端业务状态。
3. 认证检查使用可被解析的正常请求；参数校验错误不能证明认证已经通过。
4. 接口文档、字段存在或不同状态码只作为线索；确认对象归属、敏感字段控制与跨角色结果是否违背业务规则。
5. 出现签名/前端序列化依赖提交fusion-js；有源码时提交fusion-code以补控制路径。

**围绕对象补覆盖。** 从一个受控对象梳理实际存在的列表、详情、导出、分享或修改关系，逐项核对身份和服务端控制；请求格式正确、身份生效和拥有对象分别证明。已完成匿名基线不能代表登录后检查已完成；缺身份记受阻。需要细化时读 [对象与权限关系](../../references/field-methods.md#api)。

执行路由：`http.history`、`http.request`、`browser.observe`、`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`identity-matrix.json`、`api-checks.json`、`candidate-evidence.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：已选身份和接口边界有可追溯对照，未验证结论保留明确缺口。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S27 [elementalsouls/Claude-BugHunter · skills/hunt-api-misconfig/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-api-misconfig/SKILL.md)
- S23 [elementalsouls/Claude-BugHunter · skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)
- S05 [PortSwigger/mcp-server · src/main/kotlin/net/portswigger/mcp/tools/Tools.kt](https://github.com/PortSwigger/mcp-server/blob/HEAD/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
