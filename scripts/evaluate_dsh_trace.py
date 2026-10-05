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
    elif kind == "observed-tool-result" and row.get("child"):
        metrics["observed_child_tools"][row.get("tool", "unknown")] += 1
        if row.get("isError"):
            metrics["failed_child_calls"][row.get("tool", "unknown")] += 1
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


def evaluate(rows):
    metrics = {"observed_child_tools": Counter(), "failed_child_calls": Counter(), "fusion_actions": Counter(),
               "routed": set(), "reported_usage": Counter(), "turn_error_codes": [], "recovery_chars": [],
               "delivery_claims": [], "compactions": 0}
    for row in rows:
        track_tools(row, metrics)
        track_context(row, metrics)
    actual = sum(metrics["observed_child_tools"].values())
    metrics["status"] = ("infrastructure_blocked" if metrics["turn_error_codes"] and not actual else
                         "not_executed" if not actual else "delivery_reported" if metrics["delivery_claims"] else "executed_without_delivery")
    metrics["observed_child_calls"] = actual
    metrics["routed_receipts_reported"] = len(metrics.pop("routed"))
    metrics["interpretation"] = "Host trace observations only. Child calls can be local reads/writes; routed receipts are claims until checked against case hashes. Usage excludes unreported calls. No target coverage, methodology adherence, wasteful repeats or success score is inferred."
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    # Malformed traces fail visibly rather than silently becoming a passing run.
    with args.trace.open(encoding="utf-8-sig") as stream:
        result = evaluate(json.loads(line) for line in stream if line.strip())
    text = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
