---
name: fusion-js
description: 分析前端脚本、接口发起链和运行时输入输出，为Web/API评估或独立JS研究提供可复查依据。
---

**前端JS与运行时分析**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：页面/脚本材料；需要回答的调用或数据流问题。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 已有脚本或流量能回答问题时先直接检查；需要页面/动态证据时优先 JS Reverse MCP，先选正确页面，再定位请求和发起脚本；按列表→详情→完整导出逐级读取。
2. 围绕实际调用问题定位函数与输入输出，不将整站脚本一次塞入上下文。静态推断和运行观察分别记录。
3. 需要额外变换或动态观察能力时才调用jshook的搜索/描述/调用路径；不得把元工具搜索结果当执行证据。
4. 导航会改变脚本标识，暂停会影响页面行为；每次观察记录页面与脚本版本，完成后恢复本次改变的调试状态。
5. 用可控输入比较观察与本地重建的输出；缺环境条件则返回缺口，不声称已复现。

**把线索变成可验证请求。** 除路径外，保留方法、参数构造、身份传递、响应解析和脚本位置，并与实际流量核对。字符串里的路径只算候选；敏感值用安全引用。JS 取不到时利用已有流量、内联内容或文档继续，并注明限制，不让其阻塞纯 API 工作。细节见 [JS 线索与降级](../../references/field-methods.md#js)。

执行路由：`browser.observe`、`http.history`、`js.source`、`js.runtime`、`evidence.persist`。已有本地工具直接 start/run；需要 MCP 且工具选择不明确时，按 [执行路由规则](../../references/execution-router.md) 只查当前能力。能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`script-map.json`、`runtime-observations.json`、`exported-artifacts/`、`analysis-answer.md`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：核心问题有代码位置或运行证据支持；为原任务返回必要参数/条件，不夺取任务主控。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- L01 用户提供的 SRC 工作流包：方法选择与推进思路，见 [融合记录](../../references/upstream-decisions.md#src-field-methods)。

- S13 [zhizhuodemao/js-reverse-mcp · src/tools/network.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/network.ts)
- S14 [zhizhuodemao/js-reverse-mcp · src/tools/script.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/script.ts)
- S25 [zhizhuodemao/js-reverse-mcp · src/tools/pages.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/pages.ts)
- S26 [zhizhuodemao/js-reverse-mcp · src/tools/debugger.ts](https://github.com/zhizhuodemao/js-reverse-mcp/blob/HEAD/src/tools/debugger.ts)
- S15 [vmoranv/jshookmcp · README.zh.md](https://github.com/vmoranv/jshookmcp/blob/HEAD/README.zh.md)
- S20 [vmoranv/jshookmcp · src/server/MCPServer.tools.ts](https://github.com/vmoranv/jshookmcp/blob/HEAD/src/server/MCPServer.tools.ts)
- S33 [vmoranv/jshookmcp · tests/e2e/meta-tools-runtime.e2e.test.ts](https://github.com/vmoranv/jshookmcp/blob/HEAD/tests/e2e/meta-tools-runtime.e2e.test.ts)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
