**上游项目怎样融成当前包。**

本包只有三层。GitHub 来源选取15个项目的33个文件，另从用户提供的本地 SRC 工作流包 L01 学习现场方法。其他已调研项目继续保留在市场目录，不把所有仓库一并堆入运行上下文。这里描述的是已写入当前融合稿的规则与工具映射；不声称上游MCP已在本机运行。

| 来源 | 提炼的长处 | 融入位置 | 适配决定 |
|---|---|---|---|
| GreyDGL/PentestGPT | 有限工作项、执行回执、恢复前核对已有结果 | 第一层主循环、证据与恢复 | 用当前主会话与文件契约承载，不引入其Supervisor/Executor进程 |
| AIPentest/CyberStrikeAI | 每步目标自洽、依赖计划、新事实后重规划、事实与漏洞分开记录 | 第一层任务上下文与计划修订 | 不吸收外部预置授权或固定高强度/步数要求 |
| elementalsouls/Claude-BugHunter | 按目标指纹分流、基线、身份核验、业务问题分类与提交前验证 | recon/web/api/business/ai/validate | 合并重复小Skill为可按需读取的专项；项目统计不当成命中率 |
| trailofbits/skills | 先建立调用上下文、检验假设、反证、已知根因变体 | code/validate | 原代理复核改为同会话顺序复核，保留方法来源与许可 |
| cloudflare/security-audit-skill | 覆盖台账、不同结论的字段语义、报告从最终记录生成 | validate/report、证据契约 | 支持现有accepted_risk，部分完成可交付，不伪造独立验证 |
| Fausto-404/ai-mobile-reverse-skills | 阶段最低输入、流量与代码对齐、JNI与报告交接 | mobile专项与跨专项返回 | 保留阶段产物条件，去掉逐阶段等待菜单；不创建其代理 |
| SimoneAvogadro/android-reverse-engineering-skill | 框架先行、反编译路线选择、接口清单与重点详情分层 | mobile专项 | 不把每个APK都导向JADX；已有材料可直接使用 |
| 0x4m4/hexstrike-ai | 安全工具的明确MCP接口 | 第三层通用工具提供者 | 只借执行能力，主控仍在我们自己的Skill |
| PortSwigger/mcp-server | 代理历史、请求、WebSocket与结构化参数 | 第三层HTTP主通道 | 使用官方实现；按实际请求/响应形成证据 |
| zhizhuodemao/js-reverse-mcp | 页面上下文、列表/详情/导出、脚本与请求发起链 | 第三层前端主通道 | 按需取完整数据，导航后重新绑定相关标识 |
| vmoranv/jshookmcp | 搜索优先、描述后调用、动态能力与会话恢复 | 第三层前端补充通道 | 明确缺能力时才补充，不默认全量暴露工具 |
| zinja-coder/jadx-mcp-server | 类/方法/Manifest/smali等检索接口 | 第三层Android代码通道 | 只对合适框架生效，与样本绑定 |
| zinja-coder/apktool-mcp-server | 解包、资源与smali接口 | 第三层Android资源通道 | 默认分析，修改与重建由任务明确需要触发 |
| mrexodia/ida-pro-mcp | idalib数据库上下文、函数与引用接口 | 第三层原生分析 | 有IDA环境或工程时使用；不复制旧GUI接入方案 |
| bethington/ghidra-mcp | 实例/工具组发现与函数分析 | 第三层开源原生分析 | 与IDA构成选择分支，不为同一问题无条件重复分析 |

## src-field-methods

L01 是用户提供的 `src-6k-skill.zip`，包根为 `clown-src-6k-skill/`。档案与选读文件的 SHA256 记录在 [sources.lock.json](../sources.lock.json) 的 local_archives，保留离线来源身份，不假造 GitHub 仓库地址。原档案未提交到本仓库。

| 学习到的决策方法 | 融入位置 | 与现有流程的结合 |
|---|---|---|
| 根据业务特征选对应方法，不起手通读全库 | field-methods 的 features、8 个专项的 method_reference | 首份证据之后按需选一行；仍为主路由→专项→工具三层 |
| 当前业务面有可执行检查时优先推进，新线索带来源排队 | main-router、recon、business | 用已有 fact/decision 与增量 plan 保存，允许真实阻塞和预算导致切换，不无限扩面 |
| JS 与响应不仅提供地址，还提供构造请求的上下文 | js、recon | 记录方法、参数、身份传递和来源，实际调用核对；没有 JS 时从已有证据继续 |
| 成立结果与假阳性条件一起定义 | web、api、validate | 统一兜底、自有对象、身份无效等分别判定，阴性与未测边界进入原账本 |
| 已有方法只补新的认别条件、验证方式或反例 | report、scoped-memory | 候选审核与 supersedes 版本机制继续使用，不自动改全局 Skill |
| 同类业务面可以采样减少重复 | recon、validate | 相似性必须有证据；未测实例保留采样说明，不继承代表的 done |

这些规则为本包重新编写的指导，正文见 [现场方法](field-methods.md)，行为取舍可用 [验收场景](../examples/field-method-cases.md) 审阅。验收场景不是已执行的目标结果，也不构成模型效果指标。

没有采纳原包的全局环境覆盖、硬编码凭据、共享浏览器 Profile、无边界持续搜索、固定排除漏洞类别、按危害等级独断筛选经验，以及清理时删除已测状态的做法。报告保留可核对证据与脱敏规则，不要求披露完整会话值；公司或品牌归属也不自动扩张本次范围。原包脚本、原始长表、知识库正文和安装配置均未捆绑。

**冲突如何融合。**

以用户目标、适用条件、可复查证据和可结束的流程为共同约束。独立Agent实现不直接复制；扫描输出和猜测不直接升级结论；单个候选失败不停止覆盖；同类MCP按上下文和能力差异择一或互补。

方法提炼是写入本包的中文决策规则；运行软件保留外部实现，执行路由绑定其接口。后续吸收新项目时，必须指出新增了哪个决策或执行能力，与哪条规则重复，以及哪个样本证明它有用。

## wooyun-methods

2026-09-25 参考 [tanweai/wooyun-legacy](https://github.com/tanweai/wooyun-legacy/tree/d6a69e1779ccfe27981a4eb314b1f40f17052068)，固定版本 `d6a69e1779ccfe27981a4eb314b1f40f17052068`。该项目已在 README 宣布不再维护。学习其围绕业务关系形成检查、由领域方法逐步深入的组织思路；按本包当前事实路由与执行协议重新编写，不并入其插件入口。

| 参考材料 | 本包采用的思路 | 实际接入 |
|---|---|---|
| [authorization-domain](https://github.com/tanweai/wooyun-legacy/blob/d6a69e1779ccfe27981a4eb314b1f40f17052068/plugins/wooyun-legacy/skills/wooyun-legacy/references/authorization-domain.md) | 区分对象归属与角色操作权限 | 复用 object-boundary，新增 function-boundary |
| [authentication-domain](https://github.com/tanweai/wooyun-legacy/blob/d6a69e1779ccfe27981a4eb314b1f40f17052068/plugins/wooyun-legacy/skills/wooyun-legacy/references/authentication-domain.md) | 把账号恢复看作有绑定关系和阶段条件的流程 | reset-binding；允许匿名恢复但要求受控账号 |
| [financial-domain](https://github.com/tanweai/wooyun-legacy/blob/d6a69e1779ccfe27981a4eb314b1f40f17052068/plugins/wooyun-legacy/skills/wooyun-legacy/references/financial-domain.md) | 用业务状态验证规则是否真正生效 | order-transition；只检查已观察的一条转换 |
| [logic-flow-domain](https://github.com/tanweai/wooyun-legacy/blob/d6a69e1779ccfe27981a4eb314b1f40f17052068/plugins/wooyun-legacy/skills/wooyun-legacy/references/logic-flow-domain.md) | 区分一次性业务效果与请求次数 | single-use-effect；顺序重放结果不代表并发覆盖 |

四项均进入 procedures.json → 专项执行卡 → http.request → 当前宿主 MCP / mcp-run，并沿用证据、快照、查重和会话隔离；不新增 Agent、MCP 服务、向量依赖或全局记忆。方法按当前证据选择，原始案例和既往目标事实不进入新案件。

未采用上游宽泛触发、每项先画完整流程/凑至少五个假设、弱口令必先测、历史高危率决定当前命中率、仅凭页面/响应变化判定业务影响等规则。上游个别统计与案例分类口径不一致，本包不引入其统计、案例正文、payload 表或示例脚本。这里新增的是独立组织的一般方法与运行规则，没有把参考材料作为可无限制再分发的素材。

上游 [LICENSE](https://github.com/tanweai/wooyun-legacy/blob/d6a69e1779ccfe27981a4eb314b1f40f17052068/LICENSE) 标注 CC BY-NC-SA 4.0；后续若复制或改编其具体材料，须单独处理相应许可条件。本次参考记录不修改原有 33 个文件指纹快照。

验证见 [业务路由回归](../tests/test_business_routing.py)：使用明确标注的测试专用 MCP 和可变状态回环 HTTP 服务，验证四项实际调用、正反对照捕获、前提阻塞、压缩恢复包预算和进程重启后去重。结构化事实由测试显式提供，不是模型自动识别；不声称已测量 Kali/DSH 的现场表现。

## binary-depth

**2026-09-25 专精增强。** 继续参考 reverse-skill 固定版本 `cab634bd855fc287f6e420c1f36fd1a6b9245960` 中的原生/托管分流和“围绕当前问题读取函数/类型”的组织思路，独立编写 [二进制方法](binary-depth.md) 与三个标准库辅助脚本：文件头 profile、日志 triage、XFF 请求对照。未复制其代码、长教程、脱壳/利用链或代理配置，不增加子代理和常驻服务。

新增 binary-profile、managed-context、crash-triage、crash-reproduce、proxy-trust 五个方法，细化已有 binary-context。格式、选项和诊断含义分别以 Microsoft PE、ILSpyCmd、Clang ASan、MDN 的官方材料核对。明确区分 .dll 与 CLR、NativeAOT 与托管 IL、栈耗尽与栈缓冲区越界、回显与保护决策；不采用“有崩溃就可利用”“所有 .NET 均可恢复源码”等泛化结论。

验证范围为本包程序、回环服务和受控样例，见 [工具测试](../tests/test_specialist_tools.py) / [路由测试](../tests/test_specialist_routing.py)。合成 PE 头不能替代真实 ILSpy 反编译验收；Linux 上已有 Clang 时真实编译/运行 ASan 正反例，Windows 本地明确跳过。DSH 模型是否主动选中本包、真实 IDA/Ghidra/ILSpy 联调和未知漏洞发现能力均需另行实测。

**源文件索引。**

**2026-09-24 路由与执行调整。** 对照 zhaoxuya520/reverse-skill 的 `cab634bd855fc287f6e420c1f36fd1a6b9245960` 和 Prohao42/aimy-skill 的 `b508f38681c3262be8efbe87926780b49bf80334`：

- [reverse-skill 主路由](https://github.com/zhaoxuya520/reverse-skill/blob/cab634bd855fc287f6e420c1f36fd1a6b9245960/skills/scripts/master-route.sh)启发“给出一个当前专项”，[JS 专项](https://github.com/zhaoxuya520/reverse-skill/blob/cab634bd855fc287f6e420c1f36fd1a6b9245960/skills/js-reverse/SKILL.md)启发把动作和工具语义放在同一处；本包没有复制其路由脚本、关键词优先级或安装配置。
- aimy 内含的 [HackSkills API 分类](https://github.com/Prohao42/aimy-skill/blob/b508f38681c3262be8efbe87926780b49bf80334/ai-mian/hack-skills/skills/api-sec/SKILL.md)启发“观察到的行为→具体方法”。该内含目录自述上游为 yaklang/hack-skills，不能把知识包与 aimy Python 检测器视为自动打通的一条链。
- [aimy 工具注册与调用](https://github.com/Prohao42/aimy-skill/blob/b508f38681c3262be8efbe87926780b49bf80334/tools/tool_registry.py)启发将机械调用交给执行代码。新增 stdio 客户端按 MCP 公开协议独立实现，不捆绑 aimy 检测器，不复制批量扫描、利用或 payload 代码。
- 落地改动：主入口缩短、13 个专项去除重复层间交接字段、四个常用专项增加动作表、advance 自动带入账本元数据、mcp-run 自动连接/调用/捕获。受控测试见 [执行链回归](../tests/test_execution_flow.py)。它验证协议和状态机制，不代表真实 Agent 的方法选择已测量。

这些是新增的设计参考链接，不混入原有 33 个文件指纹快照；没有复制上游代码或整段正文。

- S01 [GreyDGL/PentestGPT / pentestgpt_agent/README.md](https://github.com/GreyDGL/PentestGPT/blob/HEAD/pentestgpt_agent/README.md)；blob 735c76f534450f2400fff9d30a0a6696ec54adaa。
- S02 [GreyDGL/PentestGPT / unified_agent/task.py](https://github.com/GreyDGL/PentestGPT/blob/HEAD/unified_agent/task.py)；blob abea6e9feeb18b0d5736f8ad835e700724f678f5。
- S03 [AIPentest/CyberStrikeAI / agents/orchestrator-plan-execute.md](https://github.com/AIPentest/CyberStrikeAI/blob/HEAD/agents/orchestrator-plan-execute.md)；blob 967d8215b0de3022d0e4713a3cc6a1f4c445d7fb。
- S04 [AIPentest/CyberStrikeAI / internal/workflow/graph_types.go](https://github.com/AIPentest/CyberStrikeAI/blob/HEAD/internal/workflow/graph_types.go)；blob 8e49be11d8e620a1f2767c3ba9d0b0fc2eb43463。
- S05 [PortSwigger/mcp-server / src/main/kotlin/net/portswigger/mcp/tools/Tools.kt](https://github.com/PortSwigger/mcp-server/blob/HEAD/src/main/kotlin/net/portswigger/mcp/tools/Tools.kt)；blob 131e67d290fadee7a9a885803cdae5aa1361c865。
- S06 [0x4m4/hexstrike-ai / hexstrike_mcp.py](https://github.com/0x4m4/hexstrike-ai/blob/HEAD/hexstrike_mcp.py)；blob 23b083b4710472df53ff3fb77c18bd30de2bdda8。
- S07 [trailofbits/skills / plugins/fp-check/skills/fp-check/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/fp-check/skills/fp-check/SKILL.md)；blob b7e7278cbae101f948f39890e5dcc088248d789d。
- S08 [trailofbits/skills / plugins/variant-analysis/skills/variant-analysis/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/variant-analysis/skills/variant-analysis/SKILL.md)；blob 8f58f54b1883110f1a38a51c9360d4b9d1b195a8。
- S09 [elementalsouls/Claude-BugHunter / skills/hunt-dispatch/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-dispatch/SKILL.md)；blob af35450ca038523214469276bf71b83ccc2b7fed。
- S10 [cloudflare/security-audit-skill / skills/security-audit/VALIDATION-AND-REPORTING.md](https://github.com/cloudflare/security-audit-skill/blob/HEAD/skills/security-audit/VALIDATION-AND-REPORTING.md)；blob 5e200d7387e665e53e0e4190fa4a5814c334c507。
- S11 [Fausto-404/ai-mobile-reverse-skills / ai-mobile-reverse-skills/SKILL.md](https://github.com/Fausto-404/ai-mobile-reverse-skills/blob/HEAD/ai-mobile-reverse-skills/SKILL.md)；blob 279d1f94144199d8319c911cef2b71b17ab7b06b。
- S12 [SimoneAvogadro/android-reverse-engineering-skill / plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md](https://github.com/SimoneAvogadro/android-reverse-engineering-skill/blob/HEAD/plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md)；blob 7659215465a9c1df87a533edb3a06cb0fc92422e。
- S13 [zhizhuodemao/js-reverse-mcp / src/tools/network.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/network.ts)；blob 242331ddd0c96f0990fc59592bceaee53547f631。
- S14 [zhizhuodemao/js-reverse-mcp / src/tools/script.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/script.ts)；blob 36a7416c5452f753a2316604acb9661a19fab7ed。
- S15 [vmoranv/jshookmcp / README.zh.md](https://github.com/vmoranv/jshookmcp/blob/HEAD/README.zh.md)；blob 6567e4ef57827de345bcc81e77d566122243ae11。
- S16 [mrexodia/ida-pro-mcp / README.md](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/README.md)；blob 698445389695a3c475bd32ab8a495de27f9eedee。
- S17 [bethington/ghidra-mcp / python/bridge_mcp_ghidra/static_tools.py](https://github.com/bethington/ghidra-mcp/blob/HEAD/python/bridge_mcp_ghidra/static_tools.py)；blob a2fa6af7ad875d5ed696ebc696aeb577f0db19d7。
- S18 [zinja-coder/jadx-mcp-server / jadx_mcp_server.py](https://github.com/zinja-coder/jadx-mcp-server/blob/HEAD/jadx_mcp_server.py)；blob 4a4416baef316bf2a7776e68dfafaef50a35424a。
- S19 [zinja-coder/apktool-mcp-server / apktool_mcp_server.py](https://github.com/zinja-coder/apktool-mcp-server/blob/HEAD/apktool_mcp_server.py)；blob 134fd8db55ce7f39280162f8f2507f71d85019bb。
- S20 [vmoranv/jshookmcp / src/server/MCPServer.tools.ts](https://github.com/vmoranv/jshookmcp/blob/HEAD/src/server/MCPServer.tools.ts)；blob b62ccc94f31820ee06df31df22a91ce881da718b。
- S21 [trailofbits/skills / plugins/audit-context-building/skills/audit-context-building/SKILL.md](https://github.com/trailofbits/skills/blob/HEAD/plugins/audit-context-building/skills/audit-context-building/SKILL.md)；blob 5f25f70751c688685e22f40ddae125d9411d2b77。
- S22 [elementalsouls/Claude-BugHunter / skills/hunt-business-logic/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-business-logic/SKILL.md)；blob 205d79b073f2b764f9fc52837ed54a119c2c3adc。
- S23 [elementalsouls/Claude-BugHunter / skills/triage-validation/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/triage-validation/SKILL.md)；blob 3ef9287c1e7f0037772ba6282933d605efca5a32。
- S24 [PortSwigger/mcp-server / src/main/kotlin/net/portswigger/mcp/tools/McpTool.kt](https://github.com/PortSwigger/mcp-server/blob/HEAD/src/main/kotlin/net/portswigger/mcp/tools/McpTool.kt)；blob 2ed9eb7dd6f42d081e03b9892e1c448531b57307。
- S25 [zhizhuodemao/js-reverse-mcp / src/tools/pages.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/pages.ts)；blob 71b9f7fdadc38b4e609a7dc415a274dce4a1a964。
- S26 [zhizhuodemao/js-reverse-mcp / src/tools/debugger.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/debugger.ts)；blob 9c7ddc6eb3a0b56ce10dcbd0bbdf51622eb3effc。
- S27 [elementalsouls/Claude-BugHunter / skills/hunt-api-misconfig/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-api-misconfig/SKILL.md)；blob ca6d677caca6cb4c3723dd55c691ee0cc22c0109。
- S28 [elementalsouls/Claude-BugHunter / skills/hunt-llm-ai/SKILL.md](https://github.com/elementalsouls/Claude-BugHunter/blob/HEAD/skills/hunt-llm-ai/SKILL.md)；blob 27ec152c2b059f8b80d61b8889415e7fa375ebf7。
- S29 [Fausto-404/ai-mobile-reverse-skills / ai-mobile-reverse-skills/docs/MCP-INTEGRATION.md](https://github.com/Fausto-404/ai-mobile-reverse-skills/blob/HEAD/ai-mobile-reverse-skills/docs/MCP-INTEGRATION.md)；blob 3e9c034f34d97ba26e11820baddb83803ef003ec。
- S30 [bethington/ghidra-mcp / README.md](https://github.com/bethington/ghidra-mcp/blob/HEAD/README.md)；blob f64b07117b96a184577335158e6788d7915369d5。
- S31 [mrexodia/ida-pro-mcp / src/ida_pro_mcp/ida_mcp/api_core.py](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/src/ida_pro_mcp/ida_mcp/api_core.py)；blob e2bfdc72eba4bd3bfb3111e5419885c7069ccd63。
- S32 [mrexodia/ida-pro-mcp / src/ida_pro_mcp/ida_mcp/api_analysis.py](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/src/ida_pro_mcp/ida_mcp/api_analysis.py)；blob eb79abbe43f0b73badd20fdac2927450f7aba29f。
- S33 [vmoranv/jshookmcp / tests/e2e/meta-tools-runtime.e2e.test.ts](https://github.com/vmoranv/jshookmcp/blob/HEAD/tests/e2e/meta-tools-runtime.e2e.test.ts)；blob 86041ce5cfef2c7369bf6fdbc5205222670d75eb。

仓库级许可为上一轮API快照，源文件可能另有归属，详见sources.lock.json。ToB相关方法改编文件保留CC-BY-SA-4.0说明；本包未把混合来源统一宣称为MIT。
