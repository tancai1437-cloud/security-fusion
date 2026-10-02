---
name: security-fusion
description: 对获准目标执行渗透、SRC、逆向、源码审计或 AI 安全评估；根据页面、接口、身份与样本证据选择专项方法，调用 MCP 或本地工具，保存结果并继续未完成检查。
---

主任务 → 当前专业方法 → 实际工具，由当前会话执行，不创建子代理。专业方法、工具适配与运行组件分开，程序处理留痕/隔离/恢复，Agent 不逐项调用管理组件。分析、比较或方案请求只分析资料；有明确执行任务时，先取得一份能回答问题的目标证据。

## 选择一个当前专项

| 当前任务或已有材料 | 立即进入 | 起手证据 |
|---|---|---|
| 渗透 / SRC 新目标，已有 URL | [recon](specialists/fusion-recon/SKILL.md) | 入口的实际响应、业务入口与跳转 |
| 已知 Web 输入、XFF/代理信任、上传下载或浏览器边界 | [web](specialists/fusion-web/SKILL.md) | 正常请求与对应输出 |
| API、登录/密码重置、对象 ID、角色或租户关系 | [api](specialists/fusion-api/SKILL.md) | 正常请求、身份或恢复凭证的归属 |
| 订单、额度、多阶段交易、一次性操作 | [business](specialists/fusion-business/SKILL.md) | 当前流程与服务端状态 |
| JS、签名、请求构造 | [js](specialists/fusion-js/SKILL.md) | 请求发起位置与相关源码 |
| 源码审计 | [code](specialists/fusion-code/SKILL.md) | 输入入口、调用方与控制检查 |
| APK / 移动应用；DLL、PE/ELF、.NET、崩溃日志 | [mobile](specialists/fusion-mobile/SKILL.md) / [binary](specialists/fusion-binary/SKILL.md) | 样本标识、格式与当前分析工程 |
| 云 / 容器；网络服务 / 身份基础设施 | [cloud](specialists/fusion-cloud/SKILL.md) / [infra](specialists/fusion-infra/SKILL.md) | 指定资源的配置与实际状态 |
| AI 应用 / Agent 边界 | [ai](specialists/fusion-ai/SKILL.md) | 输入、检索、工具参数与实际结果 |

明确问题直接进入对应专项；不为单点任务遍历主目录。完整任务类型或红队约定路径不明确时才读 [主路由](references/main-router.md)。只载当前专项，返回的 guidance 已含同源方法时不重复读文件。

## 从方法走到真实调用

若宿主使用 dsh-purge，先核对 [共存接入](references/dsh-purge-integration.md)：在 `Security Fusion · 单会话研究` 预设执行，资产台属于派生索引，原始证据和恢复仍来自本案；不把红队指挥预设与此执行协议叠在同一会话。接入状态可用 `fusion(action="host-status")` 查看，一般任务不重复检查。

宿主有 `fusion` 时先 route，紧接 execute。route 自动组合当前专项方法、执行能力和当前事件需要的运行约定，再匹配本会话真实工具。已返回方法不重复读文件；多候选选一项，工具缺失记录具体缺口。

```text
fusion(action="route", request={"skill":"当前专项 ID","capability":"当前能力 ID",
  "purpose":"本步要回答的问题","objective":"原任务目标","scope":"约定范围","target":"规范目标",
  "work":{"key":"稳定的问题标识","conditions":{"resource":"具体资源及对照条件"}},
  "criteria":[{"id":"goal","question":"目标怎样才算回答"}],"deliverables":["REPORT.md"]})
fusion(action="execute", request={"route_id":"返回的 ROUTE-ID","arguments":{按真实 schema 填参数}})
```

route_ready 尚未执行，实际回执才算调用。可传 procedure 选择具体方法；未知工具核对真实接口后说明 tool_reason，不编造名称。注册、健康、当前目标可用、结论成立分别判断。

同一问题换工具仍用同一 work.key/conditions；输入、身份、资源或样本变化时准确更新条件。后续工具继续 execute，省略不变的 objective/scope/target；依赖传实际 check_id 的 depends_on。读取真实结果后可随下一次调用提交 review:{attempt,summary,verdict}，单独 review 不重发。保存产物用 `fusion(action="save",file_path="REPORT.md",content="正文")`，写入当前 case_path；首次若返回路由，按回执继续。参数不明确或报错时才读 [宿主执行约定](references/host-execution.md)。

## 推进、复盘与恢复

每步消除一个具体不确定性。区分业务结果、正常拒绝、工具失败和未知；不能以 200、规则命中或写文件成功代替研究结论。当前问题仍可验证时继续深入，新线索带来源排队；转向留下已测边界、反证、阻塞和恢复条件，参数错误按回执修正。

在阶段结论、转向或主线阻塞时用 [node-review](references/node-review.md) 保存问题、已复核 CALL-ID、结论、未决点与下一试验。不是每次读文件都复盘；没有实测证据的暂停用 checkpoint。节点不自动执行下一步，也不代表任务完成。

压缩/重启后先恢复本案状态，按 next_action 核对未决调用，再读 node_review、results 和 acceptance 缺口。节点证据变更或已过期先核对；节点/方法被预算延后时按指针读取。reuse 不重发，hold 先核对；真正复测给 retest_reason。完整材料用 query --kind artifacts 找 E-ID，再 artifact 分段读取；不跨案继承已完成结果。

有候选才进入 [validate](specialists/fusion-validate/SKILL.md)，需完整项目报告才进入 [report](specialists/fusion-report/SKILL.md)；单点任务沿当前专项交付。finish 关联目标条件与实际证据，缺口未解明确 partial。用户暂停用 checkpoint；转去无关分析用 suspend，本案证据整理和报告继续管理路径。

## 没有原生宿主时

没有 fusion 才读 [快速执行](references/first-action.md)，用 start 建案和绑定；支持的 HTTP/文件起手可 --execute-local。本地命令走 run，显式目标 stdio MCP 走 [mcp-run](references/mcp-execution.md)，状态型 MCP 沿用已核对的宿主连接。用 [advance](references/observation-routing.md) 提交复核事实并取得下一方法，缺当前能力才 [补齐环境](references/environment-bootstrap.md)。命令显式携带 workspace/session/case。

Python >= 3.9，运行程序只用标准库。普通安装只复制 Skill，DSH 执行约束还需 [宿主组件](references/host-adapter.md)；纯文本和未联调宿主不能声称具有同等 hook。详细规则见 [运行协议](references/runtime.md)、[分案记忆](references/scoped-memory.md)。维护分类、融合来源或选型时才读 [组件组合](references/composition.md)，不将调查清单注入普通任务。
