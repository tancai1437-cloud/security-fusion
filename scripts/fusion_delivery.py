"""Audit observable delivery gaps without inferring unrecorded work or findings."""
from collections import Counter
import json

from fusion_methods import specialist_card
from fusion_store import digest_file
from urllib.parse import quote


def inspect_directory(case, path, item):
    if not path.is_dir():
        return dict(item, status="missing")
    nonempty_files = 0
    for index, child in enumerate(path.rglob("*")):
        if index >= 1000:
            return dict(item, status="too_large_to_inspect")
        if not child.resolve().is_relative_to(case.root):
            return dict(item, status="outside_case")
        if child.is_file() and child.stat().st_size:
            nonempty_files += 1
    return dict(item, status="present_unreviewed" if nonempty_files else "empty",
                nonempty_files=nonempty_files)


def inspect_output(case, relative):
    path = (case.root / relative).resolve()
    item = {"path": relative}
    if not path.is_relative_to(case.root):
        return dict(item, status="outside_case")
    try:
        if relative.endswith("/"):
            return inspect_directory(case, path, item)
        if not path.is_file():
            return dict(item, status="missing")
        size = path.stat().st_size
        if not size:
            return dict(item, status="empty")
        # Presence/JSON syntax are observable; neither proves adequate analysis.
        if path.suffix == ".json":
            if size > 32 * 1024 * 1024:
                return dict(item, status="too_large_to_inspect", bytes=size)
            json.loads(path.read_text(encoding="utf-8-sig"))
        return dict(item, status="present_unreviewed", bytes=size, sha256=digest_file(path))
    except (UnicodeError, ValueError):
        return dict(item, status="invalid_json")
    except OSError:
        return dict(item, status="unreadable")


def delivery_audit(case, checks, attempts):
    stages = []
    for skill in sorted({c["skill"] for c in checks}):
        card = specialist_card(skill)
        stages.append({"skill_id": skill, "completion": card["completion"],
                       "outputs": [inspect_output(case, p) for p in card["stage_outputs"]]})
    gaps = [output for stage in stages for output in stage["outputs"]
            if output["status"] != "present_unreviewed"]
    routes = Counter()
    for attempt in attempts:
        spec = json.loads(case.check(attempt["check_id"])["spec"])
        routes[(spec["skill_id"], spec["capability_id"], attempt["provider"], attempt["tool"])] += 1
    return {"status": "no_registered_work" if not checks else "missing_artifacts" if gaps else "review_required",
            "stages": stages, "gaps": gaps, "registered_attempts": len(attempts),
            "attempt_statuses": dict(Counter(a["status"] for a in attempts)),
            "routes": [dict(skill_id=k[0], capability_id=k[1], provider=k[2], tool=k[3], attempts=v)
                       for k, v in sorted(routes.items())],
            "untracked_actions": "unknown_without_host_trace",
            "methodology_adherence": "not_measured",
            "review_required": "Compare actual host calls, scope, controls and evidence with these stage requirements; "
                               "file presence and registered checks do not prove full coverage."}


def stage_markdown(case, checks, attempts, artifacts, delivery, goal, revision):
    """A deterministic handoff from real ledger rows, never a generated finding."""
    from fusion_node_review import latest_node
    config = case.meta("config")
    cell = lambda value: str(value or "—").replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = ["# 阶段报告", "", f"案件：{case.meta('case_id')} · 账本版本：{revision}", "",
             "此页按实测账本自动生成。已记录观察、已审核结论和任务验收分别列出；不自动认定漏洞或任务完成。", "",
             "## 目标与范围", "", config["objective"], "", config["scope"], "",
             "## 当前结果", "", "| 检查 | 状态 | 问题 | 已记录结论 |", "|---|---|---|---|"]
    for row in checks:
        lines.append("| " + " | ".join(cell(row.get(k)) for k in ("id", "status", "purpose", "summary")) + " |")
    lines += ["", "## 执行与证据", "", "| 实际回执 | 工具 | 状态 | 用时（秒） |", "|---|---|---|---|"]
    for attempt in attempts:
        elapsed = (round(attempt["finished"] - attempt["started"], 3)
                   if attempt.get("finished") is not None else "未结束")
        lines.append("| " + " | ".join(cell(x) for x in
                     (attempt["id"], attempt["tool"], attempt["status"], elapsed)) + " |")
    for artifact in artifacts:
        link = "../" + quote(artifact["path"], safe="/")
        lines.append(f"- {artifact['id']}: [{cell(artifact['path'])}]({link}) · SHA256 `{artifact['sha256']}`")
    lines += ["", "## 未完成项", ""]
    lines += [f"- {c['id']} [{c['status']}]: {c['purpose']}" for c in checks if c["status"] != "done"]
    lines += [f"- 专项产物 {g['path']}: {g['status']}" for g in delivery["gaps"]]
    lines += ["- 任务验收：" + json.dumps(g, ensure_ascii=False) for g in goal["gaps"]]
    node = latest_node(case)
    lines += ["", "## 接续节点", ""]
    if node:
        lines += [node["question"], "", node["conclusion"], "",
                  f"证据状态：{node['status']}；可按当前条件复用：{node['support_current']}", "",
                  "下一项：" + (node.get("next_check") or node["next_test"])]
    else:
        lines += ["从 resume 的 next_action 接续；先对账未完成回执，再选择待执行项。"]
    lines += ["", "## 完整索引", "", "- [执行账本](ledger.md)", "- [验收记录](acceptance.md)",
              "- [路由与专项产物](delivery.json)", "- [恢复入口](../resume.md)", "",
              "账本外的宿主调用未在此推断；模型额度或基础设施失败需结合宿主 trace 检阅。", ""]
    return "\n".join(lines)
