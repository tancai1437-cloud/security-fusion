# 与 dsh-purge 共存

核对日期：2026-10-02。采用 **同一个 DSH 宿主中的独立执行预设**：dsh-purge 提供已有资产台与数据接口，Security Fusion 提供当前专项方法和案件执行协议。保留原有红队预设；不要把两个主控提示词叠进同一会话。

## 固定来源与发现

- [dsh-purge 1.1.47，b7c14005](https://github.com/YuJunZhiXue/dsh-purge/tree/b7c14005c35a3db4ca5ca1c2a72cab60cf48909e)：[包声明](https://github.com/YuJunZhiXue/dsh-purge/blob/b7c14005c35a3db4ca5ca1c2a72cab60cf48909e/package.json)要求 DSH 0.2.0-rc.2。
- [红队预设](https://github.com/YuJunZhiXue/dsh-purge/blob/b7c14005c35a3db4ca5ca1c2a72cab60cf48909e/presets/redteam/agent.cordis.yml)关闭默认技能目录发现，只扫描自定义根。主角色要求委派执行，与 Fusion 当前会话执行协议冲突。`skills add --agent universal` 成功不代表该预设能看到它。
- [数据工具](https://github.com/YuJunZhiXue/dsh-purge/blob/b7c14005c35a3db4ca5ca1c2a72cab60cf48909e/lib/redteam/tools.js)使用进程内会话绑定，并保留全局当前靶标/唯一靶标回退；显式 engagement 优先。这不是本包可依赖的持久案件身份。
- [原生数据层](https://github.com/YuJunZhiXue/dsh-purge/blob/b7c14005c35a3db4ca5ca1c2a72cab60cf48909e/lib/redteam/store-core.js)支持 `openEngagement(...,{bindCurrent:false})`，可复用它而不改 SQL 或全局当前指针。
- [DSH 0.2.0-rc.2，639ed015](https://github.com/deepseek-ai/deepseek-harness/tree/639ed015397290b3745d163aafe02ffee4aa3f84)：Session format 4 的恢复替换字段是 `startSeq/endSeq`；旧版 format 0 使用 `start/end`。这是 SDK 实测发现的兼容错误，已按实际格式处理，未知格式明确拒绝。

只参考/调用正常扩展与数据接口。本包不导入 dsh-purge 的清洗入口、不调用 Apply、不重写其权限或模型策略，也不复制其全部源码/角色/技能库。

## 唯一职责

| 需求 | 所有者 | Fusion 补充 |
|---|---|---|
| 模型、会话、权限、MCP 连接 | DSH 宿主 | 读取当前 registry，调用已有工具，不新建同名 MCP 客户端 |
| 对话压缩、工具输出裁剪 | DSH 原生 compaction | 压缩后从本案磁盘恢复一块有预算的工作集，替换自己上一块；不做第二次压缩 |
| 异常请求重试/异常轮次续跑 | 已有 dsh-purge 服务 | 不再启动重试循环；Fusion 的至多两次正常结束纠正只检查交付/暂停协议 |
| 主任务、专项、真实执行 | 当前单会话 + Fusion | 先返回当前方法与工具，再执行，保留真实 CALL 回执与条件查重 |
| 资产台、资产检索、原生报表视图 | dsh-purge Drill | 每案独立 engagement，派生记录按需写入；不镜像整个数据库 |
| 原始证据、未决动作、复盘、验收 | Fusion 案件账本 | 保留唯一权威，Drill“查到一条记录”不能证明目标刚通过实测 |
| 已有方法技能 | 原技能文件 | 当前入口 + 按需专项；不重新安装、复制为同名技能 |
| 工具缺口 | 已有环境配置、按需 preflight | 只对当前方法所需资源排障；无关 FOFA/VPS 缺失不阻塞文件分析 |

这里仍有两个用途不同的存储：Fusion 保存调用证据和任务状态，Drill 保存便于浏览的资产记录。不会维护两份任务完成状态。原始请求是否再存入 Drill 由需要决定，不自动搬运全部证据。

## 具体组合

安装后新增 `Security Fusion · 单会话研究`（preset ID `security-fusion`）。从**当前已安装的官方 standard 预设**选取原生文件、shell、搜索、技能、压缩、提问等组件；用短执行说明替换该副本的人设，省去委派、workflow、额外目标管理。原 standard/redteam 定义不改，宿主已有 MCP 继续可见。

技能发现明确包含本包实际根、`$DSH_HOME/skills` 和 `$DSH_HOME/redteam/skills`；不启用默认全盘技能根。本包根只发现一个 security-fusion，不把 13 个专项再注册成另一份工具目录。用户自己的技能目录仍可能较大，入口不会把其中正文全部读入。

数据桥只注册 8 个已核对原生接口：`redteam_preflight`、`redteam_asset_add/query/get/stats/timeline`、`redteam_http_evidence_add`、`redteam_report`。其 schema 与实现来自已安装 dsh-purge，统一作为 `evidence.persist` 候选，经 `fusion.execute` 留痕。没有给整个 `redteam_*` 通配符放行。其他专业工具仍走原三层路由，未对全部 dsh-purge 接口宣称兼容。

首次需要 Drill 时，根据真实 session ID + 规范 cwd + 本案目标生成稳定独立 engagement；映射写入既有 binding.json。每次读写显式传 engagement，不依赖内存 Map、全局 current 或唯一靶标回退；跨案 ID、目标/范围改变、绑定库丢失明确报错。重启重新读取同一映射，恢复块只带 ID 和目标，不塞全库。Drill 显示名带目标及唯一标识。

## 在实际目标机接入

仅复制 Skill 不会安装宿主 hook。让目标 Agent 识别**正在使用的** profile、SDK runtime 根、DSH_HOME，然后执行以下脚本。不要把其它机器或其它 Agent 的路径填进去；也不要修改 dsh-purge 托管的 redteam 预设，它可能在升级时重写。

```bash
FUSION_ROOT="$HOME/.agents/skills/security-fusion"
python3 "$FUSION_ROOT/scripts/install_dsh_adapter.py" \
  --profile /actual/dsh/profile \
  --runtime /actual/dsh/runtime \
  --dsh-home /actual/dsh/home \
  --state-dir /actual/private/security-fusion \
  --python python3 --purge --dry-run
```

路径确认且预检通过后，去掉 `--dry-run` 安装；重启该 profile，**新建会话并选择新预设**。安装器只改自有标记块、保留配置备份。已有自有全局 adapter 可迁入预设；不自动改当前会话或默认模式。版本不符先核对接口，不能把“配置写入成功”当宿主运行接通。普通升级保留已配置的预设范围。

接入后按次序验收：

1. 原生 `skill` 能加载 security-fusion；`fusion(action="host-status")` 显示 integration=dsh-purge、session_format=4、8 个数据工具及当前 MCP 工具数量。数量只是可见性，不能证明健康。
2. 在本地受控样本完成 route → execute → review，确认有真实 CALL 和捕获文件。按需用数据工具登记派生资产；直接绕过入口的调用应被拦截。
3. 同 cwd 新建第二会话，写不同测试资产，切换 Drill 面板目标后两个会话仍互不读串。重启后各自恢复原 engagement。
4. 压缩/恢复后仍有一块当前工作集，原始日志不丢；已完成项复用，未知项先核对；验证 REPORT 引用实际回执。

撤销用同一 profile/state-dir 参数加 `--uninstall`，重启；可回选原 preset。仅取消本包注册，案件、Drill 数据和备份均保留。

## 验证范围与仍需补齐

本地已用实际 DSH 0.2.0-rc.2 SDK、Cordis ToolRuntime、dsh-purge 1.1.47 数据工具和 SQLite 验证原生技能发现、route→execute→记录、直接调用拦截、两会话隔离、映射恢复、错误回执；新版恢复替换已修复，并回归 DSH 0.1.2-rc.1。官方 standard 预设用宿主 YAML schema 解析，保留 `!!js` 为数据，不在生成时执行。测试资源和数据全部在隔离目录，没有修改日常 DSH profile。

本轮整包 160 项测试：157 通过、3 项平台相关跳过；可选上游/SDK 场景在本机启用，其中新增共存测试 6 个 Node 场景全部通过。发布文件集合的 220 个本地链接及依赖图通过；结构门禁通过，已有复杂函数数与循环依赖数未增加。仓库没有自定义结构约束 rules.toml，不能把 `sentrux check` 的缺规则提示算成规则检查通过。

这不是目标 Kali 上的完整桌面验收，也没有运行清洗入口、全套 dsh-purge 补丁或真实模型长任务；不能保证这些组合的最终遵循率。新预设完整挂载、现有自定义 prompt/插件、实际 MCP 权限与模型压缩后的行为还需目标机验收。测试不会用空实现冒充这些能力。

当前刻意不自动合并既有 Drill 案件、不跨案传播目标事实、不同步全部 POC/攻击链接口。下一步应先跑上述实际闭环，再决定需要扩展哪些数据接口。专业纵深仍取决于具体方法、模型和可用工具；资产库与恢复正确不代表每个专项都已经足够深入。

回归入口：`python -m unittest discover -s tests -v`。可选真实依赖测试设置 `FUSION_DSH_RUNTIME`、`FUSION_PURGE_SOURCE`、`FUSION_DSH_SOURCE` 指向对应已核对目录后运行 `node --test tests/dsh-purge.test.mjs tests/dsh-schema.test.mjs`；不设置时相关真实依赖场景明确 skip。
