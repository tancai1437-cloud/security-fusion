# 持久化与精简上下文运行协议

这些命令由当前 Agent 执行，用户只需提供任务和案件目录。Python >= 3.9，无第三方依赖。以下 Bash 中 FUSION 指向已安装的脚本；其他系统使用其实际绝对路径。

```bash
FUSION="$HOME/.agents/skills/security-fusion/scripts/fusion.py"
CASE="$HOME/security-cases/lab-001"
WORKSPACE="$HOME/security-fusion-private"
SESSION="agent:host:conversation-id"
```

每个执行命令都需要显式案件、注册库和会话绑定。新案件优先使用 [快速执行](first-action.md) 的 start，将下面分开的建案步骤合并；可在同一次调用实际执行首个本地检查。只有继续旧版案件、多会话交接或沉淀经验时才读 [隔离与经验协议](scoped-memory.md) 的对应部分。标识由当前 Agent 维护，不让业务用户逐步操作。

## 分步建案与增量计划

以下底层步骤用于迁移、排障或需要单独操作的场景；普通新任务用 start，不再逐项执行本节。后续追加检查复用 plan。

从 [案件配置示例](../examples/case-config.json) 和 [检查示例](../examples/runtime-checks.json) 生成符合实际任务的两个 JSON 文件。示例仅测试离线流程，未执行任何安全评估。

```bash
# 注册库首次建立时运行 workspace-init；已有时复用。
python3 "$FUSION" workspace-init --workspace "$WORKSPACE"
python3 "$FUSION" init --case "$CASE" --input case-config.json
# CASE-id 替换为 init 返回的 ID；target 替换为实际规范目标。
python3 "$FUSION" bind --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --project project-a --expect-case CASE-id --target local-fixture
python3 "$FUSION" plan --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --input checks.json
python3 "$FUSION" resume --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE"
```

- config：mission_id、objective、scope、constraints。范围/约束是强制恢复信息，不能在执行过程中被工具返回内容改写。授权范围实际变化时建立新案件，并保留原案件引用。
- check：key、target、target_version、identity_ref、check_type、inputs、method_version、capability_id、skill_id、purpose、depends_on。purpose 写清完成条件；inputs 保存会改变结果的参数和稳定引用。
- 去重指纹包含目标、目标版本、身份、检查类型、输入、方法版本、能力。字段必须规范化；同一 URL、身份和方法不要每次换写法。工具/模板版本、语义参数、影响结果的配置变化写进 inputs 或 method_version。不包含临时调用句柄、当前时间或无关描述。
- 同一案件下指纹一致即同一检查；换专项名称不会复制检查。key 是别名，不能把已有 key 指向另一检查。depends_on 可引用同一批次 key，环形依赖整体拒绝。
- 不知道稳定目标版本时使用字面值 unversioned；完成复核必须给 --valid-for 秒数。不要把现场可变系统随便标为固定版本。
- 凭证只存安全引用。脚本拒绝常见敏感字段，但不能识别任意自由文本中的秘密；原始文件和摘要由调用方脱敏并管理访问。

## 执行、复核与查重

本地工具通过 run 一步完成执行前查重、登记、运行及输出落盘：

```bash
python3 "$FUSION" run --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --check fixture --timeout 30 -- python3 -c "print('fixture observed')"
```

只接受参数数组，shell=False；不会按 shell 展开管道或通配符。需要脚本时先保存脚本再调用解释器。默认工作目录是案件目录，可显式 --cwd。命令和目录摘要用于防止同一检查下换命令误复用，实际参数不写入摘要；通过安全环境变量传凭证。脚本文件内容或工具版本变化仍需更新方法版本。

返回短回执；stdout、stderr、receipt 保存在 captures/CALL-id/，同时复制到不可覆盖的证据索引。大量输出不回灌给模型。退出码 0 进入 review；非零进入 failed；超时进入 unknown。启动失败进入 blocked。超时只停止启动的父进程，不代表子进程或远端动作已撤销。

原生 MCP 无法由这个 Python 包直接代理。按以下协议接入宿主：

1. `catalog --capability <id>` 找候选。当前宿主可导出真实工具清单时，传 `--inventory tools.json`，仅返回匹配项的实际名称和 schema。
2. 先按隔离协议登记实际工具上下文，再 `begin --workspace <registry> --session <session-id> --case <path> --check <key> --provider <provider-id> --tool <实际工具名> --context <已核对slot>`。
3. 仅 decision=execute 才调用 MCP。将 CALL-id 关联到宿主调用记录；provider 支持幂等键时可以使用该 ID，不得发明接口参数。
4. 实际保存完整返回结果，再 `record --workspace <registry> --session <session-id> --case <path> --attempt <CALL-id> --status review --summary <简明结果> --mcp-result result.json`。普通文件用可重复的 --artifact。MCP isError=true 或协议 error 强制记为 failed；分页、异步任务、截断仍需 Agent 按提供者协议判断，不能标为完整结果。
5. 读取足够证据后 `review --workspace <registry> --session <session-id> --case <path> --attempt <CALL-id> --verdict done --summary <结论与适用条件>`。可选择 failed/blocked；unversioned 结果还需 --valid-for。

工具清单格式：providers 数组，每项 id 对应 provider ID，tools 项使用真实 tools/list 的 name、inputSchema、可选 outputSchema；observed_at 标记观察时间。不存在的名称不能伪造为已接入。匹配成功只证明快照中存在接口，不证明健康、权限或目标连接正常；Agent 仍按当前宿主确认。宿主别名不符合候选名称时按实际接口人工绑定，不猜别名。

done 指该检查的完成条件已复核，阴性结果也可以 done；它不表示发现漏洞。复用前校验证据 hash、有效期及上游检查版本。failed、blocked、stale、evidence_invalid、dependency_changed 再执行要提供 --retest-reason 和可核对理由。目标/身份/方法变化应建新检查，不用重试理由掩盖不同条件。

## 中断与恢复

启动、压缩后恢复、切换案件时运行 resume；连续执行中按回执推进，阶段切换或状态不确定时再取新快照，不在每次工具调用前重读所有资料。

```bash
python3 "$FUSION" resume --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --max-chars 6000
python3 "$FUSION" resume --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --check fixture
python3 "$FUSION" query --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --kind checks --limit 10 --offset 0
python3 "$FUSION" query --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --kind notes --check fixture --limit 5
python3 "$FUSION" query --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --kind notes --target local-fixture --limit 5
```

恢复包包含目标/范围/约束、当前检查、相关笔记、未决调用、队列片段及省略计数。stored_status_counts 是存储状态，不能替代逐项证据复核。当前检查以外的记录按 --check 或精确 --target 查询；新增方法前查同目标的 checks 和 notes，复用已否定结论及限制条件。不同身份/版本下的阴性结论不可无条件推广。

遇到 running/unknown，先核对 captures/CALL-id、宿主调用记录或实际远端状态：

```bash
python3 "$FUSION" reconcile --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --attempt CALL-id --outcome observed --summary "已取回原调用结果" --artifact recovered-result.json
```

observed 进入 review；有证据证明未执行时使用 not_executed，之后才允许有理由重试。无法确认就保留未决状态，继续独立项，不以等待超时作为“未执行”的证据。重启不会自动释放未决调用。

脚本保证本地账本事务及同一检查最多一个未决调用，不能让任意外部服务具备 exactly-once。若宿主绕过 begin 直接调用 MCP，本包无法拦截；不宣称系统级强制执行。

## 阴性结论、假设与决策

```bash
python3 "$FUSION" note --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --check fixture --kind negative --text "本次条件下未观察到预期异常；覆盖仅限该样本" --evidence E-id
python3 "$FUSION" note --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --check fixture --kind refuted --text "对照证据否定此前假设" --supersedes N-old-id --evidence E-id
```

kind 为 fact / negative / refuted / hypothesis / decision / constraint / blocker。保存观察、证据、限制和简明决策，不保存隐藏推理。supersedes 保留旧记录供审计。全局 constraint 和当前检查笔记为必需上下文；超过预算时明确报错，先指定更小的工作项或按实际需要提高预算，不静默裁掉约束。

## 交付和成本控制

```bash
python3 "$FUSION" report --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE"
```

生成 report/ledger.md、report/coverage.json、state.json、events.jsonl、evidence/records.json、resume.md。它们是可重建视图，带事件版本；数据库才是事实来源。阶段结束或交付时导出，不每步重写全套文件。

fusion-report 另外编写 summary.md、report.md、findings.json 和必要的解释性覆盖说明。运行辅助程序不会编造漏洞，也不会覆盖 Agent 编写的 report.md。账本 completed 仅表示已登记检查都完成；完整任务是否覆盖全部适用面、技术结论是否有效，仍由主控和验证专项验收。

默认 6,000 字符是恢复/查询/目录响应的上限，不是总会话 token 上限。省略队列/全局笔记有计数，可分页；必需信息或单个 schema 超限报错。实际 token 取决于模型，宿主也可能仍加载全部工具定义；本包不能撤回已经进入宿主上下文的 MCP 大输出。优先使用服务自身的分页、过滤、导出能力。

账本更新和机械摘要不调用模型。CLI 可在同一个宿主 shell 调用中按实际依赖顺序组合，降低来回次数；复核仍需读取必要证据。不要为了机械落盘创建额外 Agent 或 LLM 总结任务。

现有纯文件案件不会自动迁移；不要对已有测试记录建空账本后直接重跑。先从原记录核对已完成/未决项与证据，再制定迁移映射。新运行协议适用于用 init 建立的案件。

已有 SQLite 案件使用 identify 和 bind 接入注册库，检查记录保留；同一会话不能暗中切换案件。完整经验沉淀、检索及可选向量命令见 [隔离与经验协议](scoped-memory.md)。
