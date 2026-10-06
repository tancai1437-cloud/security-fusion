#!/usr/bin/env python3
"""Offline DSH trace metrics. Never calls a model, a target, or an MCP service."""
import argparse
from collections import Counter
import json
from pathlib import Path


def object_value(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def result_values(blocks):
    for block in blocks or []:
        if block.get("type") == "text":
            yield object_value(block.get("text"))
        elif block.get("type") == "tool-result":
            yield from result_values(block.get("content"))


def track_tools(row, metrics):
    kind, data = row.get("type"), object_value(row.get("data"))
    if kind == "tool/call" and data.get("name") == "fusion":
        metrics["fusion_actions"][object_value(data.get("arguments")).get("action", "unknown")] += 1
    elif kind == "observed-tool-result":
        name = row.get("tool", "unknown")
        metrics["observed_tools"][name] += 1
        if row.get("isError"):
            metrics["failed_tools"][name] += 1
        if row.get("child"):
            metrics["observed_child_tools"][name] += 1
            if row.get("isError"):
                metrics["failed_child_calls"][name] += 1
        else:
            metrics["observed_direct_tools"][name] += 1
    elif kind == "tool/result":
        for value in result_values(object_value(data.get("message")).get("content")):
            if value.get("attempt_id") and value.get("routing"):
                metrics["routed"].add(value["attempt_id"])
            if value.get("status") in {"partial", "submitted"} and value.get("report") and value.get("verification"):
                metrics["delivery_claims"].append(value["status"])


def track_context(row, metrics):
    kind, data = row.get("type"), object_value(row.get("data"))
    if kind == "turn/end":
        reason = object_value(data.get("reason"))
        if reason.get("kind") == "error":
            # Error text may contain headers, endpoints or secrets. Export codes only.
            metrics["turn_error_codes"].append(object_value(reason.get("error")).get("code", "unspecified"))
    elif kind == "assistant/message":
        metrics["reported_usage"].update({k: v for k, v in object_value(data.get("usage")).items()
                                          if isinstance(v, (int, float)) and not isinstance(v, bool)})
    elif kind == "compaction-result":
        metrics["compactions"] += 1
    elif kind == "user/message" and object_value(data.get("source")).get("kind") == "security-fusion-state":
        metrics["recovery_chars"].append(sum(len(b.get("text", "")) for b in data.get("content", []) if b.get("type") == "text"))


def unique_observations(rows):
    """Use registry execution identities, never tool arguments, to deduplicate replays."""
    seen = {}
    for row in rows:
        if row.get("type") == "observed-tool-result" and row.get("execution_id"):
            key = (row.get("run"), row.get("job"), row.get("session"), row["execution_id"])
            signature = (row.get("tool"), bool(row.get("child")), bool(row.get("isError")))
            if key in seen:
                if seen[key] != signature:
                    raise ValueError("Conflicting observations for one execution identity")
                continue
            seen[key] = signature
        yield row


def evaluate(rows, leaf_tools=None):
    metrics = {"observed_tools": Counter(), "failed_tools": Counter(), "observed_direct_tools": Counter(),
               "observed_child_tools": Counter(), "failed_child_calls": Counter(), "fusion_actions": Counter(),
               "routed": set(), "reported_usage": Counter(), "turn_error_codes": [], "recovery_chars": [],
               "delivery_claims": [], "compactions": 0, "observations_without_identity": 0}
    for row in unique_observations(rows):
        if row.get("type") == "observed-tool-result" and not row.get("execution_id"):
            metrics["observations_without_identity"] += 1
        track_tools(row, metrics)
        track_context(row, metrics)
    actual = sum(metrics["observed_tools"].values())
    metrics["status"] = ("infrastructure_blocked" if metrics["turn_error_codes"] and not actual else
                         "not_executed" if not actual else "delivery_reported" if metrics["delivery_claims"] else "executed_without_delivery")
    metrics["observed_tool_calls"] = actual
    metrics["observed_child_calls"] = sum(metrics["observed_child_tools"].values())
    metrics["observed_direct_calls"] = sum(metrics["observed_direct_tools"].values())
    # Shared leaf names come from the frozen test environment, not a skill's wrapper names.
    metrics["shared_leaf_calls"] = None if leaf_tools is None else sum(metrics["observed_tools"][name] for name in set(leaf_tools))
    metrics["shared_leaf_failed_calls"] = None if leaf_tools is None else sum(metrics["failed_tools"][name] for name in set(leaf_tools))
    metrics["routed_receipts_reported"] = len(metrics.pop("routed"))
    metrics["interpretation"] = "Host observations include direct and nested results, including failures and local reads/writes. Shared leaf counts require a frozen common tool inventory. Legacy observations without execution identity cannot be deduplicated. Report/route receipts remain claims; usage excludes unreported calls and is not a price estimate. Status is descriptive, not a benchmark grade; even a run with provider errors may contain useful work. No target coverage, methodology adherence, wasteful repeats or success score is inferred."
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--leaf-tool", action="append", help="Shared leaf tool from the frozen environment; repeat for each name")
    args = parser.parse_args()
    # Malformed traces fail visibly rather than silently becoming a passing run.
    with args.trace.open(encoding="utf-8-sig") as stream:
        result = evaluate((json.loads(line) for line in stream if line.strip()), args.leaf_tool)
    text = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
