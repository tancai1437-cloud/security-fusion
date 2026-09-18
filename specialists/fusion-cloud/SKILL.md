---
name: fusion-cloud
description: 评估任务范围内的云配置、容器镜像和IaC材料，按环境事实选择配置检查与影响核验。
---

**云、容器与配置**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：环境/配置/镜像引用；范围与期望控制。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 区分云账户配置、镜像依赖、IaC和运行集群；按实际材料选Prowler、Trivy、Checkov或kube-bench对应接口。
2. 记录工具版本、配置来源和采集时间，不能将测试配置的结果推广到生产环境。
3. 将规则命中与实际暴露、身份权限、可达路径结合验证；配置建议与确认缺陷分开。
4. 环境缺失时仍可检查提供的静态材料，但覆盖表必须注明运行态未验证。

执行路由：`cloud.posture`、`code.inspect`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 及 [工具匹配表](../../manifests/execution-routes.json) 选择对应工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。

输出：`configuration-checks.json`、`cloud-candidates.json`、`environment-limitations.md`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：命中可追溯到具体配置和条件，不能将静态检查完成写成整个云环境已验证。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S06 [0x4m4/hexstrike-ai · hexstrike_mcp.py](https://github.com/0x4m4/hexstrike-ai/blob/HEAD/hexstrike_mcp.py)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
