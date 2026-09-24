# 从已观察事实生成下一项检查

适用于首份目标证据已经捕获之后。当前 Agent 从证据中识别业务特征；程序按明确条件选择方法、生成检查项，并匹配已有本地程序或当前宿主已验收的 MCP。路由不独立理解响应内容。显式目标 stdio MCP 可用 [mcp-run](mcp-execution.md) 真正调用并保存结果，其他 MCP 仍由宿主调用。

## 简化入口：advance

读完实际输出后，优先使用下面的合并命令。`CHECK` 是刚刚检查的明确 ID；目标、版本、来源与 evidence_ids 自动取自它的当前有效证据，无需模型再写完整 observation.json。`--summary` 表示 Agent 已对原检查的完成条件作出判断，不是程序自动认定成功。

```bash
python3 "$FUSION_ROOT/scripts/fusion.py" advance \
  --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" \
  --check "$CHECK" --summary "原始响应已核对；这里只确认入口基线，发现真实 API 操作" \
  --valid-for 600 --feature api.operation --resource /api/observed-operation
```

只有真实观察到的特征才传 `--feature`，可重复。`--resource` 不传则继承原检查资源；切换测试身份用 `--identity`，方法所需对象、请求或字段引用才另传 `--inputs inputs.json`。完整特征表见下文，当前专项也有常用分支。

返回一个 `selected` 具体方法及工具选择，随后直接执行，不再打开同一个专项。仅当匹配内置本地读取适配器时，加 `--execute-local` 可同次执行。已有来源 done 时可以省略 summary；review 状态必须先给复核结论。运行中、结果未知、过期或证据损坏均不能借此绕过处理。有效复核会独立保存，后续路由失败可修正输入后重试，不必重跑原检查。

已有直接 stdio 适配配置时，加 `--mcp-profile "$MCP_PROFILE"`，路由按当前能力返回配置中的具体工具与 `mcp_preflight_required`，接着用 mcp-run 执行；配置中的命令和环境变量不会回灌上下文。此状态不等于 ready，实际调用前仍查询当前连接。`--execute-local` 不会隐式执行 MCP。

所选适配器的工具名与配置路径随路由事件落盘。resume 恢复同一检查时附上短引用，避免压缩后重新猜工具；这是历史选择提示，执行仍做实时核对。

需要精确选择部分证据或兼容旧客户端时，继续使用下面的完整 route 接口。

## 一次路由

每份观察只描述一个规范目标、资源和身份条件。下面是格式示例，引用必须替换为当前案件的真实值；JSON 由 Agent 生成，不让用户填写：

```json
{
  "target": "canonical-target",
  "resource": "observed-resource-or-endpoint",
  "target_version": "unversioned",
  "identity_ref": "controlled-test-role",
  "source_check": "CHK-current-reviewed-observation",
  "evidence_ids": ["E-current-captured-evidence"],
  "features": ["api.object", "identity.available"],
  "inputs": {"request_ref": "reference-to-the-observed-normal-request"}
}
```

```bash
python3 "$FUSION_ROOT/scripts/fusion.py" route --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --input observation.json --execute-local
```

有当前 Agent 的已验收 MCP 索引时，加 `--environment "$ENVIRONMENT" --agent dsh --instance "$INSTANCE"`；OpenCode/Pi 使用各自名称与真实实例。只查命中能力，返回实际工具名/schema；过期或别的宿主实例不能沿用 ready。

- `selected`：当前问题、具体步骤、判定要求与结果分支。按它执行，不再从主目录逐层找同一个专项。
- `check_id/check`：已经登记的下一项；不需另写 skill_id、capability_id、method_version 或再 plan。
- `execution=local_callable`：当前存在且具备固定适配器的程序。`--execute-local` 会经原 run 实际执行并落盘；退出码 0 仍只是 review。目前固定适配器只含精确入口的匿名 HTTP 读取，以及绑定本地文件的限量源码读取。
- `execution=mcp_host_call_required`：核对目标/身份上下文，再 begin → 实际宿主工具 → record/review。返回路由不等于已经调用。
- `execution=tool_selection_required`：只有未验收候选；使用合适的现成宿主工具，或接通当前所需能力，不能宣称工具已运行。
- `execution=evidence_review_required`：当前候选优先复核已有证据；需要补新调用时再登记具体缺口。
- `decisions`：命中、缺前提、被现场事实排除、已测和未决分支。`unplanned` 只是候选，仅 `check_id` 顶层指定项被本次登记。没有新可执行项不能推导任务完成。

高优先级分支缺身份、受控对象或工具时，可以选择独立可用分支；不把所有候选一次性塞进计划。`next_on` 是读完真实结果后的分支提示，不是程序已经观察到的事实。

## 用什么事实路由

只标记有证据或用户已提供前提支持的特征，不根据页面关键词猜测。程序验证证据存在、未变、来自同一目标/版本的当前已复核检查；语义是否成立仍由 Agent 判断。

| 已观察事实 | features | 分流 |
|---|---|---|
| 指定 HTTP 入口 | `http.entry`；已有基线另标 `baseline.captured` | 入口基线，已捕获时不再安排 |
| 统一登录壳、认证拒绝 | `http.login-shell` / `http.auth-required` | 真实请求定位 / 身份前提 |
| 实际接口、GraphQL 操作、WS 消息 | `api.operation` / `api.graphql` / `api.websocket` | 请求与操作边界梳理 |
| 带对象归属的接口 | `api.object` | 有效身份和受控对象齐全后核对对象边界 |
| 实际角色受限操作、密码恢复请求 | `api.role-operation` / `auth.password-reset` | 角色边界 / 恢复凭证绑定，前提与输入见 [业务检查](business-checks.md) |
| 文件上传、下载或分享 | `file.upload` / `file.download` / `file.share` | 文件归属与实际处理 |
| 文本、搜索、模板输入 | `input.text` / `input.search` / `input.template` | 进入业务响应后确认处理/输出上下文 |
| URL 输入、Webhook | `input.url` / `integration.webhook` | 浏览器/服务端/异步来源判定 |
| 订单、额度、多阶段流程 | `business.order` / `business.quota` / `business.workflow` | 服务端状态和业务不变量 |
| 已确定的转换、一次性操作规则 | `business.transition` / `business.single-use` | 具体转换 / 幂等效果；不再重复安排泛化业务检查 |
| 脚本、请求构造函数 | `js.bundle` / `js.request-builder` | 请求链路提取 |
| 浏览器跨源、缓存 | `browser.cross-origin` / `browser.cache` | 真实浏览器边界 |
| XFF / 代理信任路径 | `http.entry` + `http.proxy-trust` | [三组真实请求及服务端决策对照](proxy-trust.md) |
| 源码、APK、未分类样本 | `code.source` / `sample.apk` / `sample.binary` | 对应材料专项；二进制先只读 profile |
| 已有原生 / 托管 profile | `binary.profiled` + `binary.native` / `binary.managed` | [函数 / 类型与 IL 分流](binary-depth.md)，需 inputs.question |
| 已保存崩溃报告 | `crash.log`；分类后为 `crash.classified` | 日志分类 → 复现；需受控样本和构建/失败输入/阴性对照引用 |
| 云配置、IaC、集群 | `cloud.config` / `cloud.iac` / `cloud.cluster` | 静态与运行态条件分离 |
| 网络服务、身份基础设施 | `network.service` / `identity.infrastructure` | 具体服务与控制关系 |
| AI 工具或检索链 | `ai.tools` / `ai.retrieval` | 真实工具/数据边界 |
| 有原始依据的候选问题 | `candidate.observed` | 优先复核候选 |

前提特征：`identity.available` 表示已提供测试身份，`identity.verified` 表示当前身份已验证有效，`objects.controlled` 表示有受控对象对照，`response.business` 表示响应已进入真实业务处理。存在登录壳时，不能仅添加后者强行绕过判定。

业务分支另使用 `roles.controlled`、`accounts.controlled`、`business.fixture`、`operation.permitted`，分别要求受控角色、受控恢复账号、可恢复测试数据和已有任务范围内的操作。它们是 Agent 对现有前提的声明，不是程序自动授予权限；具体引用见 [业务检查](business-checks.md)。正常恢复页面不应因未登录被误标为统一登录壳。

对象/文件检查的 inputs 需含 `identity_refs`、`object_refs`（各 2–8 个不同安全引用）和 `operation`；输入检查需 `request_ref`、`parameter`；业务流程需 `state_ref`、`operation`。其他会改变测试条件的字段、参数、方法和身份同样放 inputs；不要省略后让不同检查碰撞。不得写入凭据值。

## 结果与恢复

实际调用后先读原始证据，review/note 保存判断；只有新增且有依据的事实才再次 route。同输入产生同一指纹，已测项跳过，未决项先复核；对象/身份/输入/方法版本改变产生不同检查。现有旧版人工检查的语义等价性仍需 Agent 核对，不能靠换 key 绕过查重。

路由事实与决定写入案件事件；具体方法随检查保存快照，安装包更新不会改写在途方法。resume 只返回一份该方法、最近相关路由摘要和事件查询位置。摘要标明是历史决定，以当前检查状态为准。较多决定分页查事件，不恢复整套资料；默认上限 6,000 字符，自动本地执行提前预留回执空间。

这些方法是当前明确支持的分支，不代表穷尽所有漏洞类别。未匹配的实际问题继续按专项证据判断生成 plan，并把缺少的方法作为改进输入；不能为了命中规则伪造 features。
