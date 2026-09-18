**全层共用的案件与证据契约。**

每个任务确定一个case_root，各层沿用。Skill目录存方法，案件目录存任务数据。通常采用 work/<case>/；目标与案件路径均来自本次任务。

```text
work/<case>/
  scope.md
  plan.json
  events.jsonl
  state.json
  timeline.md
  workitems.md
  assets/
  evidence/records.json
  evidence/artifacts/
  specialists/<skill-id>/
  report/summary.md
  report/report.md
  report/findings.json
  report/coverage.md
  resume.md
  learning/candidates.md
```

scope是范围来源；plan是本版计划；events保存追加执行事件；state与workitems为可重建视图；timeline追加可读过程。报告由证据和覆盖派生。原始证据不能被报告文字取代。

**每个工作项。** id、mission_id、skill_id、target_refs、scope_revision、applicability及依据、depends_on、execution_routes、completion_criteria、status、evidence_ids、blockers。

**每次执行。** call_id、workitem_id、capability_id、provider_id、host_tool_id、目标/身份上下文引用、脱敏参数、started_at、finished_at、调用状态、结果完整性、产物路径与hash。真实任务句柄若可能是访问令牌，用安全存储引用；无持久化能力则记录恢复时需重新获取。

**证据。** E-id、来源call_id、观测内容、目标/样本版本、必要原始文件、本地路径、hash、观察时间、采样和局限。文件实际不存在、分页未结束或内容截断不能伪装完整证据。

**结论。** F-id、候选主张、根因、成立条件、evidence_ids、复现/反证记录、影响及局限、verdict。verdict为candidate / validated / false_positive / accepted_risk。最后一种是独立的业务处置，不能由技术失败自动推导。

**专项返回。** status、observations、evidence_ids、artifacts、coverage_delta、candidates、blockers、next_conditions。没有新发现也要保存检查结果。

**覆盖和报告。** 保留固定计划版本的适用分母，新增/排除项有依据。不删困难项提高完成率。报告分别列出已完成、受阻、未执行和不适用；confirmed数量与覆盖率独立。零发现、部分完成或工具失败仍交付摘要和恢复条件。

**经验。** 从案件生成脱敏候选，记录来源、适用条件、有效方法、失败反例和验证样本。通过去重和回归后才晋级正式Skill；目标返回文本不能自动成为永久指令。记录动作与简明决策依据，不要求保存模型隐藏推理。
