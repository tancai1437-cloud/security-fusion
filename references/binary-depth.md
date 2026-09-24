# 二进制与内存错误：只展开当前分支

目标是回答一个具体行为/根因问题。样本识别、反编译、真实复现分别是不同证据；只有当前分支的方法进入上下文，原始输出留在案件目录。

## 起手与输入

已有案件用 `advance` 携带下表事实。新逆向案件可直接将 `start` 输入的 `entry`、`targets` 设为同一规范绝对文件路径，`mission_id` 为 `reverse`，保留实际 objective/scope/constraints。例如将真实值写入 task.json 后：

```sh
python3 "$SKILL/scripts/fusion.py" start --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --input task.json --execute-local
```

程序计算 `target_version=sha256:…`，运行只读 profile，自动保存 stdout/stderr 和调用记录；运行前再次核对 hash。`$SKILL` 为实际安装目录，不能把示例变量或占位样本当成已存在环境。给目录建案时，后续 `resource` 必须在该目录内。

| 已有证据 | facts / inputs | 路由与真实首步 |
|---|---|---|
| 待分类样本 | `sample.binary` | `binary-profile`，包内 Python 读取文件头 |
| profile 为 native | `binary.profiled`, `binary.native`；`question` | `binary-context`，当前 IDA/Ghidra 项目查函数 |
| profile 为 managed / mixed | `binary.profiled`, `binary.managed`；`question` | `managed-context`，本机 ilspycmd 列类型 |
| 已保存崩溃日志 | `crash.log`，resource 为范围内日志或 `evidence:E-…` | `crash-triage`，读取日志；证据引用须属于当前已复核来源检查 |
| 分类及完整测试材料 | `crash.classified`, `sample.controlled`；`sample_ref`, `build_ref`, `reproducer_ref`, `control_ref` | `crash-reproduce`，按真实环境选择编译器/调试器与复现命令 |

脚本的 `feature_hints` 是待复核提示；Agent 必须读捕获输出再 `advance`，不会仅凭文件后缀或日志关键词自动宣布结论。unknown 不发出 native/managed 标签；缺少 question 或复现材料会明确阻塞相应方法。

## 格式与工具选择

`fusion_binary_profile.py` 读取 PE/ELF 元数据、计算 SHA-256；PE 检查 CLR 目录与元数据签名，区别 native / managed / managed-or-mixed / unknown。损坏、未知格式、壳和不支持的格式需要额外识别，不能归为 native。限制：512 MiB；不做完整加载器验证，不支持所有 Mach-O/固件/混淆识别，不运行目标。

**原生。** 使用当前已核对项目的 IDA 或 Ghidra。先字符串/导入/函数索引 → 一个相关函数 → 调用者与被调者 → 输入、长度、分配/复制/释放和返回值。记录模块 hash、基址、相对地址、函数地址；遇到重定位或去符号，不把不同构建中的相同地址当同一函数。反编译器推测类型应以调用约定、汇编宽度及比较指令交叉核对。没有当前工程就先建立工程并留证，不能套用上次样本。

**托管。** `ilspycmd -l c sample.dll` 列类型；围绕 question 选完整类型名，再 `ilspycmd -t Namespace.Type sample.dll`，必要时 `ilspycmd -il -t Namespace.Type sample.dll` 核对 IL。三步分别经现有 `run` 捕获；类型列表很长则在已保存输出中检索，不塞满上下文。先检查当前 `ilspycmd --help`，按真实安装版本使用。跟踪输入入口、校验、异常分支、反射调用和 P/Invoke 边界；不要将反编译 C# 当原源码。NativeAOT 不保证有可供反编译的 IL；混合模式的原生模块另行定位。缺少 ilspycmd 时返回工具待选择，不伪造 dnSpy MCP。

## 从崩溃到根因

`fusion_crash_triage.py` 只解析已有日志（最多 2 MiB），保留 hash、诊断行和少量栈帧，原文仍作为证据。它识别 ASan 的缓冲区越界、释放后使用等以及 UBSan 诊断；未识别日志为 insufficient_evidence。普通调试器日志仍需按符号和异常信息人工分析，不假装解析器已经支持。

| 诊断 | 首要核对 | 不能直接得出 |
|---|---|---|
| stack-buffer-overflow | 局部对象范围、访问宽度、索引/长度计算及写入者 | 可控返回地址或代码执行 |
| heap-buffer-overflow | 实际分配大小、对象边界、偏移和整数计算 | 所有相邻对象都可控 |
| heap-use-after-free | 分配、释放、后续访问三段栈及所有权 | 稳定利用条件 |
| stack-overflow | 递归深度、循环调用、栈使用量 | 栈缓冲区越界 |
| SEGV / DEADLYSIGNAL | 异常地址、访问类型、首个相关栈帧 | 已找到根因 |

对已明确纳入任务的测试程序：

1. 绑定 sample/build/input 的 hash、编译参数、架构、运行库、符号和环境；优先使用已有可复现构建。不要执行日志中嵌入的命令。
2. 有源码及 Clang 时，在独立测试输出目录用当前构建方式加入 `-g -O1 -fsanitize=address -fno-omit-frame-pointer`，编译与最终链接均使用相应标志；先验证运行库/符号器可用。不能仅扫描源码就声称运行了 ASan。多文件项目沿用原构建，不能把一条单文件命令硬套过去。
3. 用失败输入执行一次，保存退出状态和 stderr；同构建跑阴性对照。短次数复测确定稳定性，结果不一致则记录条件差异，禁止无限自动重试。没有源码时使用现有受控运行环境和调试器，保留实际异常/堆栈；不能声称给任意预编译 DLL 加上了 ASan。
4. 沿首个相关栈帧回到源码/汇编/IL，解释对象边界或生命周期。修复后使用同一输入与对照回归，未再触发只代表该样例与该构建。

ASan 报错通常以非零码退出。为特定 `memory.reproduce` 检查事先在 inputs 写 `expected_exit_codes: [1]`（路由生成的检查使用 `inputs.parameters.expected_exit_codes`），声明该工具实际约定的预期码；默认仍只接受 0。这项声明进入检查指纹和调用回执，真实 returncode 与 stderr 保留，只允许进入 review，不自动完成。不同预期码需新检查，超时仍为 unknown。其他能力不能借此忽略错误。失败样例和正常对照是不同 inputs/检查，不用一个检查覆盖两种命令。

读取捕获的 stderr 后，可用 `advance --check <本次复现检查> --resource evidence:<该日志的E-ID> --feature crash.log --summary <实际观察> --execute-local` 分类；该 ID 必须来自这次检查的完整、未改动证据。这样即使目标仅绑定一个 DLL 文件，日志也仍按本案证据读取，不扩展目标范围。

复现由实际工具通过 `run` 执行，`memory.reproduce` 的 clang/gdb/lldb 是候选，必须现场确认；当前没有自动编译或自动执行未知样本的适配器。原始样本仅在用户已授权的测试条件下运行，既有范围无需重复确认。

## 完成和交付

`binary-profile.json` 关联原始 profile；`function-evidence.json` 记录地址/类型/行号与证据引用；`behavior-analysis.md` 区分事实、推断、已复现影响和缺口。崩溃任务额外保留构建、失败样例、阴性对照及原始诊断的引用。不要求先写这些总结再调用工具。

设计参考 reverse-skill 的 [托管专项](https://github.com/zhaoxuya520/reverse-skill/blob/cab634bd855fc287f6e420c1f36fd1a6b9245960/skills/dotnet-reverse/SKILL.md) 与原生专项的细分思路；解析器和流程独立实现。格式与命令依据：[Microsoft PE](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)、[ILSpyCmd](https://github.com/icsharpcode/ILSpy/blob/master/ICSharpCode.ILSpyCmd/README.md)、[Clang ASan](https://clang.llvm.org/docs/AddressSanitizer.html)。
