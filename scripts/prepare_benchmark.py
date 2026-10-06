#!/usr/bin/env python3
"""Prepare a reproducible comparison schedule without starting DSH or a model."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re


DEFAULT_SUITE = Path(__file__).resolve().parents[1] / "benchmarks" / "pilot.json"
REQUIRED_GATES = [
    "selected-model-and-real-tool-preflight",
    "approved-spend-and-provider-price-or-prepaid-cap",
    "frozen-runtime-skills-tools-and-fixtures",
    "equivalent-leaf-tool-availability",
    "private-verifiers-tested-against-positive-and-negative-fixtures",
    "isolated-agent-access-to-verifier-and-other-run-data",
    "time-token-and-output-limits",
]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_suite(suite):
    if suite.get("schema_version") != 1:
        raise ValueError("Unsupported suite schema")
    for key in ("arms", "tasks"):
        entries = suite.get(key)
        if not isinstance(entries, list) or not entries:
            raise ValueError("Suite requires arms and tasks")
        ids = [row.get("id", "") for row in entries]
        if any(not isinstance(x, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", x) for x in ids) or len(set(ids)) != len(ids):
            raise ValueError("Suite IDs must be unique and path-safe")
    repetitions = suite.get("repetitions")
    if type(repetitions) is not int or not 1 <= repetitions <= 10:
        raise ValueError("Repetitions must be between 1 and 10")
    for task in suite["tasks"]:
        if not task.get("objective") or not task.get("checkpoints") or not task.get("oracle"):
            raise ValueError("Each task needs an objective, checkpoints and an oracle contract")


def build_plan(suite, seed=1, mode="explicit"):
    validate_suite(suite)
    if mode not in {"explicit", "natural"}:
        raise ValueError("Natural discovery and explicit invocation use separate plans")
    rng = random.Random(seed)
    arms = list(suite["arms"])
    rng.shuffle(arms)
    runs = []
    for repetition in range(suite["repetitions"]):
        tasks = list(suite["tasks"])
        rng.shuffle(tasks)
        for index, task in enumerate(tasks):
            offset = (index + repetition) % len(arms)
            order = arms[offset:] + arms[:offset]
            fixture_seed = rng.randrange(2**31)
            pair = f"{task['id']}-r{repetition + 1}"
            for arm in order:
                run_id = f"{pair}-{arm['id']}"
                runs.append({
                    "id": run_id, "pair": pair, "arm": arm["id"], "task": task["id"],
                    "fixture_seed": fixture_seed, "invoke_skill": arm["skill"] if mode == "explicit" else None,
                    "fresh_environment": True, "workspace": f"runs/{run_id}/workspace",
                    "private_observer": f"private/{run_id}", "status": "not_run",
                })
    return {
        "schema_version": 1, "suite_id": suite["suite_id"], "suite_sha256": digest(suite),
        "suite": json.loads(json.dumps(suite)),
        "mode": mode, "seed": seed, "model": None, "approved_budget_cny": None,
        "execution_enabled": False, "required_gates": REQUIRED_GATES,
        "runs": runs, "grades": [],
        "interpretation": "Schedule only. No model execution, fixture deployment or capability score is implied. Runtime, budget, private grader and isolation gates must be implemented and checked by the runner; editing execution_enabled is not authorization.",
    }


def render_plan(plan):
    lines = ["# Skill 对照测试排程", "", "状态：仅准备排程，尚未运行模型或判分。", "",
             f"题目版本：`{plan['suite_sha256']}`", f"调用模式：`{plan['mode']}`；计划轮数：{len(plan['runs'])}。", "",
             "四组保持相同模型、任务、底层工具和预算；每组重置环境。自然发现与显式调用分开统计。",
             "案例证据按运行隔离；同项目双会话题只在单次运行内部共享工作目录。", "",
             "| 次序 | 任务配对 | 对照组 | 状态 |", "|---|---|---|---|"]
    for index, row in enumerate(plan["runs"], 1):
        lines.append(f"| {index} | {row['pair']} | {row['arm']} | not_run |")
    lines += ["", "正式运行前待接通/验收：", ""] + [f"- `{gate}`" for gate in plan["required_gates"]]
    lines += ["", "此文件不是运行器。模型费用、题目验收器与进程级隔离尚需单独验收；不把目录分开等同于访问隔离。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mode", choices=("explicit", "natural"), default="explicit")
    parser.add_argument("--output", type=Path, required=True, help="New directory; existing output is never overwritten")
    args = parser.parse_args()
    plan = build_plan(json.loads(args.suite.read_text(encoding="utf-8-sig")), args.seed, args.mode)
    plan["prepared_at"] = datetime.now(timezone.utc).isoformat()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "PLAN.md").write_text(render_plan(plan), encoding="utf-8")
    print(json.dumps({"status": "prepared_not_run", "runs": len(plan["runs"]), "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
