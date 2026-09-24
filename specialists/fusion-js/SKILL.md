---
name: fusion-js
description: 分析前端脚本、接口发起链和运行时输入输出，为Web/API评估或独立JS研究提供可复查依据。
---

**前端JS与运行时分析**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：页面/脚本材料；需要回答的调用或数据流问题。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

| 要回答的问题 | 立即选择的工具动作 | 得到证据后 |
|---|---|---|
| 请求从哪里发起 | 当前 MCP 的网络请求列表 → 请求详情/initiator；缺流量才在已核对页面触发正常操作 | 保存请求 ID 和脚本位置 |
| 参数如何构造 | 脚本列表 → 相关源码搜索 → 函数附近源码；已有文件直接 rg | 记录方法、base URL、序列化及身份传递 |
| 静态结果仍缺运行条件 | 当前 MCP 的运行采样/Hook；必要时断点并读取暂停信息 | 比较同一受控输入的真实值与本地结果 |
| 已还原真实 API 请求 | 提交 `api.operation` 及原始请求引用，转 API 具体方法 | 复用已有基线，不重新进入 recon |

上表是工具语义，不是假定存在的裸函数名。先在当前已连接工具中匹配真实接口；jshook 需要元工具时只 search/describe 当前所需动作，再 call。页面、脚本与工程状态使用宿主连接，不能把新 stdio 进程当作原页面。

1. 已有脚本或流量能回答问题时先直接检查；需要页面/动态证据时优先 JS Reverse MCP，先选正确页面，再定位请求和发起脚本；按列表→详情→完整导出逐级读取。
2. 围绕实际调用问题定位函数与输入输出，不将整站脚本一次塞入上下文。静态推断和运行观察分别记录。
3. 需要额外变换或动态观察能力时才调用jshook的搜索/描述/调用路径；不得把元工具搜索结果当执行证据。
4. 导航会改变脚本标识，暂停会影响页面行为；每次观察记录页面与脚本版本，完成后恢复本次改变的调试状态。
5. 用可控输入比较观察与本地重建的输出；缺环境条件则返回缺口，不声称已复现。

**把线索变成可验证请求。** 除路径外，保留方法、参数构造、身份传递、响应解析和脚本位置，并与实际流量核对。字符串里的路径只算候选；敏感值用安全引用。JS 取不到时利用已有流量、内联内容或文档继续，并注明限制，不让其阻塞纯 API 工作。细节见 [JS 线索与降级](../../references/field-methods.md#js)。

执行路由：`browser.observe`、`http.history`、`js.source`、`js.runtime`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`script-map.json`、`runtime-observations.json`、`exported-artifacts/`、`analysis-answer.md`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：核心问题有代码位置或运行证据支持；为原任务返回必要参数/条件，不夺取任务主控。

读取结果后，按 [advance](../../references/observation-routing.md#简化入口advance) 提交复核结论与新事实，继续所选方法；没有新事实就处理当前证据缺口。保存阴性、反证和阻塞，阶段结束再整理上述产物，无需用户逐阶段选择。

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
