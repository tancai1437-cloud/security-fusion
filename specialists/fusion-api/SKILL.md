---
name: fusion-api
description: 评估REST、GraphQL等接口的身份、会话、对象/功能/租户边界及数据字段控制；使用指定测试身份与可复查对照。
---

**API与身份权限**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：接口集合；测试身份及角色/租户关系；预期允许和拒绝的行为。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**起手动作。** 用一条真实正常请求核对当前身份与业务处理，不先填全量矩阵。缺身份只阻塞依赖项；格式报错不能替代权限验证。

| 当前证据 | 本次具体动作与工具 | 分支 |
|---|---|---|
| 接口文档或已捕获请求 | 从 Burp/浏览器历史取一条原始请求与响应，核对方法、字段、实际操作 | `api.operation` → `api-contract` |
| 测试身份已提供，尚未确认有效 | 用实际 HTTP 请求接口重放已知正常请求，核对当前用户/租户及资源归属 | `identity.available` + request_ref → `identity-baseline` |
| 身份与受控对象已确认 | 同一操作分别保留允许与应拒绝对照，比较实际对象内容/服务端状态 | `api.object` + `identity.verified` + `objects.controlled` → `object-boundary` |
| 已观察角色受限操作 | 用两个已验证角色对同一真实操作做允许/拒绝对照；核对服务端结果 | `api.role-operation` → `function-boundary` |
| 实际密码恢复流程 | 对受控账号核对恢复凭证与账号/阶段的绑定；用最终账号状态判断 | `auth.password-reset` → `reset-binding` |
| 请求依赖前端签名或序列化 | 沿请求发起位置读取相关源码；只在静态资料不足时运行采样 | 转 JS，带原请求引用；不重新侦察 |

对照只改变一个条件；200、空列表、参数报错不单独代表允许或拒绝。排除缓存、过期会话和统一成功包装。

业务分支前提见 [业务检查](../../references/business-checks.md)。恢复可未登录但须控制账号；角色检查须双方身份有效。先执行当前一项，不凑假设数量，历史案例不充当目标证据。

保存身份引用、对象归属、输入、原始返回和实际状态，按业务规则判断。接口文档与字段存在只是线索；有源码时转 fusion-code 核对服务端控制路径。

**补覆盖。** 列表、详情、导出、分享、修改按实际存在的动作分别核对，不能相互继承结果。匿名基线不覆盖登录后检查；细化时读 [对象与权限关系](../../references/field-methods.md#api)。

执行路由：`http.history`、`http.request`、`browser.observe`、`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`identity-matrix.json`、`api-checks.json`、`candidate-evidence.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：已选身份和接口边界有可追溯对照，未验证结论保留明确缺口。

宿主有 fusion 时继续 execute，以 review 提交上一回执的实际结论；阶段暂停用 checkpoint，交付用 finish。没有宿主组件才用 [advance](../../references/observation-routing.md#简化入口advance)。保存阴性、反证和阻塞；只在阶段结束整理产物，不等用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S27 [elementalsouls/Claude-BugHunter · skills/hunt-api-misconfig/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-api-misconfig/SKILL.md)
- S23 [elementalsouls/Claude-BugHunter · skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)
- S05 [PortSwigger/mcp-server · src/main/kotlin/net/portswigger/mcp/tools/Tools.kt](https://github.com/PortSwigger/mcp-server/blob/HEAD/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
