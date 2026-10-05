# 分环节改造验收记录

日期：2026-10-06。选型和逐项落地见 [对照表](component-selection-2026-10-06.md)。

本轮完成代码与宿主接口改造，未执行新的模型靶场对照。旧模型 trace 仅用于校验离线评测器，不代表新版本实战成绩。

## 已验证行为

| 问题 | 本轮可观察结果 |
|---|---|
| 已选择路由但参数繁琐 | 当前会话的 execute 可省 route_id，仍须有本次 arguments+work；另一个会话不能借用 |
| 改了工具接口仍沿旧路由 | schema 变化会返回重新准备结果，准备动作不调用目标 |
| 重启后从别处开始 | 有效 next_check 优先；未决回执仍先对账，已完成检查不能绑定为下一项 |
| 历史材料占满上下文 | focus 限定工作集，按指针恢复长方法/证据，保留目标、范围、条件与前置证据 |
| 阶段产物没交出来 | checkpoint 自动生成 Markdown；deliver 生成并部分交付真实阶段报告，缺失文件如实列出 |
| 自动报告被误当成功 | 未复核观察仍为 review；partial 不补写 done，也不自动替用户完成验收 |
| CVE/OSV 状态被混淆 | REJECTED/withdrawn 明确不是可操作候选；受影响片段有省略计数与完整快照 |
| 只加载 Skill 或额度失败被算成功 | trace 审计区分 not_executed、infrastructure_blocked、executed_without_delivery、delivery_reported |

## 回归记录

- `python -X utf8 -m unittest discover -s tests -q`：178 项，175 通过、3 项因环境条件跳过，102.446 秒；启用本机 DSH SDK 接口测试。Python 中包含 Node 测试包装，不能把两种统计简单相加。
- 最后调整后的 `node --test tests/dsh-routing.test.mjs tests/dsh-runtime.test.mjs tests/dsh-schema.test.mjs`：35/35 通过，28.139 秒。覆盖真实 Python CLI、临时文件、回执落盘、DSH SDK schema、恢复 surface、隔离、MCP 路由绑定、实际写入和自动阶段交付。
- 节点/恢复 Python 相关回归：5+10 项通过。评测器拆分函数后再跑其 3 项相关测试。
- 交付文件集的 `validate_pack.py`：PASS；6 类任务、13 专项、28 具体方法、23 能力、13 组件，275 个本地链接有效。
- Skill frontmatter 校验：PASS。Windows 下校验器须使用 Python `-X utf8`。
- `sentrux gate .`：PASS，纳入全部新增文件；质量指标 5943→5941，复杂函数数量未增加、依赖环仍为原有 1 个、无新增超大文件。
- `sentrux check .`：未能执行自定义架构规则，项目没有 `.sentrux/rules.toml`。未把它记作通过，也未为过门禁新建空规则。

本地根目录的通配文档检查会扫到被 Git 忽略的旧 `work/agent-eval/reverse-upstream`，其中已有失效链接；正式包校验在由 Git 交付文件集构成的独立副本运行，没有删除或修改旧研究材料。

## 上下文对照

同一份本地可控案件、同一 6000 字符预算，比较标准 resume 与 focus resume。长历史样例包含 25 条无关已完成检查和 80 条历史笔记。两种视图选中同一个下一检查，完整目标/范围/条件与有效前置回执保持一致。

| 样例 | 标准视图字符 | focus 字符 | 减少 |
|---|---:|---:|---:|
| 短历史 | 3888 | 2882 | 25.9% |
| 长历史 | 5858 | 4417 | 24.6% |

这是固定样例的恢复 JSON 字符数，不是 token 计费、整场任务上下文或模型能力提升率。整条 DSH 恢复消息仍保留 8000 字符硬上限；必需约束不能在预算内装下时明确报错，不静默丢弃。

## 历史 trace 校验

- 旧额度不足样例：观察到 0 次子调用、2 个 QUOTA 结束原因，正确归类为 `infrastructure_blocked`。
- 旧执行样例：观察到 3 次子调用和 3 个带路由的回执声明，但没有交付，归类为 `executed_without_delivery`。
- 评测器仅导出错误代码与指标，不导出错误原文、工具参数或凭据。trace 声明还须与案件回执哈希核对，不能单独用来认证报告或判断“漏洞已经通过”。

使用方法：

```bash
python3 scripts/evaluate_dsh_trace.py /path/to/trace.jsonl --output /path/to/metrics.json
```

## 生效与回退

部署时同时更新整个 Skill 和对应 DSH 宿主模块，再重启实际使用的 profile。仅覆盖 SKILL.md 不会升级已复制到 profile 的代码。本轮没有修改本机用户全局 DSH 配置，也没有新增生产依赖或数据库迁移。

回退到 `99b66797eb6f04f9688605ce9dcd9ae8467ab10e` 的 Skill 与配套宿主模块即可；保留原案件目录，重新准备路由。未测的多模型纵深能力、其他 Agent hooks 和全量 MCP 服务健康情况仍是后续实测项。
