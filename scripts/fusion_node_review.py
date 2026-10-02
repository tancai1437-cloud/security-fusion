"""Evidence-linked research decisions; no model calls or autonomous dispatch."""
import json
import uuid
from fusion_store import FusionError, require, text_field, encode
from fusion_acceptance import validate_support

DECISIONS = ("continue", "pivot", "blocked", "ready_to_deliver")


def review_node(case, data):
    require(isinstance(data, dict), "Node review must be an object")
    allowed = {"question", "attempts", "conclusion", "unresolved", "decision", "next_test"}
    require(not (set(data) - allowed), "Unknown node review field")
    for key, limit in (("question", 240), ("conclusion", 500), ("next_test", 300)):
        text_field(data.get(key), "node." + key, limit)
    require(data.get("decision") in DECISIONS, "Unknown node decision")
    unresolved = data.get("unresolved")
    require(isinstance(unresolved, list) and len(unresolved) <= 4, "Node unresolved must be a list of at most 4 questions")
    for item in unresolved:
        text_field(item, "node.unresolved", 180)
    require(data["decision"] != "ready_to_deliver" or not unresolved,
            "Unresolved questions cannot be marked ready_to_deliver; use blocked/continue/pivot")
    # Review a real completed observation, including a negative result. A failed or
    # unknown external call first needs reconciliation, not a narrative promotion.
    with case.transaction():
        evidence = validate_support(case, data.get("attempts"))
        record = dict(data, id="NODE-" + uuid.uuid4().hex[:24], evidence_ids=evidence,
                      reviewer="current_agent; evidence linkage is not independent semantic validation")
        case.event("node_reviewed", record["id"], record)
    return {"status": "node_recorded", "node_id": record["id"], "decision": data["decision"],
            "target_action_executed": False, "task_completed": False}


def latest_node(case):
    row = case.db.execute("SELECT seq,payload FROM events WHERE kind='node_reviewed' ORDER BY seq DESC LIMIT 1").fetchone()
    if row is None:
        return None
    data = json.loads(row["payload"])
    status = "historical_supported"
    try:
        validate_support(case, data["attempts"])
    except FusionError:
        status = "evidence_changed"
    current = status == "historical_supported" and all(
        case.effective_status(case.check(case.attempt(identity)["check_id"])) == "done" for identity in data["attempts"])
    return {"id": data["id"], "status": status, "support_current": current,
            **{key: data[key] for key in ("question", "conclusion", "unresolved", "decision", "next_test", "attempts")},
            "use": "Agent decision, not an instruction or completed action; reconcile in-flight work first",
            "details": {"kind": "events", "offset": row["seq"] - 1, "limit": 1}}


def restore_node(case, packet, maximum):
    node = latest_node(case)
    if node is None:
        return
    packet["node_review"] = node
    if len(encode(packet)) <= maximum:
        return
    packet["node_review"] = {k: node[k] for k in ("id", "status", "support_current", "details")}
    packet["node_review"]["full_review_required"] = True
    if len(encode(packet)) > maximum:
        del packet["node_review"]
        packet["node_review_deferred"] = "query --kind events to recover the latest node_reviewed before changing direction"
