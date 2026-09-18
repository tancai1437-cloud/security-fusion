---
name: fusion-api
description: 评估REST、GraphQL等接口的身份、会话、对象/功能/租户边界及数据字段控制；使用指定测试身份与可复查对照。
---

**API与身份权限**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：接口集合；测试身份及角色/租户关系；预期允许和拒绝的行为。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先确认每个测试身份实际生效及角色，再建立身份×对象×动作矩阵；账号无效则记录受阻，不能得出无权限问题。
2. 围绕同一个接口和资源设置正常与拒绝对照，保留身份引用、输入、返回和服务端业务状态。
3. 认证检查使用可被解析的正常请求；参数校验错误不能证明认证已经通过。
4. 接口文档、字段存在或不同状态码只作为线索；确认对象归属、敏感字段控制与跨角色结果是否违背业务规则。
5. 出现签名/前端序列化依赖提交fusion-js；有源码时提交fusion-code以补控制路径。

执行路由：`http.history`、`http.request`、`browser.observe`、`code.inspect`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 执行 fusion.py catalog --capability <id> 按需选择工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

输出：`identity-matrix.json`、`api-checks.json`、`candidate-evidence.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：已选身份和接口边界有可追溯对照，未验证结论保留明确缺口。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S27 [elementalsouls/Claude-BugHunter · skills/hunt-api-misconfig/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-api-misconfig/SKILL.md)
- S23 [elementalsouls/Claude-BugHunter · skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)
- S05 [PortSwigger/mcp-server · src/main/kotlin/net/portswigger/mcp/tools/Tools.kt](https://github.com/PortSwigger/mcp-server/blob/HEAD/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
