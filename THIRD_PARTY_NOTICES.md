# Third-party attribution and licensing

本包重新组织中文工作流与能力映射，不捆绑上游 MCP、扫描器或分析工具的实现代码。各专项文件列出方法来源；[sources.lock.json](sources.lock.json)保存本次读取的文件路径及 Git blob 指纹，[融合决策](references/upstream-decisions.md)记录改编方式。

## Trail of Bits 方法改编

[fusion-code](specialists/fusion-code/SKILL.md) 和 [fusion-validate](specialists/fusion-validate/SKILL.md) 的相关方法文本改编自 [Trail of Bits skills](https://github.com/trailofbits/skills)，包括 audit-context-building、variant-analysis 与 fp-check。改动包括中文表述、合并同类检查、采用当前主会话顺序复核，以及统一证据与专项返回契约。

这些改编文本按 **CC BY-SA 4.0** 提供，保留 Trail of Bits 及其贡献者的归属。许可正文与免责声明见 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode)，上游声明见 [Trail of Bits LICENSE](https://github.com/trailofbits/skills/blob/main/LICENSE)。

## 其他方法与工具接口来源

以下许可名称为来源锁定文件中记录的仓库级快照，不代替上游各文件的具体条款：

| 项目 | 本包采用的内容 | 已记录的仓库许可 |
|---|---|---|
| [GreyDGL/PentestGPT](https://github.com/GreyDGL/PentestGPT) | 工作项、回执与恢复方法 | MIT |
| [AIPentest/CyberStrikeAI](https://github.com/AIPentest/CyberStrikeAI) | 计划与重规划方法 | Apache-2.0 |
| [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) | 专项分流与验证方法 | MIT |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 覆盖与报告方法 | MIT |
| [Fausto-404/ai-mobile-reverse-skills](https://github.com/Fausto-404/ai-mobile-reverse-skills) | 移动分析阶段与产物方法 | MIT |
| [SimoneAvogadro/android-reverse-engineering-skill](https://github.com/SimoneAvogadro/android-reverse-engineering-skill) | Android 框架分流方法 | Apache-2.0 |
| [0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai) | 外部 MCP 能力及接口名映射 | MIT |
| [PortSwigger/mcp-server](https://github.com/PortSwigger/mcp-server) | 外部 HTTP/WS MCP 接口映射 | GPL-3.0 |
| [zhizhuodemao/js-reverse-mcp](https://github.com/zhizhuodemao/js-reverse-mcp) | 外部浏览器与前端 MCP 接口映射 | Apache-2.0 |
| [vmoranv/jshookmcp](https://github.com/vmoranv/jshookmcp) | 外部动态工具发现接口映射 | AGPL-3.0 |
| [zinja-coder/jadx-mcp-server](https://github.com/zinja-coder/jadx-mcp-server) | 外部 Android 代码 MCP 接口映射 | Apache-2.0 |
| [zinja-coder/apktool-mcp-server](https://github.com/zinja-coder/apktool-mcp-server) | 外部 APK 资源 MCP 接口映射 | Apache-2.0 |
| [mrexodia/ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp) | 外部 IDA / idalib MCP 接口映射 | MIT |
| [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp) | 外部 Ghidra MCP 接口映射 | Apache-2.0 |

上游软件继续使用各自许可。引用项目名称及接口不表示获得其官方背书。本包保留文件中已有的许可说明，不将混合来源统一宣称为 MIT。

## 用户提供的本地方法来源

L01：`src-6k-skill.zip`（包根 `clown-src-6k-skill/`）。用户提供该档案用于分析和学习工作方法；包内未见覆盖整个档案的许可声明，作者归属及再分发条款未核实。这里记录来源，不将其宣称为具有某种开源许可。

本次仅学习业务特征分流、现场推进、反证条件和经验筛选等一般思路，并针对现有协议重新编写指导。没有复制、发布原档案、原始知识库正文、脚本、配置、凭据或目标材料。档案指纹和具体取舍见 [来源锁定](sources.lock.json) 与 [融合记录](references/upstream-decisions.md#src-field-methods)。

## WooYun Legacy 设计参考

参考 [探微安全实验室 / tanweai/wooyun-legacy](https://github.com/tanweai/wooyun-legacy/tree/d6a69e1779ccfe27981a4eb314b1f40f17052068) 的业务关系与分层查阅思路，具体取舍见 [融合记录](references/upstream-decisions.md#wooyun-methods)。上游标注 [CC BY-NC-SA 4.0](https://github.com/tanweai/wooyun-legacy/blob/d6a69e1779ccfe27981a4eb314b1f40f17052068/LICENSE)，包含署名、非商业和相同方式共享条件。

本次针对已有路由协议编写通用的角色、恢复绑定、状态转换和一次性效果检查，没有复制其案例正文、统计表、payload 库、图表、示例脚本或插件文件。不把上游资料附带分发，也不将其标注为 MIT。今后如引入其具体材料，须明确适用许可与分发边界。

## 专精方法设计参考

2026-09-25 参考 zhaoxuya520/reverse-skill 固定版本的原生/托管分流思路；新增辅助脚本和方法独立实现，不附带上游 Skill、MCP 或工具实现。格式/命令含义依据 Microsoft、ILSpy、Clang 和 MDN 官方资料，来源和取舍见 [专精融合记录](references/upstream-decisions.md#binary-depth)。相关链接仅为来源与接口参考，不将外部材料的许可改为本包许可，也不表示已经验证外部工具的所有运行环境。
