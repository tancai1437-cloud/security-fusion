"""Audit observable delivery gaps without inferring unrecorded work or findings."""
from collections import Counter
import json

from fusion_methods import specialist_card
from fusion_store import digest_file


def inspect_output(case, relative):
    path = (case.root / relative).resolve()
    item = {"path": relative}
    if not path.is_relative_to(case.root):
        return dict(item, status="outside_case")
    if not path.is_file():
        return dict(item, status="missing")
    try:
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
