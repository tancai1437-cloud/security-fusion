# Security Fusion

将安全任务组织成三层：**主路由 → 专项 Skill 路由 → 执行路由（MCP / 本地工具）**。

一个主入口包含 6 类任务、13 个专项和 22 类执行能力映射。Agent 根据任务材料安排适用检查，保存证据、覆盖记录、报告和续跑信息。

当前入口按现场材料直接进入一个专项，recon / Web / API / JS 给出具体动作与工具选择。`advance` 合并证据复核与下一方法选择，自动带入当前检查的目标、版本和证据引用；显式目标 stdio MCP 可用 `mcp-run` 真正连接并调用工具，一次完成登记和结果落盘。详见 [下一步](references/observation-routing.md#简化入口advance) 与 [MCP 执行](references/mcp-execution.md)。

本次升级增加 Python 标准库运行辅助程序：SQLite 案件账本、执行前查重、中断恢复、证据校验、按需查询及报告导出。三层路由保持不变。

现在还包括会话/案件绑定、共享工具上下文占用、经验候选与版本审核，以及本地 BM25 和可选向量混合检索。不同目标分别维护案件，同项目可复用经过审核的方法。

[基础能力改造](references/foundations.md)进一步让 DSH 写入与交付归属独立案件、保存产物版本、按证据 ID 小段读取；恢复先带回前置结果、替换旧恢复块，并自动召回已审核方法。目标验收关联实际回执，未满足条件不会仅凭“报告已生成”完成。已有账本兼容，无新增依赖或数据库迁移。

[本次验证](references/foundations-validation-2026-09-26.md)：150 项本地测试，147 通过、3 跳过；真实 DSH 两轮任务在压缩后复用原证据完成限定交付，全程一次目标请求。保留前两轮失败与修复记录，不将此推断为所有复杂任务均已可靠。

实际任务先用已有工具完成一个具体检查，再按结果扩展；start 命令合并建案、绑定、首项登记和可选本地执行。当前检查确实缺少 MCP 能力时才检测、补齐并验收该能力；显式安装/初始化仍按完整环境流程执行。验证通过的 MCP 能力进入私有索引。

Web/SRC 方法进一步吸收了用户提供工作流包的思路：按业务特征选择专项、优先完成当前业务面的检查、从响应提取线索、用对照识别假阳性，并只沉淀有新增价值的经验。关键决策直接融入对应专项，[现场方法](references/field-methods.md) 仅按需补读；来源和取舍见 [融合记录](references/upstream-decisions.md#src-field-methods)。

业务方法现增加角色权限、密码恢复绑定、订单转换和一次性效果四个事实分支，接到现有工具执行链；已有对象权限方法继续复用。参考 WooYun Legacy 的业务组织思路，按本包协议编写短执行卡，没有打包历史案例库或增加全量加载。前提与输入见 [业务检查](references/business-checks.md)，来源和许可取舍见 [融合记录](references/upstream-decisions.md#wooyun-methods)。

## 在 Kali / Linux 上一条命令安装

安装需要 Node.js >= 22.20.0、npm 和 GitHub 网络；执行运行辅助程序需要 Python >= 3.9。在目标 Kali / Linux 的终端运行（已安装时同一命令可更新）：

```bash
npx --yes skills@1.7.0 add tancai1437-cloud/security-fusion --skill security-fusion --agent universal --global --copy --yes
```

这是**用户级安装**，不依赖终端当前目录，也不需要 sudo。安装器下载整个技能包；主入口及其 13 个专项一起保留在 `~/.agents/skills/security-fusion/`。升级会替换同名安装副本，定制内容应保存在自己的源仓库。

安装使用 [Skills CLI](https://github.com/vercel-labs/skills)。先查看远程技能而不安装，可以运行：

```bash
npx --yes skills@1.7.0 add tancai1437-cloud/security-fusion --list
```

## Agent 接入

需要持续执行约束的 DSH 使用 [宿主组件](references/host-adapter.md)：注册原生 `fusion` 工具，激活后将实际工具调用约束到 execute，自动捕获回执；压缩后从磁盘恢复，交付前检查未决工作与报告证据。安装 Skill 后还需让当前 Agent 识别其实际 profile，运行包内安装器并重启该 profile。只复制 Skill 文件没有这些 hook。`AGENTS.md` 只需保留入口约定，不要复制全部方法。组件不能替模型保证测试覆盖或结论正确。

[本轮实测](references/agent-execution-validation-2026-09-25.md)：Web 首次目标请求由 186 秒降至 34 秒，压缩后形成报告；同模型 JS 任务仍因输出上限而未交付，不能视为全部通过。

| Agent | 如何加载 | MCP 接入 |
|---|---|---|
| [DSH / DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) | 启用 Skill 组件，读取用户级 `.agents/skills/` | 使用 [官方 MCP 客户端](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md) |
| [Pi](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md) | 原生 Skill 支持，可读取用户级 `.agents/skills/` | 核心未内置 MCP，可使用 [pi-mcp-adapter](https://github.com/nicobailon/pi-mcp-adapter) |
| [OpenCode](https://opencode.ai/docs/skills/) | 原生 Skill 支持，可读取用户级 `.agents/skills/` | 配置 [本地或远程 MCP 服务](https://opencode.ai/docs/mcp-servers/) |

安装后在 Agent 中发起新会话，明确说“使用 security-fusion”。如果没有出现在技能列表，让 Agent 读取 `~/.agents/skills/security-fusion/SKILL.md`，核对当前 Agent 的发现配置。专项文件由主入口按需读取，不要求全部单独登记。

首次也可以直接说：

```text
使用 security-fusion，初始化当前机器的运行环境。
如果当前是 DSH，先识别实际使用的 profile，运行 scripts/install_dsh_adapter.py 安装或更新宿主组件。
需要重启时保存续跑位置；重启后验收原生 fusion.execute，不能把配置写入当成运行接通。
自动检测已有工具和 MCP，复用可用安装，补齐当前所需依赖，接入当前 Agent。
通过实际调用验收后建立能力索引，交付可用项、阻塞项及证据位置。
```

普通 `skills add` 是文件安装器，不会自动运行包内脚本；让 Agent 执行安装或显式初始化时，它应继续完成环境接入；直接执行任务时只补齐当前检查缺少的能力，已有本地工具可先执行。无需用户手写 MCP 配置，完整流程见 [环境初始化](references/environment-bootstrap.md)。实际下载、软件安装、配置合并及调用由目标机 Agent 执行；本包的脚本负责检测、生成配置、验证收据和维护索引。

## 提交任务

替换下面的示例目标和范围：

```text
使用 security-fusion。

任务：对我的本地靶场做 Web/API 安全评估。
目标：http://127.0.0.1:3000
范围：仅该服务以及我提供的测试账号。
输出目录：work/lab-001。

先选当前适用专项和具体检查，使用已有本地工具执行，或复用当前已验收的 MCP。只有检查所需能力缺失时才补齐；不先盘点全部工具或生成全量计划。见 [快速执行](references/first-action.md)。
持续保存动作、结果和原始证据。
交付总结、报告、覆盖清单和续跑记录。
缺工具先自动补齐；确实缺账号、许可证或必要权限的项目记录阻塞，继续其他可执行项。
```

后续继续：

```text
使用 security-fusion，继续 work/lab-001。
先核对 work/lab-001 的案件 ID、注册库与当前会话绑定，再运行带完整绑定参数的 resume。
按当前检查查询相关证据与旧结论，再处理未完成项；待核对调用不要直接重发。
```

## 三层如何衔接

HTTP 新任务支持 `entry` 起手：自动选择侦察方法、能力和现有 curl，只读获取第一份响应。复核后使用 [事实路由](references/observation-routing.md)，由已观察特征与前提选择具体检查，直接登记并匹配工具；当前提供 27 个方法分支。缺身份、统一登录壳、受控对象不足、已测/未决检查分别处理，不要求 Agent 逐层猜 ID。这里的自动路由基于 Agent 提取的结构化事实，并非独立理解网页或保证全部攻击面覆盖。

本地二进制也支持绝对文件 `entry`：自动计算样本版本并执行只读 PE/ELF/CLR 分流；新增 XFF 三组请求、.NET 类型定位、崩溃分类和复现方法。用法与边界见 [二进制专精](references/binary-depth.md) / [代理信任](references/proxy-trust.md)。

`catalog --skill`、`start`、`plan`、`resume` 会直接返回当前专项的实际方法、完成条件与产物路径；方法从专项原文生成，只加载当前一项。持续执行的 `run/begin` 返回专项→能力→实际工具回执，避免每步重新阅读整套文档。压缩恢复优先处理原有未决/待复核结果，不先跳到新待办。

阶段 `report` 另输出 `report/delivery.json`，显示已登记工具调用和缺失专项产物。`ledger_status=completed` 只代表登记检查完成；`status=partial/review_required` 不替 Agent 宣称整个任务完成。DSH 的[宿主组件](references/host-adapter.md)现提供统一 execute、真实调用回执、绕过拦截、交付检查和有限结束纠正；纯文本 Skill 没有这些能力。验收仍看真实目标证据、对照和结果正确性，不能只看“读了哪些文件”。

1. [主路由](references/main-router.md)识别渗透、SRC、逆向、源码审计、红队路径或 AI 应用评估，维护范围、计划、工作项与进度。
2. [专项路由](manifests/specialists.json)按实际材料选择 recon、web、api、business、js、code、mobile、binary、cloud、infra、ai、validate、report。
3. [执行路由](references/execution-router.md)根据[能力映射](manifests/execution-routes.json)，直接使用已有本地工具，或从经当前宿主验收的索引匹配当前所需 MCP；缺项按需补齐，核对结果并将证据交回专项。

所有层由当前主会话顺序协调。新线索可以扩展适用检查，单项受阻时继续其余可执行项。

## 长任务与上下文成本

| 问题 | 实际处理 |
|---|---|
| 上下文压缩或会话重启 | 恢复当前专项方法、下一动作和相关的已复核结果；直接/间接前置证据优先 |
| 重复执行 | DSH 新任务按 work 问题与条件跨工具查重；换身份、版本、能力或条件另建项；旧调用指纹兼容 |
| 忘记失败、反证和阴性结果 | 用 notes 持久化，按目标/检查检索；修订保留旧记录 |
| 中断或超时 | 已完整捕获但未写账的回执自动补记，不重发工具；无结果的 running/unknown 保持待核对 |
| token 和来回调用开销 | 只载当前专项/能力；机械记录不调用模型；本地执行与记录合并为 run；阶段结束才导出全量文件 |
| 上下文越来越大 | CLI 默认 6,000 字符；DSH 整条恢复消息最多 8,000 字符；省略项分页，必要约束超限报错 |
| 多会话串案 | 会话显式绑定案件、项目、目标和范围摘要；错误组合拒绝读写，交接后旧会话失效 |
| 多案件共用 MCP | 按实际 provider/context_id 独占，换 slot 别名不能绕过；未决调用不允许切换 |
| 积累经验又污染新任务 | 原始事实不共享；经验经历候选、验证、限定范围、失效/修订，召回不修改检查状态 |

这是字符预算，不是模型 token 或宿主总上下文上限。原生 MCP 的大量输出若已进入宿主上下文，本包无法撤回；应结合 MCP 分页、过滤和导出。模型消耗依赖宿主与任务，不能用字符预算直接换算账单。

Agent 的命令、示例与中断处理见 [运行协议](references/runtime.md)。由 Agent 使用这些命令，业务用户仍可直接用自然语言提交任务。

本轮实现与验收见 [长任务恢复验证](references/long-task-reliability-2026-09-25.md)：包含跨工具查重、中断补记、整条恢复消息预算，以及真实 DSH 压缩后不重复请求的两轮测试；不代表全部专项已经实战验收。

多会话与经验的完整用法见 [隔离与经验协议](references/scoped-memory.md)，联网依据和选型取舍见 [调研记录](references/memory-design-research.md)。默认 SQLite FTS5/BM25，无需嵌入模型；可传入真实模型生成的向量，使用余弦与 RRF 混合排序。程序不自动安装模型、调用付费服务或向外传输案件文本；合成向量回归不代表真实语义检索效果。

升级注意：运行命令现在强制 --workspace / --session / --case。旧 SQLite 案件用 identify → bind 接入，无需丢弃已有检查；纯文件案件仍需先制定迁移映射。同一套工具共用一个私有注册库；绑定与工具观察是可信调用方协作协议，不是操作系统权限隔离或自动 MCP 探测。

## 产物

[证据契约](references/evidence-contract.md)约定每项任务使用独立目录：

```text
work/<case>/
  case.sqlite3
  captures/
  events.jsonl
  state.json
  evidence/
  specialists/
  report/
    summary.md
    report.md
    ledger.md
    coverage.json
    findings.json
    coverage.md
  resume.md
  learning/candidates.md
```

没有确认发现、部分完成或工具失败时仍生成对应状态的报告。原始证据、候选问题和已验证结论分别记录。账本是事实来源；JSON/Markdown 导出带事件版本，由运行程序重建。summary.md、report.md 和 findings.json 由报告专项据实编写，运行程序只生成机械覆盖和证据视图。

## 当前交付范围

本仓库提供融合指令、路由数据、环境补齐流程、输出契约、持久化运行辅助程序与校验脚本。安装/初始化请求及当前检查的缺项由目标机 Agent 完成外部工具安装/复用、MCP 配置与验收，普通文件安装器本身不执行这些动作。需要账号、许可证或交互提权的步骤明确报告阻塞。

能力索引按机器、Agent、宿主实例和配置版本隔离；实际工具调用失败、验收过期或证据/配置变化会使绑定失效。索引证明记录的验收上下文可用，不代表任意目标、身份、项目都已经就绪；每个案件仍须绑定实际工具上下文。收据的业务含义由执行 Agent 核验，程序不会独立伪装成 MCP 客户端探测所有服务。

本地 run 和显式目标 stdio 的 mcp-run 可组合查重与执行；后者每次使用新连接、实时 tools/list、实际 tools/call，不改宿主配置、不继承宿主页面/工程状态。原生有状态 MCP 仍使用 begin / record / review 协议。Skill 无法拦截绕过协议的直接调用，也无法保证任意外部服务 exactly-once。已有纯文件案件未自动迁移，不能建空账本后把历史检查重跑一遍。

已完成 Skill 格式、文件引用、路由映射、依赖及本地持久化回归检查；曾在 Windows 隔离目录验证标准安装器能完整复制技能包。本次未向当前电脑的 Agent 目录安装 Skill。Kali 上的 Agent 行为与真实 MCP 联调尚未验证，离线检查不代表这些任务已经执行成功。

维护时可运行（Python >= 3.9）：

```bash
python3 scripts/validate_pack.py
python3 -m unittest discover -s tests -v
```

结构结果见 [validation-results.json](validation-results.json)，格式结果见 [skill-format-validation.json](skill-format-validation.json)，运行与字符预算结果见 [runtime-validation.json](runtime-validation.json)。[持续集成](https://github.com/tancai1437-cloud/security-fusion/actions)运行 Ubuntu / Windows 离线测试，不能替代 Kali Agent 与真实 MCP 联调。

首项执行回归见 [test_start.py](tests/test_start.py)：启动命令真实访问回环 HTTP 服务、保留原始响应、在进程重启后阻止重复请求，并核对会话隔离、历史文件保护和失败报告。该测试验证程序路径，不代表已验证 DSH/OpenCode/Pi 中模型的实际任务表现。

MCP 执行链回归见 [test_execution_flow.py](tests/test_execution_flow.py)：测试专用 stdio 服务经过真实协议交换读取回环 HTTP，验证自动落盘、advance 分流、进程重启后的查重，以及分页、错目标、错会话、工具错误和超时。该服务明确是测试替身，不能作为 Burp/HexStrike 等真实服务已接通的证据；真实 Kali Agent 的方法选择与调用效果仍需现场轨迹验证。

2026-09-24 执行改造的验证范围和回退点见 [execution-validation.json](execution-validation.json)。旧版记录文件保留各自当时的验证范围。

2026-09-25 业务方法融合见 [business-validation.json](business-validation.json)：四个新增分支通过测试专用 MCP 实际访问有状态的回环服务，验证对照、证据、恢复预算与去重。测试显式提供业务特征，不代表已验证模型能自主识别这些特征或真实 Kali MCP 已接通。

2026-09-25 专精增强与验证范围见 [specialist-validation.json](specialist-validation.json)：原生/托管样本分流、XFF 请求对照、崩溃分类与预期退出码处理。Linux CI 还会真实编译并运行 ASan 正反例；这不代表 DSH 模型或真实 IDA/Ghidra/ILSpy 已完成联调。

本次环境初始化与索引回归结果见 [bootstrap-validation.json](bootstrap-validation.json)。测试使用明确标注的离线收据与临时目录，不将测试替身列为可用 MCP，也未在开发机安装外部安全工具。

## 来源

提炼来源与改编决定见[融合决策](references/upstream-decisions.md)、[33 个上游文件指纹](sources.lock.json)和[第三方署名及许可说明](THIRD_PARTY_NOTICES.md)。上游 MCP 实现保持外部依赖，本仓库没有捆绑这些服务的软件代码。
