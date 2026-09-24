---
name: fusion-cloud
description: 评估任务范围内的云配置、容器镜像和IaC材料，按环境事实选择配置检查与影响核验。
---

**云、容器与配置**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：环境/配置/镜像引用；范围与期望控制。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 区分云账户配置、镜像依赖、IaC和运行集群；按实际材料选Prowler、Trivy、Checkov或kube-bench对应接口。
2. 记录工具版本、配置来源和采集时间，不能将测试配置的结果推广到生产环境。
3. 将规则命中与实际暴露、身份权限、可达路径结合验证；配置建议与确认缺陷分开。
4. 环境缺失时仍可检查提供的静态材料，但覆盖表必须注明运行态未验证。

执行路由：`cloud.posture`、`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`configuration-checks.json`、`cloud-candidates.json`、`environment-limitations.md`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：命中可追溯到具体配置和条件，不能将静态检查完成写成整个云环境已验证。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

**方法来源。**

- S06 [0x4m4/hexstrike-ai · hexstrike_mcp.py](https://github.com/0x4m4/hexstrike-ai/blob/HEAD/hexstrike_mcp.py)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
