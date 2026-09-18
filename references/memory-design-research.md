# 记忆与检索选型记录

本轮联网核对官方文档于 2026-09-19。下面是基于本项目规模、可移植性和已有账本的工程选择，不是对各产品的性能排行榜。没有复制这些产品的实现或安装其依赖。

| 方案 | 适合的问题 | 本项目决定 |
|---|---|---|
| 结构化账本、明确命名空间 | 案件归属、状态、授权范围、查重、版本 | 作为事实来源，保留现有 SQLite |
| SQLite FTS5 / BM25 | 标识符、工具名、已知术语和低成本本地检索 | 默认路径，复用标准库 |
| 稠密向量 | 不同表述的相似方法 | 可选；实际存储向量并计算余弦，同模型版本严格匹配 |
| 词法与向量融合 | 同时保留精确术语和语义召回 | 有向量时使用 RRF；不直接相加不同量纲分数 |
| Qdrant 等索引服务 | 大规模向量、索引加速与服务化 | 当前不引入额外服务；超过精确扫描边界再评估 |
| 全自动记忆抽取服务 | 大量对话自动提取、更新、合并 | 当前在阶段交付时提炼，避免每步增加推理调用 |

**分开会话状态与跨会话经验。** LangGraph 将 thread-scoped 状态与可按自定义 namespace 组织的长期记忆区分。这里对应独立案件数据库与明确限定范围的经验卡片；没有使用相似度决定哪个案件归哪个会话。[官方 Memory overview](https://docs.langchain.com/oss/python/concepts/memory)

**隔离使用过滤条件。** Qdrant 多租户文档通过元数据过滤限制搜索范围。这里将项目、共享标记、状态、有效期和专项作为召回边界，先限定范围再取排名。向量更相似不能越过范围。[官方多租户文档](https://qdrant.tech/documentation/manage-data/multitenancy/)、[过滤文档](https://qdrant.tech/documentation/search/filtering/)

**保留精确匹配，并允许混合排序。** SQLite FTS5 支持 BM25 排序，其更优匹配分值更低；实现使用升序。Qdrant 描述的 RRF 根据各路结果的名次融合，适合不直接比较 BM25 与余弦分数的情况。本包采用普通 RRF、k=60，这是明确的实现参数，尚未通过真实案例调参。[SQLite FTS5](https://www.sqlite.org/fts5.html)、[Qdrant Hybrid Queries](https://qdrant.tech/documentation/search/hybrid-queries/)

**不把全文档常驻上下文。** Letta 的 memory blocks 与外部归档检索提供了区分常驻信息和按需信息的参考。这里仅把绑定、约束和当前检查视作必要恢复内容，经验按需返回，统一执行字符预算。[Letta Memory Blocks](https://docs.letta.com/tutorials/attaching-detaching-blocks/)

**机械保存不必每次触发模型抽取。** Mem0 的 add 文档区分推理提取与直接写入，也提示混用写入路径可能出现重复。这里使用明确的候选文档、内容指纹、审核事件及版本替换，由当前 Agent 在阶段结束时提炼，无额外记忆模型调用。[Mem0 官方 add 文档](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-operations/add.mdx)

验证重点是跨案误读/误写、旧会话失效、工具上下文冲突、项目越界召回、失效经验退出、证据来源校验、中文词法查询、向量计算及统一预算。合成向量测试只验证算法逻辑；真实嵌入模型的 Precision/Recall、延迟、token 和费用改善均未测量。需要真实脱敏案例集后再比较 BM25、向量、混合检索，而不是提前承诺某种索引一定更好。
