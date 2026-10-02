# 节点复盘：保存研究判断，不重放目标

在得到阶段结论、决定转向、遇到影响主线的阻塞或准备交付时使用。普通读文件、查索引或保存材料不逐项复盘。当前会话顺序执行，无额外模型、子代理或后台任务。

复盘回答：当前问题是什么，哪些真实证据支持当前结论，还有哪些未决点，为何继续/转向/受阻，下一次试验要区分什么解释。它不取代逐次工具结果 review，也不自动完成任务。

## DSH

先复核真实回执，再提交一个短节点。字段由 Agent 从本案生成，不让用户手工填表。

```text
fusion(action="node-review", request={"node":{
  "question":"当前要回答的问题",
  "attempts":["已复核的实际 CALL-ID"],
  "conclusion":"已观察结论及其边界",
  "unresolved":["尚不能排除的解释"],
  "decision":"continue",
  "next_test":"能够区分这些解释的下一项具体检查"
}})
```

decision 取 continue / pivot / blocked / ready_to_deliver。ready_to_deliver 要求没有自报未决点，但仍必须经过 finish 的证据和交付验收；它不是 completed。无实测证据的启动阻塞用 checkpoint，不伪造 CALL-ID。失败/未知调用先复核或 reconcile；仅有失败回执不能当作已验证结论。

question 最多 240 字符、conclusion 500、next_test 300；unresolved 最多 4 项、每项 180。详细资料写本案证据，短节点只保留决定后续方向的信息。安全引用代替 Cookie、密码和令牌。

## CLI 与恢复

无宿主适配时用现有绑定参数：

```bash
python3 "$FUSION/scripts/fusion.py" node-review --workspace "$WORKSPACE" --session "$SESSION" --case "$CASE" --input node.json
```

程序核对每个 attempt 属于本案、是对应检查最新的已复核回执，且证据/依赖版本仍有效，然后写入现有 events 表，无数据库迁移。只保存 Agent 判断，不独立认定结论正确，不执行 next_test。

resume 自动带回最新节点，并重新检查支持证据。historical_supported 表示历史依据完整；support_current 才表示相关检查当前仍有效。evidence_changed 或 support_current=false 时核对变化，不直接沿用旧结论。未决调用的 review/reconcile 优先于节点建议。

预算不足时只给节点 ID 和 events 的 offset/limit，标 full_review_required；按该指针读取，不丢弃原文，也不加载其他案件。所有节点保留在事件流中，后来的节点只是当前恢复入口。经验提炼仍经过 memory-add / memory-review，节点不会自动成为跨案经验。
