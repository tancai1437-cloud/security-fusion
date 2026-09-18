---
name: fusion-binary
description: 分析提供的PE/ELF/SO等原生程序，通过函数、交叉引用和反编译回答具体行为或安全问题。
---

**原生二进制分析**

在主控编排中只完成当前工作项，保留 mission_id / case_root / scope_ref / workitem_id / return_to。独立调用时以用户指定的小任务为边界。当前主会话顺序执行，不创建子代理。

输入：样本hash、架构与问题；已有工程/符号或地址线索。读取当前工作项与必要证据，不默认载入全部专项或全部MCP工具。

1. 绑定当前样本与工程；已有IDA环境使用idalib-mcp，开源路径选Ghidra，默认不重复跑两套。
2. 先查函数/字符串/调用关系索引，再读取与问题有关的反编译和引用，避免遍历全库消耗上下文。
3. 函数命名、反编译类型和静态路径可能不准确；保留地址、样本标识及原始依据，必要时交叉核对。
4. 工具错误、函数缺失与不可达路径分别记录。确认影响所需运行条件交fusion-validate，不由反编译文本直接推导运行成功。

执行路由：`binary.analysis`、`code.inspect`、`evidence.persist`。按 [执行路由规则](../../references/execution-router.md) 执行 fusion.py catalog --capability <id> 按需选择工具；能力ID不是工具名，最终参数和调用标识来自宿主实际接口。执行与结果用 [运行协议](../../references/runtime.md) 的 run 或 begin/record/review 记账；保存阴性结果和被否定假设，返回主控前确认已落盘。

输出：`binary-profile.json`、`function-evidence.json`、`behavior-analysis.md`。产物位于当前案件的本专项工作目录，按 [证据契约](../../references/evidence-contract.md) 关联，不在Skill目录写任务数据。

完成条件：问题答案能回到具体样本和地址，推断与已观察事实明确分开。

结束时返回 status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。主控接收后继续剩余工作；无需用户逐阶段选菜单。缺少前提时返回blocked及最小缺口，不伪造完成。

**方法来源。**

- S16 [mrexodia/ida-pro-mcp · README.md](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/README.md)
- S31 [mrexodia/ida-pro-mcp · src/ida_pro_mcp/ida_mcp/api_core.py](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/src/ida_pro_mcp/ida_mcp/api_core.py)
- S32 [mrexodia/ida-pro-mcp · src/ida_pro_mcp/ida_mcp/api_analysis.py](https://github.com/mrexodia/ida-pro-mcp/blob/HEAD/src/ida_pro_mcp/ida_mcp/api_analysis.py)
- S17 [bethington/ghidra-mcp · python/bridge_mcp_ghidra/static_tools.py](https://github.com/bethington/ghidra-mcp/blob/HEAD/python/bridge_mcp_ghidra/static_tools.py)
- S30 [bethington/ghidra-mcp · README.md](https://github.com/bethington/ghidra-mcp/blob/HEAD/README.md)

以上为本包对来源方法/接口的中文提炼和组合；上游软件保持原项目与许可，未复制安装其运行代码。
