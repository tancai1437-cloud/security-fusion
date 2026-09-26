"""Goal acceptance linked to actual attempts, using existing config/events only."""
import json
from fusion_store import FusionError, require, text_field


def validate_support(case, attempts):
    require(isinstance(attempts, list) and 1 <= len(attempts) <= 12, "Assessment needs 1..12 actual attempt IDs")
    evidence = []
    for identity in attempts:
        attempt = case.attempt(identity)
        check = case.check(attempt["check_id"])
        require(check["latest_attempt"] == identity and case.historical_valid(check),
                "Assessment support is not reviewed or its evidence/dependency version changed")
        evidence.extend(a["id"] for a in case.artifacts(identity))
    return evidence


def assess(case, items):
    criteria = {c["id"] for c in case.meta("config").get("criteria", [])}
    require(criteria, "This legacy case has no goal criteria; do not invent full acceptance retrospectively")
    require(isinstance(items, list) and 1 <= len(items) <= 12, "assess requires 1..12 assessments")
    with case.transaction():
        for item in items:
            require(isinstance(item, dict) and item.get("criterion") in criteria, "Unknown goal criterion")
            text_field(item.get("summary"), "assessment.summary", 1200)
            evidence = validate_support(case, item.get("attempts"))
            payload = {"criterion": item["criterion"], "attempts": item["attempts"],
                       "summary": item["summary"], "evidence_ids": evidence,
                       "reviewer": "current_agent; not independent semantic validation"}
            case.event("criterion_assessed", item["criterion"], payload)
    return acceptance(case)


def acceptance(case, details=False):
    criteria = case.meta("config").get("criteria", [])
    latest = {}
    for row in case.db.execute("SELECT payload FROM events WHERE kind='criterion_assessed' ORDER BY seq"):
        item = json.loads(row["payload"])
        latest[item["criterion"]] = item
    items = []
    for criterion in criteria:
        item = {"id": criterion["id"], "status": "unassessed"}
        assessment = latest.get(criterion["id"])
        if assessment:
            try:
                validate_support(case, assessment["attempts"])
                item.update(status="supported", attempts=assessment["attempts"])
            except FusionError:
                item.update(status="support_changed", attempts=assessment["attempts"])
        if details:
            item["question"] = criterion["question"]
            if assessment:
                item.update(summary=assessment["summary"], evidence_ids=assessment["evidence_ids"])
        items.append(item)
    return {"specified": bool(criteria), "items": items,
            "gaps": [i for i in items if i["status"] != "supported"],
            "validation": "Evidence linkage and current-agent assessment; not independent proof of coverage"}
