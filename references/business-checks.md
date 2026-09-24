# 业务线索到当前检查

只在 API / business 当前事实命中时使用。具体方法由 [procedures.json](../manifests/procedures.json) 返回，作为检查快照落盘；这里说明前提和输入，不再维护第二份方法全文。不加载上游案例库，不设固定假设数量。

| 已观察特征 | 方法 | 必要前提 features | 必要 inputs |
|---|---|---|---|
| `api.role-operation`：实际操作存在角色限制 | `function-boundary` | `identity.verified`、`roles.controlled`、`operation.permitted` | `identity_refs`、`request_ref`、`operation`、`rule_ref`、`scope_ref` |
| `auth.password-reset`：已获得正常恢复请求 | `reset-binding` | `accounts.controlled`、`operation.permitted` | `identity_refs`、`request_ref`、`challenge_ref`、`state_ref`、`operation`、`scope_ref` |
| `business.transition`：已确定一条转换及其前置条件 | `order-transition` | `identity.verified`、`business.fixture`、`operation.permitted` | `request_ref`、`state_ref`、`fixture_ref`、`rule_ref`、`operation`、`scope_ref` |
| `business.single-use`：已确认一次性/幂等规则 | `single-use-effect` | `identity.verified`、`business.fixture`、`operation.permitted` | `request_ref`、`state_ref`、`fixture_ref`、`rule_ref`、`operation`、`scope_ref` |

对象归属检查继续复用 `api.object` → `object-boundary`，不新增同义方法。具体转换/幂等事实出现后，泛化 `business-transition` 不再重复安排；具体分支缺前提时保留阻塞，不能用泛化项绕过。

`roles.controlled` / `accounts.controlled` 表示两个测试角色/账号归用户控制，`identity_refs` 为 2–8 个不同安全引用。`business.fixture` 表示已有可恢复的测试数据，`fixture_ref` 标识具体对象组及起始条件。`operation.permitted` 和 `scope_ref` 来自现有任务范围，不是新增权限或每步要求重新批准；程序检查字段存在，语义与权限仍须由 Agent 核对。未满足前提可先读已有流量或源码，不伪造 feature。

inputs 存放当前案件的短引用；请求、状态、业务规则和既有授权说明通过这些引用查原始证据。凭据仅放私有材料，`challenge_ref` 不能填写令牌值。字段值、受控对象、逻辑操作标识或身份条件改变时更新 inputs，避免错误复用旧检查。未变化且已复核的检查继续走现有查重。

例如已有正常订单请求、可恢复数据和允许测试该转换的任务范围时，Agent 生成以下引用文件（示意，必须换为真实案件引用）：

```json
{
  "request_ref": "E-normal-order-request",
  "state_ref": "E-order-start-state",
  "fixture_ref": "controlled-order-pair-v1",
  "rule_ref": "E-required-approval",
  "operation": "submit-for-fulfilment",
  "scope_ref": "case-scope/order-fixture"
}
```

随后用已有 `advance --check ... --feature business.transition --feature identity.verified --feature business.fixture --feature operation.permitted --inputs ...`，由原始检查继承目标、版本与证据。其他业务分支使用表内特征即可。恢复流程可保持匿名调用，不需要先伪造一个登录身份。

四个新增方法都通过 `http.request` 匹配当前真实工具：已有宿主 MCP 用 begin → 调用 → record；显式目标 stdio 配置用 [mcp-run](mcp-execution.md)。`operation` 是方法的业务含义，不是 MCP 工具名或通用参数；按当前工具实际 schema 构造请求。账号 A/B 的切换必须保留实际身份，不能把同一会话标签冒充两种身份。

一个方法通常需要正常对照、变体和状态读取。宿主路径可在当前 attempt 中收集这些材料后一次 record；中途状态未知先记录 unknown 并核对。stdio 路径只有在实际工具支持所需完整操作及证据返回时，才可用一次 mcp-run 覆盖方法；工具只支持单请求时改用宿主协议收集对照，不反复用同一检查 ID 更换参数调用，也不把首次返回当作完整验证。账本的 attempt 数不等于其中包含的 HTTP 请求数，报告以原始回执核对。

判断顺序：先核对正常对照 → 再核对期望拒绝或幂等结果 → 排除异步未完成、缓存及身份失效 → 保存当前条件下的结论。目标事实、已测结果继续留在各自案件；来源方法不会把历史案例写入目标账本。

来源与许可取舍见 [WooYun 融合记录](upstream-decisions.md#wooyun-methods)。这些分支是针对当前运行协议编写的方法，不含上游案例正文、统计表或 payload 库。
