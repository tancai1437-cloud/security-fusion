# 按职责分开，再按当前动作组合

三层路由仍是：主任务 → 当前专业方法 → 实际执行工具。下表是横向的组件分类，不是让 Agent 逐层读取的新流程。完整机器索引为 [components.json](../manifests/components.json)，来源比较见 [GitHub 选型与蒸馏](upstream-survey-2026-10-02.md)。

| 类型 | 负责什么 | 实现与加载方式 |
|---|---|---|
| 专业方法 Skill | 问题、前提、对照、反证、下一分支 | specialists + procedures；仅当前专项 |
| 工具适配 | MCP/CLI schema、真实上下文、调用与失败语义 | execution-routes + MCP/宿主接口；仅当前能力 |
| 上下文管理 | 当前问题、结论和原文指针 | views/宿主恢复；大输出留磁盘 |
| 执行留痕 | 调用与产物来源、版本、哈希 | store/evidence；执行时自动记录 |
| 任务隔离 | 项目、案件、会话、共享工具资源 | workspace/宿主；检索前限定范围 |
| 中断恢复 | 未决核对、查重、依赖有效性 | progress/store；恢复事件触发 |
| 节点复盘 | 阶段结论、未决点、转向与下一试验 | [node-review](node-review.md)；仅有意义的节点 |
| 纵深推进 | 当前假设、前提、路径与试验顺序 | 节点 next_check 与已满足依赖优先；动态收益排序仍待实现 |
| 经验记忆 | 脱敏方法、反例、版本、召回 | memory；默认词法，可选真实向量 |
| 交付复测 | 完成条件、证据、未测与受阻范围 | acceptance/delivery；交付事件触发 |
| 效果评测 | 正确性、开销、重复、恢复与交付 | 独立测试路径；不塞进每个任务上下文 |
| 装配与来源 | 选择当前组件、约束与固定来源 | composition；程序生成，不让模型读全目录 |
| 漏洞情报与知识 | 来源、时效、受影响范围与适用性 | knowledge/intel；按需查询并保存快照 |

每环节的三个优先参考、固定提交与本次落地映射见 [2026-10-06 分环节选型](component-selection-2026-10-06.md)。这是维护者资料，不进入普通任务的恢复包。

## 组合入口

DSH 的 route 已直接调用装配程序：返回一个专项方法、一项能力、当前执行阶段需要的运行约定，再从真实宿主 registry 选工具。旧 route 缓存的指纹包含组件清单版本，清单改变必须重新准备。它不创建目标检查、不调用目标、不宣称 MCP 已健康。

维护者或无原生宿主时可以只读查看：

```bash
python3 scripts/fusion.py compose --skill fusion-api --capability http.request --phase execute --host cli
python3 scripts/fusion.py compose --skill fusion-api --capability http.request --phase recover --host cli
python3 scripts/fusion.py catalog --component recovery
```

phase 为 execute/recover/review/deliver。组合结果只包含当前方法、能力及当前阶段约定；上游清单、其他专项、评测说明不进入普通调用。compose 是选择与展示，不是新调度器，也不替代 begin/run/execute。

| 事件 | 自动机制 | Agent 需要做的判断 |
|---|---|---|
| 选择当前动作 | 组合方法/能力、验证配对、返回真实工具接口 | 本次要消除什么不确定性 |
| 实际执行 | DSH 捕获回执；CLI 通过管理命令留痕 | 读取真实结果、正确 review |
| 阶段结论或转向 | node-review 校验证据并持久化 | 结论、反例、未决点与下一试验 |
| 压缩或中断恢复 | 本案状态、节点、未决调用和前置结果按预算返回 | 先核对未知结果，再继续有效节点 |
| 交付 | 条件/证据/产物检查，缺口保留 | 正确解释影响、边界及未测部分 |

新手检查前不要求先阅读全部分类；没有安装 DSH 宿主组件时只具备 CLI 管理路径或文字指引，不声称启用 hook。Pi/OpenCode 等适配未达到同等联调覆盖。原始证据留在独立案件；Markdown 是人读视图，SQLite/JSON 是程序索引和状态。向量检索只帮助找到相关材料，不能接管案件归属、已测状态或执行授权。

## 融合边界与剩余缺口

优先复用现有 Python 标准库/SQLite，不引入 LangGraph、Temporal、图数据库或可观测平台作为生产依赖。上游项目分别提供参考机制，不整体复制其 Agent、规则、凭据或运行代码。当前主会话执行，不因某项目使用多代理而改变用户约束。

已有组件与新增节点/装配路径不代表全部需求最优。仍需专项深度与多模型盲测、真实工具能力探针、动态试验排序、完整路径图、防守遥测、清理复测、其他宿主接入；这些在组件清单的 gap 字段保留。后续采用组件必须说明解决哪个缺口、相较本地实现的收益、额外服务成本和可回退方式。
