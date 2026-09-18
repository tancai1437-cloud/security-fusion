# Security Fusion

将安全任务组织成三层：**主路由 → 专项 Skill 路由 → 执行路由（MCP / 本地工具）**。

一个主入口包含 6 类任务、13 个专项和 18 类执行能力映射。Agent 根据任务材料安排适用检查，保存证据、覆盖记录、报告和续跑信息。

## 在 Kali / Linux 上一条命令安装

需要 Node.js >= 22.20.0、npm，以及能访问 GitHub 的网络。在终端运行：

```bash
npx --yes skills@1.7.0 add tancai1437-cloud/security-fusion --skill security-fusion --agent universal --global --copy --yes
```

这是**用户级安装**，不依赖终端当前目录，也不需要 sudo。安装器下载整个技能包；主入口及其 13 个专项一起保留在 `~/.agents/skills/security-fusion/`。升级会替换同名安装副本，定制内容应保存在自己的源仓库。

安装使用 [Skills CLI](https://github.com/vercel-labs/skills)。先查看远程技能而不安装，可以运行：

```bash
npx --yes skills@1.7.0 add tancai1437-cloud/security-fusion --list
```

## Agent 接入

| Agent | 如何加载 | MCP 接入 |
|---|---|---|
| [DSH / DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) | 启用 Skill 组件，读取用户级 `.agents/skills/` | 使用 [官方 MCP 客户端](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md) |
| [Pi](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md) | 原生 Skill 支持，可读取用户级 `.agents/skills/` | 核心未内置 MCP，可使用 [pi-mcp-adapter](https://github.com/nicobailon/pi-mcp-adapter) |
| [OpenCode](https://opencode.ai/docs/skills/) | 原生 Skill 支持，可读取用户级 `.agents/skills/` | 配置 [本地或远程 MCP 服务](https://opencode.ai/docs/mcp-servers/) |

安装后在 Agent 中发起新会话，明确说“使用 security-fusion”。如果没有出现在技能列表，让 Agent 读取 `~/.agents/skills/security-fusion/SKILL.md`，核对当前 Agent 的发现配置。专项文件由主入口按需读取，不要求全部单独登记。

## 提交任务

替换下面的示例目标和范围：

```text
使用 security-fusion。

任务：对我的本地靶场做 Web/API 安全评估。
目标：http://127.0.0.1:3000
范围：仅该服务以及我提供的测试账号。
输出目录：work/lab-001。

先核对可用工具和 MCP，再自动选择专项、编排适用检查并执行。
持续保存动作、结果和原始证据。
交付总结、报告、覆盖清单和续跑记录。
缺工具的项目记录阻塞原因，继续其他可执行项。
```

后续继续：

```text
使用 security-fusion，继续 work/lab-001。
先读取 resume.md、state.json 和已有证据，再处理未完成项。
```

## 三层如何衔接

1. [主路由](references/main-router.md)识别渗透、SRC、逆向、源码审计、红队路径或 AI 应用评估，维护范围、计划、工作项与进度。
2. [专项路由](manifests/specialists.json)按实际材料选择 recon、web、api、business、js、code、mobile、binary、cloud、infra、ai、validate、report。
3. [执行路由](references/execution-router.md)根据[能力映射](manifests/execution-routes.json)，匹配当前 Agent 真实暴露的 MCP / 本地工具，核对调用结果并将证据交回专项。

所有层由当前主会话顺序协调。新线索可以扩展适用检查，单项受阻时继续其余可执行项。

## 产物

[证据契约](references/evidence-contract.md)约定每项任务使用独立目录：

```text
work/<case>/
  scope.md
  plan.json
  events.jsonl
  state.json
  timeline.md
  workitems.md
  evidence/
  specialists/
  report/
    summary.md
    report.md
    findings.json
    coverage.md
  resume.md
  learning/candidates.md
```

没有确认发现、部分完成或工具失败时仍生成对应状态的报告。原始证据、候选问题和已验证结论分别记录。

## 当前交付范围

本仓库提供 Agent 可读取的技能指令、路由数据、输出契约与结构校验脚本。MCP 调用使用宿主已经接入的服务；安装此包不自动安装 MCP 服务、分析软件、账号凭证或系统依赖。

已完成 Skill 格式、文件引用、路由映射和示例依赖检查；曾在 Windows 隔离目录验证标准安装器能完整复制技能包。Kali 上的 Agent 行为与真实 MCP 联调尚未验证，结构检查不代表这些任务已经执行成功。

维护时可运行（Python >= 3.9）：

```bash
python3 scripts/validate_pack.py
```

结构结果见 [validation-results.json](validation-results.json)，格式结果见 [skill-format-validation.json](skill-format-validation.json)。

## 来源

提炼来源与改编决定见[融合决策](references/upstream-decisions.md)、[33 个上游文件指纹](sources.lock.json)和[第三方署名及许可说明](THIRD_PARTY_NOTICES.md)。上游 MCP 实现保持外部依赖，本仓库没有捆绑这些服务的软件代码。
