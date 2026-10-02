# 红队 / SRC 方法与公开漏洞情报

2026-10-02。方法、公开情报、本案实测分开；不自动运行上游PoC，不创建第二套任务或向量数据库。

## 调用

DSH首次route/execute明确 `request.mission="src"` 或 `"redteam"`，保存到案件与恢复状态。SRC沿业务的身份/对象/状态边界深入；红队沿约定控制、入口前提、依赖和防守观测推进。旧案件不自动迁移类型。

新组件/CVE事实 `software.identified` / `cve.mentioned` 可经advance选择 `advisory-applicability`。新业务边界或方法受阻时才查local，不每轮检索。查询有效就读快照；更新需明确retest_reason与refresh。

```json
{"action":"route","request":{"mission":"src","skill":"fusion-recon","capability":"knowledge.lookup","tool":"fusion_knowledge","purpose":"核对组件CVE适用条件"}}
```

接route_id执行；首次仍需实际objective/scope/target/criteria：

```json
{"action":"execute","request":{"route_id":"本会话返回值","arguments":{"mode":"cve","skill":"fusion-recon","cve":"CVE-2021-44228"},"work":{"key":"advisory-log4j","conditions":{"cve":"CVE-2021-44228","component_evidence":"实际证据ID"}}}}
```

fusion_knowledge是宿主实际工具，经fusion.execute留痕，不另装MCP。完整JSON快照被保存为调用证据，用artifact按E-ID分段读affected/版本/配置/厂商引用；案件内另有Markdown摘要。

CLI：`python3 "$SKILL/scripts/fusion.py" knowledge --case "$CASE" --workspace "$WORKSPACE" --session "$SESSION" --input query.json`。返回快照路径/哈希/案件事件，不伪造目标检查完成；后续通过管理的run/read保存复核回执。

## 查询模式

| mode | 输入（均需skill） | 行为 |
|---|---|---|
| local | query：具体问题 | BM25方法卡+本项目/专项审核有效经验，不联网 |
| cve | 精确cve | CVE List V5+CISA KEV官方镜像+FIRST EPSS |
| package | ecosystem/package/version | OSV包版本候选，支持PyPI/npm/Maven/Go/RubyGems/crates.io/Packagist/NuGet/Debian/Alpine |
| recent | 可选days 1..7/product/offset/until | NVD修改记录，每页20条；摘要最多5条，完整页落盘 |

recent默认截止当前整点；分页复用window.until和next_offset。它是修改流，不是全部新发布漏洞。OSV next_cursor非空继续同一包版本，不能把首页当全库。公开查询只发送明确提供的公共标识/产品元数据；不自动发送目标域名、流量、凭据、经验。私有包不能发到OSV，用local。

## 新鲜度与证据

按需查询，TTL一小时；refresh:true强制请求，offline:true只读缓存，互斥。公共缓存不存案件事实。没有后台定时任务、全量镜像或秒级推送。

每源分别返回live/cache/offline_cache/stale_on_error/unavailable、fetched_at/checked_at/age_seconds和规范化JSON的源SHA256；保留KEV dateReleased、EPSS分值所属date、CVE更新时间。刚下载不等于源刚更新。失联/限流/坏格式显式返回，无结果不等于安全。每源响应最多8MiB，网络超时12秒，不自动重试。无进展分页返回错误，避免重复读取同一页。

REJECTED、withdrawn、backport、未启用功能和未知版本都进入适用性判断。KEV/EPSS只辅助优先级，不合成目标可利用概率；查询成功也不是目标漏洞证据。

## 知识与上下文

[8张方法卡](../manifests/knowledge-cards.json)按mission/skill过滤，最多两张；经验复用原Memory，默认本项目，候选/过期/未审核不返回。include_general只扩展已脱敏审核的通用方法。返回最多6000字符（宿主绑定另计），完整JSON+MD落盘。

事实留在案件；教训经memory-add→memory-review→检索。已有可选真实嵌入接口保持，不新增向量库或模型调用。dsh-purge继续拥有资产/POC库，不复制数据库，不自动执行未审核PoC。

## 来源

- [CVE List V5](https://github.com/CVEProject/cvelistV5)：状态、CNA条件和厂商引用，按ID取回。
- [CISA官方镜像](https://github.com/cisagov/kev-data)：已知利用记录与更新时间。
- [FIRST接口](https://api.first.org/epss/) / [含义](https://www.first.org/epss/faq)：保留分值日期。
- [OSV接口](https://google.github.io/osv.dev/post-v1-query/)：生态/包/版本及分页。
- [NVD接口](https://nvd.nist.gov/developers/vulnerabilities)：修改时间窗和分页；公共接口受限流。
- [OWASP WSTG](https://github.com/OWASP/wstg)：提炼业务边界、身份和对照。
- [Attack Flow](https://github.com/center-for-threat-informed-defense/attack-flow)：吸收条件节点，复用depends_on/node-review。
- [Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup)：借鉴多源保留出处，不复制服务或声称同等覆盖。

仍需Agent解释条件和设计验证；未证明所有模型遵循，也未完成目标Kali长任务验收。

## 本轮验证

- 本地全量回归170项：167通过，3项平台条件跳过；尾部调整后重跑10项情报专项与真实DSH SDK两项，均通过。
- 真实DSH 0.2.0-rc.2：路由到fusion_knowledge、执行本地检索、完整快照导入E-ID证据、拒绝未绑定直调、SRC类型恢复与禁止会话内改型。
- 官方只读实测：CVE-2021-44228取得CVE/KEV/EPSS；OSV对PyPI jinja2 3.1.4返回6份记录（含别名关联，不能宣称6个独立漏洞）；NVD 2026-10-01 08:00至10-02 08:00 UTC修改窗返回总数1215，实际只取20条并返回next_offset=20。带nginx关键词的同窗为0条，不解释为产品无漏洞。
- 未执行任何外部目标扫描/利用，未对用户日常DSH安装做修改，未安装新生产依赖或迁移数据库。
