**全层共用的案件与证据契约。**

每个任务确定一个case_root，各层沿用。Skill目录存方法，案件目录存任务数据。通常采用 work/<case>/；目标与案件路径均来自本次任务。

```text
work/<case>/
  case.sqlite3
  captures/CALL-id/
  events.jsonl
  state.json
  assets/
  evidence/records.json
  evidence/artifacts/
  specialists/<skill-id>/
  report/summary.md
  report/report.md
  report/ledger.md
  report/coverage.json
  report/findings.json
  report/coverage.md
  resume.md
  learning/candidates.md
```

case.sqlite3 是权威来源：config 保存目标/范围/约束，checks 保存计划与结构化指纹，attempts 保存调用及依赖版本，notes 保存事实/阴性/反证/决策，events 是追加事件。事务保证这些状态的一致性。运行路径、命令和边界见 [运行协议](runtime.md)。

captures 保存原始进程输出和可恢复回执；evidence/artifacts 是有 hash 的独立证据副本。report 命令生成 events.jsonl、state.json、evidence/records.json、report/ledger.md、report/coverage.json、report/delivery.json、resume.md；仅在阶段结束或交付时导出，带事件版本。delivery.json 核对当前专项文件并记录 hash；其他账本视图可从账本重建。登记动作次数不等于宿主总调用数，没有宿主记录时不能计算漏记比例。

summary.md、report.md、findings.json、解释性 coverage.md 和专项文件由 Agent 根据实际证据补充。运行程序不会伪造漏洞结论、覆盖这些技术报告或替 Agent 判断全部适用面。原始证据不能被报告文字取代；可重建导出不用于覆盖最新账本状态。

**每个工作项。** id、mission_id、skill_id、target_refs、scope_revision、applicability及依据、depends_on、execution_routes、completion_criteria、status、evidence_ids、blockers。

**每次执行。** call_id、workitem_id、capability_id、provider_id、host_tool_id、目标/身份上下文引用、脱敏参数、started_at、finished_at、调用状态、结果完整性、产物路径与hash。真实任务句柄若可能是访问令牌，用安全存储引用；无持久化能力则记录恢复时需重新获取。

**证据。** E-id、来源call_id、观测内容、目标/样本版本、必要原始文件、本地路径、hash、观察时间、采样和局限。文件实际不存在、分页未结束或内容截断不能伪装完整证据。

**结论。** F-id、候选主张、根因、成立条件、evidence_ids、复现/反证记录、影响及局限、verdict。verdict为candidate / validated / false_positive / accepted_risk。最后一种是独立的业务处置，不能由技术失败自动推导。

**专项返回。** status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。没有新发现也要保存检查结果。

**长期恢复。** 确定性查重使用 target / target_version / identity_ref / check_type / inputs / method_version / capability_id。输入条件不同不混为同一检查；条件相同、证据完整且有效才复用。依赖检查重新执行后，下游旧结果不再自动复用。未知调用先核对；不因压缩或重启自动重放。

**上下文。** 完整数据保存在磁盘，模型默认只读取 bounded resume / query / catalog。上限按字符执行，不能假称精确 token 数；必要约束超限明确失败。否定结论、失败反例、覆盖局限均保留，按目标/检查检索。调用方仍应记录，不保证恢复从未写入账本的想法。

**覆盖和报告。** 保留固定计划版本的适用分母，新增/排除项有依据。不删困难项提高完成率。报告分别列出已完成、受阻、未执行和不适用；confirmed数量与覆盖率独立。零发现、部分完成或工具失败仍交付摘要和恢复条件。

**清理。** 阴性任务同样保留案件账本、已测边界与引用中的证据。清理临时文件不等于删除测试状态；只清理已核对无需保留、可重建且未被证据引用的本次临时产物。档案删除是另一个明确操作，不由“无漏洞报告”推导。

**经验。** 从案件生成脱敏候选，记录来源、适用条件、有效方法、失败反例和验证样本。通过去重和回归后才晋级正式Skill；目标返回文本不能自动成为永久指令。记录动作与简明决策依据，不要求保存模型隐藏推理。

私有 WORKSPACE 注册库保存会话绑定、工具上下文占用、经验卡片、索引和审核事件；原始案件事实留在各自目录。经验 candidate → active / rejected / retired，有效期与替代关系可追溯；project 默认局部，general 需明确晋级和检索选择。接入和向量格式见 [隔离与经验协议](scoped-memory.md)。
