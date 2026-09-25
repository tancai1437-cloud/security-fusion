---
name: fusion-binary
description: 按 PE/ELF/CLR 证据分流原生和托管样本，定位函数或 IL，并分类、复核内存错误与崩溃。
---

**原生/托管二进制与崩溃分析**

在当前会话执行本专项，沿用案件与目标绑定；独立调用以用户指定任务为边界。不创建子代理，不为层间交接另写一套表。

输入：样本hash、架构与问题；已有工程/符号或地址线索。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

**先做一个真实动作。** 新样本用 `start` 的绝对文件 `entry` + `--execute-local` 取得 profile；已有案件按下表 `advance`。未知类型不能仅凭 `.dll` 分流；已有 profile 就直接选函数/类型。

| 已复核事实 | 下一方法 / 首个动作 |
|---|---|
| `sample.binary`，尚无分类 | `binary-profile` → 包内 Python 只读识别 hash、PE/ELF、架构、CLR |
| `binary.profiled` + `binary.native` | `binary-context` → IDA/Ghidra 查与 `question` 相关的一个函数及引用 |
| `binary.profiled` + `binary.managed` | `managed-context` → 已有 `ilspycmd -l c` 列类型，再按问题读一个类型/IL |
| `crash.log` | `crash-triage` → 包内 Python 分类已有日志、提取行号/栈帧 |
| `crash.classified` + 完整复现材料 | `crash-reproduce` → 当前测试构建与失败输入/阴性对照，分别用 run 留证 |

1. 核对样本 hash 与当前工程；profile 不执行样本。混合模式分开记录托管/原生边界；NativeAOT 不能因后缀推定有 IL。
2. 以函数地址、完整类型名、metadata token、来源行号定位；反编译类型/命名不可靠时查汇编或 IL。
3. 栈耗尽不等于栈缓冲区越界，普通 SEGV 不等于根因；日志分类不等于已复现或可利用。
4. 只展开当前需要的 [专项方法](../../references/binary-depth.md)。缺工具/符号/构建则记录具体缺口，安装记录不能代替可调用工具。

执行路由：`binary.profile`、`binary.dotnet`、`binary.analysis`、`memory.triage`、`memory.reproduce`、`code.inspect`、`evidence.persist`。按当前动作选择真实工具，本地用 run；显式目标 stdio MCP 用 [mcp-run](../../references/mcp-execution.md) 自动调用并保存结果；有状态 MCP 用 [宿主协议](../../references/execution-router.md)。只查当前所需能力，能力 ID 不当作工具名。

阶段输出（执行中先用账本和原始证据记录，阶段结束再整理这些文件）：`binary-profile.json`、`function-evidence.json`、`behavior-analysis.md`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：问题答案能回到具体样本和地址，推断与已观察事实明确分开。

宿主有 fusion 时继续 execute，以 review 提交上一回执的实际结论；阶段暂停用 checkpoint，交付用 finish。没有宿主组件才用 [advance](../../references/observation-routing.md#简化入口advance)。保存阴性、反证和阻塞；只在阶段结束整理产物，不等用户逐阶段选择。

**方法来源。**

- S16 [mrexodia/ida-pro-mcp · README.md](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/README.md)
- S31 [mrexodia/ida-pro-mcp · src/ida_pro_mcp/ida_mcp/api_core.py](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/src/ida_pro_mcp/ida_mcp/api_core.py)
- S32 [mrexodia/ida-pro-mcp · src/ida_pro_mcp/ida_mcp/api_analysis.py](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/src/ida_pro_mcp/ida_mcp/api_analysis.py)
- S17 [bethington/ghidra-mcp · python/bridge_mcp_ghidra/static_tools.py](https://github.com/bethington/ghidra-mcp/blob/HEAD/python/bridge_mcp_ghidra/static_tools.py)
- S30 [bethington/ghidra-mcp · README.md](https://github.com/bethington/ghidra-mcp/blob/HEAD/README.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
