# 从第一项真实检查开始

适用于新任务。当前 Agent 选择工具和参数；程序负责登记、隔离、查重与捕获，不会自行判断测试面或调用模型。已有案件直接 resume；换会话先 handoff，命令见 [运行协议](runtime.md)。

**DSH 已有原生 fusion 工具时，使用主入口的 execute(request)；本文 CLI 配置步骤不需要再做。** 首次 execute 合并建案、方法校验、宿主真实调用和回执捕获；后续继续 execute，并传上一结果的语义 review。不要为了遵守本文先读取实现源码或制作工具清单。

## 选一项能拿到证据的检查

只取当前专项：读专项文件或 `catalog --skill <id>` 的行动卡，二者选一。尚未读取时，start 不追加本地程序，直接从返回的 guidance 获取方法后再 run。行动卡由专项原文生成，不要求重复读文件；其中 completion 是本阶段完成条件，不表示一次调用就应完成整个阶段。确定“这一次调用要回答什么、用什么输出判断”，然后选择已有工具：

| 已有材料 | 第一份业务证据 | 随后的决定 |
|---|---|---|
| 获准 URL，缺乏基线 | 对指定入口的正常读取：状态、跳转、页面/接口摘要，保留原始输出 | 根据实际页面或响应选择 Web/API/JS 面；不把状态码当漏洞 |
| 已有请求/响应或问题线索 | 核对该请求的目标、身份、参数及对应正常行为 | 只补验证假设所缺的对照，不重新跑资产发现 |
| 源码 | 当前入口/调用路径的实际文件与行号 | 跟进具体输入与控制检查，避免先生成全仓审计清单 |
| APK/二进制 | 文件格式、架构或已打开工程中与用户问题相关的函数 | 按样本事实选择后续静态/动态工具 |

新任务可先登记一个检查；这不表示完整任务只做一个检查。实际结果触发后续工作，沿用同一案件、规范目标和身份引用。

## 一次启动并执行本地检查

新 Web/SRC 任务只有一个明确 HTTP(S) 入口时，可用更短的 entry 模式；targets 必须包含该入口，config 仍记录本次范围和约束：

```json
{
  "project": "actual-project",
  "targets": ["https://authorized.example/"],
  "config": {"mission_id": "src", "objective": "检查已授权入口", "scope": "仅用户约定入口与测试条件", "constraints": ["只读起手"]},
  "entry": "https://authorized.example/"
}
```

```bash
python3 "$FUSION_ROOT/scripts/fusion.py" start --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --input task.json --execute-local
```

程序选择 fusion-recon → web.crawl → 当前 curl，执行一次精确入口的匿名读取，不跟随跳转；有凭据的请求和其他检查仍按实际工具处理。没有 curl 时返回候选和 planned_not_executed，不伪造调用。HTTP 错误响应仍需语义复核，成功退出不等于完成。`entry` 和下面的显式 `check` 二选一。首份证据 review 后，优先用 [事实路由](observation-routing.md) 生成下一项。

**二进制起手**也可用同一 entry 命令：将 targets/entry 改为同一规范绝对文件路径，mission_id 用 reverse（或含该样本的 pentest/redteam）。程序绑定样本 SHA-256，运行本包只读 PE/ELF/CLR profile；不会执行样本。后续按 [二进制专精](binary-depth.md) 分流原生、托管和 unknown。其他材料或已有明确检查时沿用下面的格式。

使用已安装的实际脚本路径，生成一个 task.json，放在案件目录之外。下列结构仅示例，目标、输入、版本与完成条件由当前任务事实替换：

```json
{
  "project": "actual-project",
  "targets": ["canonical-target"],
  "config": {
    "mission_id": "audit",
    "objective": "回答当前用户的具体问题",
    "scope": "用户指定的源代码目录与只读范围",
    "constraints": ["不写入目标文件"]
  },
  "check": {
    "key": "first-observation",
    "target": "canonical-target",
    "target_version": "unversioned",
    "identity_ref": "current-local-user",
    "check_type": "source-entry-read",
    "inputs": {"path_ref": "actual-source-path"},
    "method_version": "source-read-v1",
    "capability_id": "code.inspect",
    "skill_id": "fusion-code",
    "purpose": "取得指定入口的真实代码与位置，据此选择下一条调用路径",
    "depends_on": []
  }
}
```

```bash
python3 "$FUSION_ROOT/scripts/fusion.py" start --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --input task.json --timeout 30 -- <实际可用程序> <参数>
```

`WORKSPACE` 是同一执行环境共享的私有注册库，`SESSION` 是当前宿主/会话唯一 ID，`CASE` 是本目标的新案件目录；都由 Agent 维护，不让用户逐步填表。数据留在安装目录之外。命令参数必须对应 check 的目标、身份与 inputs；程序不独立验证任意程序的网络范围，不要把不同动作合并成一个含糊检查。

start 自动复用已有注册库，建立新案件、绑定会话、登记这项检查；追加本地程序时通过既有 run 流程真正执行命令。stdout/stderr/回执落盘，返回 case_id、check_id、guidance、execution 与捕获位置。guidance 提供本专项的方法、完成条件、产物路径，以及本检查能力的输入/输出要求。plan 返回本批首项的方法；resume 返回当前实际需要处理项的方法。不先跑 catalog、workspace-init、init、bind、plan、resume 六组准备命令。只填写当前检查，不编写完整测试计划。

- 已有案件不自动覆盖：恢复用 resume；修复启动中断时，可 identify 核对后给 start 加 `--expect-case <原ID>`，但配置、绑定和会话仍需一致。
- 有历史文件却没有账本时拒绝创建空账本，防止把已测任务当新任务；按运行协议迁移。
- `--` 后是参数数组，不展开管道或重定向；复杂读取先保存小脚本。没有可用程序时记录缺项，不能把打印成功当真实执行。
- 阅读返回的 captures 中必要片段。成功退出只是 review；真实达到 purpose 才 review 为 done。unversioned 检查须按证据适用时效给 `--valid-for`。
- 首项的代码、参数、工具版本改变时更新 inputs/method_version；不是为了避免查重而换 key。

## 当前检查必须用 MCP 时

同一 start 命令不追加本地程序，返回 planned_not_executed。已经安装且显式携带目标的 stdio MCP 用 [mcp-run](mcp-execution.md)，一次完成连接、查询真实工具、调用、登记与捕获。配置由 Agent 根据当前安装生成一次并复用。依赖当前页面/工程的 MCP 使用宿主已有连接，按 [执行路由](execution-router.md) 完成上下文核对与 begin → 宿主调用 → record。只补当前所缺能力，不重复发现全库。

## 拿到结果之后

用简明记录保存“观察到了什么、支持/否定什么、还有什么缺口”。优先 [advance](observation-routing.md#简化入口advance) 合并原检查复核与下一方法选择，来源、版本和证据引用由程序补齐。未匹配的明确检查才手工 plan。每份观察只涉及一个资源和身份条件。同目标有历史时 query 指定目标/检查，复用已有结果。不在每一步重读 Skill、重新建案或生成全套报告。方法受阻才检索经验，阶段结束再导出报告与提炼经验。范围、预算或明确阻塞决定停止；不能用增加工具调用次数替代有效证据。
