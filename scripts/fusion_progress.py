"""Derive a small continuation and relevant outcomes from the existing ledger."""
import json


def blocked_by(case, row):
    return [key for key in json.loads(row["deps"])
            if case.effective_status(case.check(key)) != "done"]


def next_action(case, current, rows):
    if current is None:
        return {"action": "unblock" if any(r["status"] in {"pending", "blocked", "failed"} for r in rows)
                else "select_or_deliver", "completion": False}
    status = case.effective_status(current)
    action = {"running": "reconcile", "unknown": "reconcile", "review": "review", "done": "reuse"}.get(status)
    if action is None:
        action = "execute" if status == "pending" and not blocked_by(case, current) else "unblock"
    return {"action": action, "check_id": current["id"], "attempt_id": current["latest_attempt"]}


def dependency_ids(case, current):
    pending = json.loads(current["deps"]) if current else []
    ordered, seen = [], set()
    while pending:
        key = pending.pop(0)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
        pending.extend(json.loads(case.check(key)["deps"]))
    return ordered


def outcome_card(case, row):
    spec = json.loads(row["spec"])
    evidence = case.artifacts(row["latest_attempt"])
    # Freshness and historical validity answer different questions. An expired
    # negative result remains history but must not authorize automatic reuse.
    status = case.effective_status(row)
    historical = case.historical_valid(row)
    notes = list(case.db.execute(
        "SELECT * FROM notes WHERE check_id=? AND superseded=0 AND kind IN ('fact','negative','refuted') "
        "ORDER BY created DESC", (row["id"],)))
    return {"check_id": row["id"], "attempt_id": row["latest_attempt"], "purpose": spec["purpose"],
            "target": spec["target"], "identity_ref": spec["identity_ref"],
            "capability": spec["capability_id"], "method_version": spec["method_version"],
            "target_version": spec["target_version"], "work": spec.get("work"),
            "status": status, "reusable": status == "done", "historical_evidence_valid": historical,
            "summary": row["summary"], "evidence": evidence[:1], "omitted_evidence": max(0, len(evidence) - 1),
            "notes": [{"id": n["id"], "kind": n["kind"], "text": n["text"],
                       "evidence_ids": json.loads(n["evidence"])} for n in notes[:2]],
            "omitted_notes": max(0, len(notes) - 2)}


def relevant_results(case, current, rows):
    dependencies = dependency_ids(case, current)
    rank = {key: i for i, key in enumerate(dependencies)}
    candidates = [r for r in reversed(rows) if r["status"] == "done" and
                  (current is None or r["id"] != current["id"]) and
                  (current is None or r["target"] == current["target"] or r["id"] in rank)]
    # Direct and transitive prerequisites precede incidental recent observations.
    candidates.sort(key=lambda row: (0, rank[row["id"]]) if row["id"] in rank else
                    (1 if json.loads(row["spec"])["capability_id"] != "evidence.persist" else 2, 0))
    return (outcome_card(case, r) for r in candidates), len(candidates)
