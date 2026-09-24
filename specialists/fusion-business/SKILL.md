---
name: fusion-business
description: 评估订单、额度、审批、邀请等业务流程中的状态转换、次数限制与服务端一致性；先定义业务不变量和可控测试数据。
---

**业务流程与状态**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：流程图或可观察正常流程；业务规则、测试身份和测试数据。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**起手动作。** 从已有请求和状态选一个要回答的问题；只画当前转换，不先整理完整流程。用当前 HTTP 工具取得对照与前后状态，结果明确后继续下一项。

| 当前证据 | 具体动作 | 分支 |
|---|---|---|
| 只有订单/额度/流程入口 | 从正常流程确认当前状态、规则和请求 | `business.order/quota/workflow` → `business-transition` |
| 已定位一条有前置条件的转换 | 在受控数据上比较正常转换与缺前提的转换，读取最终状态 | `business.transition` → `order-transition` |
| 实际操作具有一次性或幂等规则 | 一次正常提交、一次获准顺序重放，核对服务端实际效果数 | `business.single-use` → `single-use-effect` |

后两项需要有效身份、可恢复测试数据和本次操作范围；缺项会返回具体阻塞，不能退回泛化方法继续写操作。前提和输入引用见 [业务检查](../../references/business-checks.md)。执行卡已返回时直接使用其中步骤，无需再读参考。

1. 从当前正常流程写出一个要核对的金额/数量、所有权、顺序、次数或终态规则。
2. 将界面限制与服务端实际规则分开观察；每次检查围绕一个不变量记录前后状态。
3. 依赖并发、真实支付或不可逆状态的检查按本次任务范围处理；使用可控测试资源，不从抽象异常推导经济影响。
4. 有异常时先复测正常路径与负例，排除过期状态、重复提交提示和测试环境特例。

同一逻辑操作返回两次成功而只产生一次效果可以是正常幂等；一次调用结果未知时先查询状态。顺序重放不代表并发竞态已覆盖。历史案例与当前任务结果分开，阴性只覆盖本次测试条件。

**当前异常优先收口。** 出现可复现的状态异常后，先围绕同一业务对象补齐前提、对照和影响边界，再切换新入口；新线索先落盘。后续检查必须回答新问题，不能仅为提高漏洞等级扩大操作。界面按钮、角色名或请求被接受不能直接证明服务端状态已改变；见 [业务证据](../../references/field-methods.md#business)。

执行路由：`browser.observe`、`http.history`、`http.request`、`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`business-invariants.json`、`state-transition-checks.json`、`business-impact-evidence.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：每个选定不变量有实际对照或清楚的验证前提，影响与证据相称。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S22 [elementalsouls/Claude-BugHunter · skills/hunt-business-logic/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-business-logic/SKILL.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
