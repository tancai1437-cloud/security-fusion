# DSH 执行约束与恢复

适用于 DSH 0.1.2-rc.1。Skill 提供方法，宿主组件负责让实际调用持续经过执行入口、保存真实回执、恢复任务状态，并在缺少交付记录就结束时有限纠正。组件不替模型证明业务结论正确。

## 安装与升级

普通 `skills add` 只复制技能文件。Agent 在已识别当前 DSH profile 后，执行安装器；不要猜 profile 或改另一个 Agent 的配置。示例路径需换成当前环境真实路径：

```bash
FUSION_ROOT="$HOME/.agents/skills/security-fusion"
python3 "$FUSION_ROOT/scripts/install_dsh_adapter.py" \
  --profile /actual/dsh/profile \
  --state-dir /actual/private/security-fusion \
  --python python3
```

Windows 可将解释器设为 `python` 或实际绝对路径。`--dry-run` 只检查并显示将配置的位置。安装器复用已有 DSH 依赖，复制三个 adapter 模块，向所选 profile 的 cordis.patch.yml 加一个有边界标记的条目，备份改动前的配置；重复执行更新同一条目。它保留其他配置和原有案件，不安装模型或安全工具。

重启该 profile 后，确认真实工具列表包含 `fusion`；执行结果应有实际 `tool_call_id`、`case_path` 和 `observed.capture`。安装器返回 `configured_requires_restart`，不把写完配置称为运行已接通。

已有手工添加、没有管理标记的 security-fusion-host 条目时，安装器会保留并报告冲突。维护该原条目也可以：同时更新 [dsh.mjs](../adapters/dsh.mjs)、[dsh-runtime.mjs](../adapters/dsh-runtime.mjs)、[dsh-execution.mjs](../adapters/dsh-execution.mjs)，三者必须在同一目录；skillRoot 指向当前技能包，stateDir 在包外。不可仅更新一个 JS 文件。

## 一次调用完成一项实际动作

首次调用示意，工具名和 arguments 使用当前宿主真实接口：

```json
{
  "action": "execute",
  "request": {
    "objective": "核对已授权入口的正常响应",
    "scope": "用户指定的精确入口，只读，不跟随范围外跳转",
    "target": "https://authorized.example/entry",
    "skill": "fusion-web",
    "capability": "http.request",
    "purpose": "取得无自定义请求头的基线",
    "work": {"key": "entry-baseline", "conditions": {"resource": "/entry", "control": "no-custom-header"}},
    "next": "根据当前专项核对剩余对照",
    "tool": "实际宿主工具名",
    "arguments": {"实际参数": "实际值"},
    "deliverables": ["REPORT.md"]
  }
}
```

不需要提前生成 task.json、查 CLI 帮助、手工建案或填写 MCP 清单。程序验证专项/能力、绑定当前会话、登记检查，经 DSH 原生权限流程调用工具，捕获回执，再返回必要预览。完整 arguments/result 留在该会话私有目录；输入只传宿主凭据引用，不嵌入密钥。新任务的目标检查必须声明 work:{key,conditions}。相同目标、版本、身份、能力以及 work 条件共用一个检查，换工具也复用已复核结果；完整调用参数继续保存在各自回执。evidence.persist 整理/搜索可以不声明 work，按调用参数查重。旧会话继续兼容调用指纹，不把旧结果自动猜配到新问题。

下一次 execute 可加 `review:{"summary":"根据刚才实际输出得出的结论","verdict":"done"}`，复核本会话上一次执行；需要复核较早项才显式加 attempt。这不是自动根据退出码判成功。失败/中断结果不能直接判 done；未知是否执行时先 reconcile，不重发。

既有 CLI 操作仍支持 args/input_json，案件/会话由宿主提供。使用结构化 execute 时，shell、搜索、读写、MCP 都沿此入口执行，调用时自动记录，无需再手工 record。

## 长任务中的问题与成果

新增约定与验收见 [基础能力](foundations.md)。所有交付文件必须在 case_path 内；相对 write/edit 路径会在调用前解析到本案，成功写入自动保存不可变副本。读取共享源码仍使用项目绝对路径。任意 shell/MCP 的嵌入命令无法靠路径字符串实现沙箱，须显式指定本案输出位置；当前组件不声称阻止所有越界写入。

首次 execute 可声明 criteria:[{id,question}]，省略时以原 objective 为一项，之后不因压缩改写目标。finish 可带 assessment:[{criterion,attempts:[实际调用 ID],summary}]；也可提前用 assess 的 input_json 存入账本。程序核对已复核证据、依赖版本和每一项是否有评估；不独立判断自然语言推论是否正确。旧案件未声明 criteria 时仍属旧协议，不追补虚构验收。

work.key 是稳定的检查问题，如 entry-baseline，conditions 是会影响结论的具体资源、样本版本、请求变化或对照条件。换工具时原样沿用；不要将“用 curl 读一次”作为 key，再将“用 MCP 读一次”另起一个 key。已完成项返回 reuse；未复核/未知项返回 hold；复测须说明 retest_reason。该协议不能自动理解任意 shell 的语义，条件填错仍可能错误复用，调用方必须准确描述条件。

execute 的可选 next 在实际工具调用前写入 continuation，标记 proposed_not_executed。恢复时程序生成 next_action：先 review/reconcile，再 execute；未就绪依赖列在 blocked_by，不阻塞独立可执行项。旧 checkpoint 在真正继续执行后清除，避免它把后续阶段重新指回早先动作。

results 优先带回当前检查的直接/间接前置结论，然后补充同目标的近期已复核结果，包括相关 fact/negative/refuted 笔记、证据路径、身份与版本条件。证据哈希、依赖变化和时效分别核对；历史观察尚可追溯，不等于现在仍可复用。结果只是 Agent 根据真实回执作出的复核，程序不替它证明结论正确。其余结果保留在账本，按 omitted_results 分页查询。

## MCP 的目标上下文

真实 MCP 工具从当前 DSH registry 调用，不建立冒充原页面的新连接。对依赖当前页面/工程的 MCP，先用既有 context-set 保存现场观察，并向 execute 传 context_slot；原有目标、身份、新鲜度和独占检查继续有效。不同会话的“最近页面”不能互认。

如果服务在启动配置中确实固定为单一目标，维护者可在 adapter config 的 `boundTools` 中将真实工具名映射到该精确目标，省略每次 context_slot。只能来自已核对的服务配置，不让模型靠声明把任意 MCP 当作已绑定。例如本地实验服务的固定 URL/样本属于这种情况；浏览器和通用 shell 不属于固定目标服务。

## 持续执行、压缩和结束

- 激活后，实际工具必须通过 execute；有限次直接读取当前技能文件可用于方法选择。控制类工具、用户提问仍可用。拦截是宿主执行前检查，不靠模型自觉重复读 Skill。
- 每次结果包含当前路由和回执。激活、新轮次、压缩或执行状态改变时从磁盘恢复；通过 DSH 的已记录 surface replace 替换上一恢复块，原始日志不删。工作集先放相关结果，再在预算内补入完整方法；method_deferred 表示按 source 读取，完成条件和方法来源始终保留。整条当前恢复消息上限 8,000 UTF-16 单元；CLI 默认 6,000 字符，不等于模型 token 数或整个对话预算。
- `checkpoint` 保存 summary 与 next，用于用户要求暂停或实际阻塞；明确不是完成。`resume` 从同一案件恢复，沿未完成动作继续。
- `finish` 要求已登记工作无 pending/running/unknown/review，报告和首次声明的交付文件存在且非空，所有宿主捕获件哈希匹配。未复核时直接返回相关调用 ID，沿 execute 的 review 处理，不靠重复请求补账。报告至少引用一个完整的实际 CALL-… 回执 ID，引用不存在的调用会拒绝；并生成机器可核对的 host-adherence.json。失败/受阻项尚存、或当前专项规定产物缺失时只能按 partial 交付，返回具体缺口，不声称全完成。生成的报告、代码仍须做任务对应的语义验证。
- 未调用 finish/checkpoint 就结束，宿主最多补充两次纠正；仍不通过记录 incomplete，避免无限消耗。用户改成分析、取消或切到其他任务时用 `suspend(reason)`，保留旧案并释放该执行约束。
- 若宿主结果已完整落盘而账本 record 因进程退出中断，下次恢复核对 owner/check/捕获哈希，只补记原回执，不重发工具，也不自动判 done。没有完整回执的 running/unknown 仍需核对实际状态。
- 模型输出上限、取消等强制结束可能不经过上述纠正 hook；组件另记录实际 turn/end 原因及 interrupted_without_delivery。模型完全不发工具调用时，执行入口无法替它做分析；保留案件供受限续跑，不自动无限重试或把异常当成功。

同项目不同会话使用宿主真实 session ID 分案；同会话不能悄悄换目标。新案件的共享经验项目标识包含规范 cwd 的摘要，避免两个不同路径的同名文件夹误共用经验。每次恢复按原目标和当前问题自动触发本地关键词检索，只召回同项目/专项已审核且有效的方法卡；有真实向量时仍可用 CLI 显式混合检索，无额外模型或嵌入服务调用。外部目标数据不成为任务指令，最新用户指令始终优先。

## 边界与回退

这是一套可观察的执行约束，不是操作系统沙箱。它能检查已声明专项与能力的匹配、真实调用与交付条件，不能保证模型绝不会误判、选择错误测试面或写错程序；模型给工具贴上能力标签也不证明工具适合这一步。新任务在准确声明 work 条件时可以跨工具查重；改名或错误描述条件的语义重复仍不能自动识别。宿主权限与目标范围控制仍需正常启用。对其他未验证版本、Pi/OpenCode 不能宣称支持这些 hook；仅使用 Skill 文本时也没有这些执行约束。

安装器配置的组件可用相同参数加 `--uninstall` 移除注册并重启；模块、配置备份及案件数据保留。手工配置则移除对应插入项。历史 CLI 案件仍可按显式绑定协议读取。

此前的旧版恢复接入记录见 [2026-09-25 联调](agent-integration-2026-09-25.md)，不能将旧版数据视为本执行约束版本的验收结果。
