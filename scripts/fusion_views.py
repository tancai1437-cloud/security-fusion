"""Small model-facing views and reproducible exports of the case ledger."""
from collections import Counter
import json
import os
from pathlib import Path
import uuid

from fusion_store import FusionError, encode, manifest, require
from fusion_methods import check_guidance, specialist_card
from fusion_delivery import delivery_audit


def bounded(value, maximum):
    require(maximum >= 512, "max-chars must be at least 512")
    size = len(encode(value))
    require(size <= maximum,
            f"context_budget_exceeded: required_chars={size}; narrow the query or explicitly increase --max-chars")
    return value


def catalog(mission=None, skill=None, capability=None, inventory=None):
    missions = manifest("missions.json", "missions")
    modules = manifest("specialists.json", "modules")
    if mission:
        match = next((m for m in missions if m["id"] == mission), None)
        require(match is not None, "Unknown mission")
        return match
    if skill:
        match = next((m for m in modules if m["id"] == skill), None)
        require(match is not None, "Unknown specialist")
        result = {k: v for k, v in match.items() if k not in {"source_ids", "returns_to"}}
        return dict(result, action_card=specialist_card(skill))
    if not capability:
        return {"missions": [{"id": m["id"], "label": m["label"]} for m in missions],
                "specialists": [{"id": m["id"], "title": m["title"]} for m in modules]}
    match = next((r for r in manifest("execution-routes.json", "routes") if r["id"] == capability), None)
    require(match is not None, "Unknown capability")
    result = {"capability": capability, "required_input": match["required_input"],
              "expected_output": match["expected_output"]}
    if inventory is None:
        result.update(status="unverified_candidates", choices=match["choices"])
        return result
    bindings = observed_bindings(match, inventory)
    result.update(status="observed_candidates" if bindings else "unavailable", bindings=bindings,
                  observed_at=inventory.get("observed_at"), health="not_probed", automatic_selection=False)
    return result


def observed_bindings(route, inventory):
    require(isinstance(inventory, dict) and isinstance(inventory.get("providers"), list),
            "Inventory must contain providers from the current host")
    bindings = []
    for choice in route["choices"]:
        for provider in inventory["providers"]:
            if provider.get("id") != choice["provider"]:
                continue
            for tool in provider.get("tools", []):
                name = tool.get("name", "")
                candidates = choice["tool_candidates"]
                if not any(name == c or name.endswith("__" + c) for c in candidates):
                    continue
                require(isinstance(tool.get("inputSchema"), dict), "Observed tool has no inputSchema")
                binding = {"provider": provider["id"], "name": name, "inputSchema": tool["inputSchema"]}
                if "outputSchema" in tool:
                    binding["outputSchema"] = tool["outputSchema"]
                bindings.append(binding)
    return bindings


def check_card(case, row, verify=False):
    spec = json.loads(row["spec"])
    return {"id": row["id"], "skill": spec["skill_id"], "purpose": spec["purpose"],
            "target": spec["target"], "target_version": spec["target_version"],
            "identity_ref": spec["identity_ref"], "check_type": spec["check_type"],
            "status": case.effective_status(row) if verify else row["status"],
            "summary": row["summary"], "attempt_id": row["latest_attempt"]}


def note_card(row):
    return {"id": row["id"], "check_id": row["check_id"], "kind": row["kind"],
            "text": row["text"], "evidence_ids": json.loads(row["evidence"])}


def select_current(case, rows, identity):
    if identity:
        return case.check(identity)
    unresolved = next((r for r in rows if r["status"] in {"running", "unknown", "review"}), None)
    if unresolved:
        return unresolved
    return next((
        r for r in rows if r["status"] == "pending" and all(
            case.effective_status(case.check(d)) == "done" for d in json.loads(r["deps"]))), None)


def resume_notes(case, current_id):
    notes = list(case.db.execute("SELECT * FROM notes WHERE superseded=0 ORDER BY created DESC"))
    required_notes = [note_card(n) for n in notes if
                      (n["check_id"] is None and n["kind"] == "constraint") or
                      (current_id is not None and n["check_id"] == current_id)]
    optional_notes = [note_card(n) for n in notes if n["check_id"] is None and n["kind"] != "constraint"]
    return required_notes, optional_notes


def append_with_budget(packet, name, candidates, omitted, maximum):
    for item in candidates:
        packet[name].append(item)
        packet[omitted] -= 1
        if len(encode(packet)) > maximum:
            packet[name].pop()
            packet[omitted] += 1
            break


def resume(case, identity=None, maximum=6000, binding=None, experiences=None):
    rows = [dict(r) for r in case.db.execute("SELECT * FROM checks ORDER BY rowid")]
    current = select_current(case, rows, identity)
    current_id = current["id"] if current else None
    required_notes, optional_notes = resume_notes(case, current_id)
    queue = [check_card(case, r) for r in rows if
             r["id"] != current_id and r["status"] in {"pending", "failed", "blocked"}]
    inflight = [dict(r) for r in case.db.execute(
        "SELECT id,check_id,status FROM attempts WHERE status IN ('running','unknown','review') ORDER BY started")]
    packet = {
        "case_id": case.meta("case_id"),
        "revision": case.db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0],
        "config": case.meta("config"), "stored_status_counts": dict(Counter(r["status"] for r in rows)),
        "counts_are_not_evidence_revalidation": True, "in_flight": inflight,
        "required_notes": required_notes, "current": None,
        "recent_global_notes": [], "queue": [],
        "omitted_notes": len(optional_notes), "omitted_queue": len(queue),
    }
    if current:
        current_spec = json.loads(current["spec"])
        packet["current"] = dict(check_card(case, current, verify=True),
                                 spec={k: v for k, v in current_spec.items() if k != "procedure_snapshot"},
                                 dependencies=json.loads(current["deps"]),
                                 evidence=case.artifacts(current["latest_attempt"]) if current["latest_attempt"] else [])
        packet["guidance"] = check_guidance(current_spec)
        packet["next"] = ("Inspect/reconcile this existing attempt before repeating it; independent checks may proceed."
                          if current["status"] in {"running", "unknown", "review"}
                          else "Execute the current check using its specialist method and route; then inspect evidence.")
    if binding:
        packet["binding"] = binding
    last_route = case.db.execute("SELECT seq,payload FROM events WHERE kind='observation_routed' ORDER BY seq DESC LIMIT 1").fetchone()
    if last_route:
        routed = json.loads(last_route["payload"])
        observation = routed["observation"]
        if current is None or current["target"] == observation["target"]:
            packet["routing"] = {"event_seq": last_route["seq"], "target": observation["target"],
                                 "decisions_are_historical": True,
                                 "resource": observation["resource"], "decisions": routed["decisions"][:6],
                                 "omitted_decisions": max(0, len(routed["decisions"]) - 6),
                                 "details": {"kind": "events", "offset": last_route["seq"] - 1, "limit": 1}}
            if current_id == routed.get("selected") and routed.get("adapter_hint"):
                packet["routing"]["adapter_hint"] = routed["adapter_hint"]
    if experiences is not None:
        packet["experience_hints"] = []
        packet["experience_engine"] = experiences["engine"]
        packet["experience_use"] = experiences["use"]
        packet["omitted_experiences"] = experiences["omitted"] + len(experiences["items"])
    bounded(packet, maximum)
    if experiences is not None:
        append_with_budget(packet, "experience_hints", experiences["items"], "omitted_experiences", maximum)
    append_with_budget(packet, "recent_global_notes", optional_notes, "omitted_notes", maximum)
    append_with_budget(packet, "queue", queue, "omitted_queue", maximum)
    return bounded(packet, maximum)


def query(case, kind, offset=0, limit=10, identity=None, target=None):
    require(kind in {"checks", "notes", "events", "attempts"}, "Unknown query kind")
    require(offset >= 0 and 1 <= limit <= 100, "Use offset >= 0 and limit between 1 and 100")
    clauses, args = [], []
    if identity:
        require(kind != "events", "Event queries currently use pagination only")
        column = "id" if kind == "checks" else "check_id"
        clauses.append(f"{column}=?")
        args.append(case.check(identity)["id"])
    if target:
        require(kind in {"checks", "notes"}, "Target filtering supports checks and notes")
        clauses.append("target=?" if kind == "checks" else "check_id IN (SELECT id FROM checks WHERE target=?)")
        args.append(target)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    total = case.db.execute(f"SELECT COUNT(*) FROM {kind}{where}", args).fetchone()[0]
    rows = case.db.execute(f"SELECT * FROM {kind}{where} ORDER BY rowid LIMIT ? OFFSET ?",
                           args + [limit, offset]).fetchall()
    if kind == "checks":
        items = [check_card(case, dict(r)) for r in rows]
    elif kind == "notes":
        items = [dict(note_card(r), superseded=bool(r["superseded"])) for r in rows]
    else:
        items = [dict(r) for r in rows]
    return {"kind": kind, "total": total, "offset": offset, "items": items,
            "next_offset": offset + len(items) if offset + len(items) < total else None}


def write_view(case, relative, content):
    path = case.root / relative
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(path.resolve().is_relative_to(case.root), "Export path escapes case")
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def report(case):
    with case.transaction():
        checks = [check_card(case, dict(r), verify=True) for r in case.db.execute("SELECT * FROM checks ORDER BY rowid")]
        notes = [note_card(r) for r in case.db.execute("SELECT * FROM notes WHERE superseded=0 ORDER BY created")]
        events = [dict(r) for r in case.db.execute("SELECT * FROM events ORDER BY seq")]
        artifacts = [dict(r) for r in case.db.execute("SELECT * FROM artifacts ORDER BY rowid")]
        attempts = [dict(r) for r in case.db.execute("SELECT * FROM attempts ORDER BY started")]
        config = case.meta("config")
    counts = dict(Counter(r["status"] for r in checks))
    ledger_status = "completed" if checks and all(c["status"] == "done" for c in checks) else "partial"
    revision = events[-1]["seq"] if events else 0
    write_view(case, "resume.md",
               f"# Recovery pointer\n\nExport revision: {revision}\n\n"
               "Inspect fusion.py identify --case <case-directory> to recover the explicit binding.\n"
               "Then run fusion.py resume --workspace <registry> --session <session-id> --case <case-directory>.\n"
               "Do not reload all history or assume this export is current.\n")
    delivery = delivery_audit(case, checks, attempts)
    status = "review_required" if ledger_status == "completed" and not delivery["gaps"] else "partial"
    snapshot = {"status": status, "ledger_status": ledger_status,
                "completion_scope": "no_overall_completion_claim", "revision": revision,
                "counts": counts, "checks": checks, "delivery_status": delivery["status"]}
    lines = ["# Execution ledger", "", f"Status: {status}; recorded checks: {ledger_status}; revision: {revision}", "",
             "Completion refers to the recorded checks, not overall target security or confirmed vulnerabilities.",
             "", "## Objective", "", config["objective"], "", "## Scope", "", config["scope"],
             "", "## Constraints", ""] + ["- " + c for c in config.get("constraints", [])]
    lines += ["", "## Coverage", ""]
    for check in checks:
        lines += [f"- {check['id']} [{check['status']}]: {check['purpose']}",
                  "  " + (check["summary"] or "No result recorded.")]
    lines += ["", "## Observations and decisions", ""]
    for note in notes:
        lines += [f"- {note['id']} [{note['kind']}]: {note['text']}",
                  "  Evidence: " + ", ".join(note["evidence_ids"])]
    lines += ["", "## Evidence index", ""]
    for artifact in artifacts:
        lines += [f"- {artifact['id']}: {artifact['path']} (sha256: {artifact['sha256']})"]
    lines += ["", "## Delivery gaps", ""]
    lines += [f"- {gap['path']}: {gap['status']}" for gap in delivery["gaps"]]
    lines += ["", f"Registered attempts: {delivery['registered_attempts']}. "
              "Actions outside this runtime are unknown without the host trace.",
              "File presence does not verify methodology, semantic correctness or full scope coverage.",
              "See report/delivery.json for actual recorded routes and stage requirements."]
    write_view(case, "report/ledger.md", "\n".join(lines) + "\n")
    write_view(case, "report/coverage.json", encode(snapshot) + "\n")
    write_view(case, "state.json", encode(snapshot) + "\n")
    write_view(case, "events.jsonl", "".join(encode(e) + "\n" for e in events))
    write_view(case, "evidence/records.json", encode(artifacts) + "\n")
    write_view(case, "report/delivery.json", encode(dict(delivery, revision=revision)) + "\n")
    return {"status": status, "ledger_status": ledger_status,
            "completion_scope": "no_overall_completion_claim", "revision": revision,
            "counts": counts, "registered_attempts": delivery["registered_attempts"],
            "delivery_status": delivery["status"], "delivery_gaps": delivery["gaps"][:10],
            "omitted_gaps": max(0, len(delivery["gaps"]) - 10),
            "untracked_actions": delivery["untracked_actions"],
            "artifacts": ["report/ledger.md", "report/coverage.json", "report/delivery.json", "resume.md"]}
