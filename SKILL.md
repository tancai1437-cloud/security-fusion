---
name: security-fusion
description: 对获准目标执行渗透、SRC、逆向、源码审计或 AI 安全评估；根据页面、接口、身份与样本证据选择专项方法，调用 MCP 或本地工具，保存结果并继续未完成检查。
---

主路由 → 当前专项的方法 → 实际工具，由当前会话执行，不创建子代理。分析、比较或方案请求只分析资料；有明确执行任务时，先取得一份能回答问题的目标证据。

## 选择一个当前专项

| 当前任务或已有材料 | 立即进入 | 起手证据 |
|---|---|---|
| 渗透 / SRC 新目标，已有 URL | [recon](specialists/fusion-recon/SKILL.md) | 入口的实际响应、业务入口与跳转 |
| 已知 Web 输入、上传下载或浏览器边界 | [web](specialists/fusion-web/SKILL.md) | 正常请求与对应输出 |
| API、登录、对象 ID、角色或租户关系 | [api](specialists/fusion-api/SKILL.md) | 有效身份下的真实请求与对象归属 |
| 订单、额度、多阶段交易 | [business](specialists/fusion-business/SKILL.md) | 当前流程与服务端状态 |
| JS、签名、请求构造 | [js](specialists/fusion-js/SKILL.md) | 请求发起位置与相关源码 |
| 源码审计 | [code](specialists/fusion-code/SKILL.md) | 输入入口、调用方与控制检查 |
| APK / 移动应用；原生二进制 | [mobile](specialists/fusion-mobile/SKILL.md) / [binary](specialists/fusion-binary/SKILL.md) | 样本标识、格式与当前分析工程 |
| 云 / 容器；网络服务 / 身份基础设施 | [cloud](specialists/fusion-cloud/SKILL.md) / [infra](specialists/fusion-infra/SKILL.md) | 指定资源的配置与实际状态 |
| AI 应用 / Agent 边界 | [ai](specialists/fusion-ai/SKILL.md) | 输入、检索、工具参数与实际结果 |

明确问题直接进入对应专项；不为单点任务遍历主目录。完整任务类型或红队约定路径不明确时才读 [主路由](references/main-router.md)。只载当前专项，返回的 guidance 已含同源方法时不重复读文件。

## 从方法走到调用

1. **新任务**读 [快速执行](references/first-action.md)。HTTP 入口用 `start --execute-local` 合并建案、会话绑定和第一次读取；已有材料直接登记对应检查。Agent 维护案件与参数，用户不用逐步填表。
2. **选工具**：现成本地命令走 `run`；已建立显式目标 stdio 配置的 MCP 走 [mcp-run](references/mcp-execution.md)，程序完成连接、实际工具查询、调用及证据落盘。依赖当前浏览器/工程的 MCP 用宿主已连接工具，按 [执行路由](references/execution-router.md) 核对上下文。只查当前能力，缺项才 [补齐环境](references/environment-bootstrap.md)。
3. **读结果并推进**：取得输出后先判断实际响应；用 [advance](references/observation-routing.md#简化入口advance) 一次提交上一项复核结论与新事实，程序补齐来源和证据引用，返回下一具体方法。继续调用该方法所需工具。未匹配的问题按当前专项生成具体检查，不强凑标签。

每次下一步应回答一个明确问题，并给出可核对输出。连续准备却没有消除阻塞时，执行当前可用检查或转到独立可执行项。正常拒绝、登录壳、工具错误和结果未知分别处理；不能靠重复同一失败调用制造进展。缺身份只阻塞依赖身份的检查。

## 保留结果与恢复

运行命令显式携带 `--workspace / --session / --case`。同项目不同目标分案；压缩或重启后 `resume`，先处理未决调用与待复核证据；换会话按 [隔离协议](references/scoped-memory.md) 交接。`reuse` 不重发，`hold` 先核对。成功返回不等于检查完成，复核由当前 Agent 根据证据判断。

原始输出自动保存，阶段结束再整理专项产物，经 [validate](specialists/fusion-validate/SKILL.md) 核对并由 [report](specialists/fusion-report/SKILL.md) 交付已测、未测、受阻与依据。账本完成不代表整个评估完成。经验按需检索，阶段结束再审核沉淀；恢复默认最多 6,000 字符。详细命令按需查 [运行协议](references/runtime.md)。

Python >= 3.9，辅助程序只用标准库。Skill 文本不拦截绕过适配器的宿主调用；原生 MCP 与直接 stdio 连接的上下文不能互认。方法与许可取舍见 [融合记录](references/upstream-decisions.md)。
