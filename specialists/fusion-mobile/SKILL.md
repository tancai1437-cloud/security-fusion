---
name: fusion-mobile
description: 分析Android样本的框架、Manifest、代码与网络接口，并将JNI/SO或WebView逻辑交给对应专项；适用于APK及反编译材料。
---

**移动端分流与链路对齐**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：样本或反编译目录；样本标识、目标问题；可用流量/设备材料。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 先识别Native Java/Kotlin、Flutter、React Native、Cordova/WebView等框架，再选择代码路径；框架标识必须有文件依据。
2. JADX用于Java/Kotlin类、方法和调用线索；Apktool补Manifest、资源和smali。JADX无有效代码时不推导样本没有相关功能。
3. 将网络接口与调用代码按方法、路径、参数和身份对齐；无法对齐的项保留未知。
4. JNI/SO线索交fusion-binary，WebView/JS逻辑交fusion-js。原生分析不是每个APK必经阶段。
5. 风险综合后进入fusion-validate，最后形成样本画像、协议映射、证据和报告。

执行路由：`mobile.unpack`、`mobile.code`、`http.history`、`binary.analysis`、`js.source`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 执行 fusion.py catalog --capability <id> 按需选择工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

输出：`app-profile.json`、`entrypoints.json`、`traffic-code-map.json`、`mobile-findings.json`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：框架分流有依据、关键链路有证据；未覆盖的运行环境与原生部分明确列出。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S12 [SimoneAvogadro/android-reverse-engineering-skill · plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md](https://github.com/SimoneAvogadro/android-reverse-engineering-skill/blob/HEAD/plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md)
- S11 [Fausto-404/ai-mobile-reverse-skills · ai-mobile-reverse-skills/SKILL.md](https://github.com/Fausto-404/ai-mobile-reverse-skills/blob/HEAD/ai-mobile-reverse-skills/SKILL.md)
- S29 [Fausto-404/ai-mobile-reverse-skills · ai-mobile-reverse-skills/docs/MCP-INTEGRATION.md](https://github.com/Fausto-404/ai-mobile-reverse-skills/blob/HEAD/ai-mobile-reverse-skills/docs/MCP-INTEGRATION.md)
- S18 [zinja-coder/jadx-mcp-server · jadx_mcp_server.py](https://github.com/zinja-coder/jadx-mcp-server/blob/HEAD/jadx_mcp_server.py)
- S19 [zinja-coder/apktool-mcp-server · apktool_mcp_server.py](https://github.com/zinja-coder/apktool-mcp-server/blob/HEAD/apktool_mcp_server.py)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
