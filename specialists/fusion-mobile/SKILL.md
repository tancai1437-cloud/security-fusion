---
name: fusion-mobile
description: 分析Android样本的框架、Manifest、代码与网络接口，并将JNI/SO或WebView逻辑交给对应专项；适用于APK及反编译材料。
---

**移动端分流与链路对齐**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：样本或反编译目录；样本标识、目标问题；可用流量/设备材料。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先识别Native Java/Kotlin、Flutter、React Native、Cordova/WebView等框架，再选择代码路径；框架标识必须有文件依据。
2. JADX用于Java/Kotlin类、方法和调用线索；Apktool补Manifest、资源和smali。JADX无有效代码时不推导样本没有相关功能。
3. 将网络接口与调用代码按方法、路径、参数和身份对齐；无法对齐的项保留未知。
4. JNI/SO线索交fusion-binary，WebView/JS逻辑交fusion-js。原生分析不是每个APK必经阶段。
5. 风险综合后进入fusion-validate，最后形成样本画像、协议映射、证据和报告。

执行路由：`mobile.unpack`、`mobile.code`、`http.history`、`binary.analysis`、`js.source`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`app-profile.json`、`entrypoints.json`、`traffic-code-map.json`、`mobile-findings.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：框架分流有依据、关键链路有证据；未覆盖的运行环境与原生部分明确列出。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

**方法来源。**

- S12 [SimoneAvogadro/android-reverse-engineering-skill · plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md](https://github.com/SimoneAvogadro/android-reverse-engineering-skill/blob/HEAD/plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md)
- S11 [Fausto-404/ai-mobile-reverse-skills · ai-mobile-reverse-skills/SKILL.md](https://github.com/Fausto-404/ai-mobile-reverse-skills/blob/HEAD/ai-mobile-reverse-skills/SKILL.md)
- S29 [Fausto-404/ai-mobile-reverse-skills · ai-mobile-reverse-skills/docs/MCP-INTEGRATION.md](https://github.com/Fausto-404/ai-mobile-reverse-skills/blob/HEAD/ai-mobile-reverse-skills/docs/MCP-INTEGRATION.md)
- S18 [zinja-coder/jadx-mcp-server · jadx_mcp_server.py](https://github.com/zinja-coder/jadx-mcp-server/blob/HEAD/jadx_mcp_server.py)
- S19 [zinja-coder/apktool-mcp-server · apktool_mcp_server.py](https://github.com/zinja-coder/apktool-mcp-server/blob/HEAD/apktool_mcp_server.py)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
