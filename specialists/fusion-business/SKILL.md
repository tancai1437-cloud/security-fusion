---
name: fusion-business
description: 评估订单、额度、审批、邀请等业务流程中的状态转换、次数限制与服务端一致性；先定义业务不变量和可控测试数据。
---

**业务流程与状态**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：流程图或可观察正常流程；业务规则、测试身份和测试数据。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 从正常业务流程建立状态图，写出金额/数量、所有权、顺序、次数和终态等必须成立的规则。
2. 将界面限制与服务端实际规则分开观察；每次检查围绕一个不变量记录前后状态。
3. 依赖并发、真实支付或不可逆状态的检查按本次任务范围处理；使用可控测试资源，不从抽象异常推导经济影响。
4. 有异常时先复测正常路径与负例，排除过期状态、重复提交提示和测试环境特例。

执行路由：`browser.observe`、`http.history`、`http.request`、`code.inspect`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 及 [工具匹配表](../../manifests/execution-routes.json) 选择对应工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。

输出：`business-invariants.json`、`state-transition-checks.json`、`business-impact-evidence.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：每个选定不变量有实际对照或清楚的验证前提，影响与证据相称。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S22 [elementalsouls/Claude-BugHunter · skills/hunt-business-logic/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-business-logic/SKILL.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
