"""Compile evidenced observations into bounded, deduplicated executable checks."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlsplit

from fusion_store import ACTIVE, encode, manifest, reject_credentials, require, text_field, validate_spec


def procedures():
    return manifest("procedures.json", "procedures")


def procedure_card(identity):
    item = next((p for p in procedures() if p["id"] == identity), None)
    require(item is not None, "Unknown procedure_id")
    return {key: item[key] for key in ("id", "question", "steps", "acceptance", "next_on")}


def validate_controlled_refs(inputs):
    require(isinstance(inputs, dict), "inputs must be an object")
    for key in ("identity_refs", "object_refs"):
        values = inputs.get(key)
        if values is not None:
            require(isinstance(values, list) and 2 <= len(values) <= 8
                    and all(isinstance(v, str) and v.strip() for v in values)
                    and len(set(values)) == len(values), key + " requires 2-8 distinct controlled references")


def validate_observation(case, data):
    require(isinstance(data, dict), "Observation must be an object")
    for field in ("target", "target_version", "identity_ref", "resource", "source_check"):
        text_field(data.get(field), field, 1000)
    features = data.get("features")
    known = {f for p in procedures() for field in ("any_features", "requires", "unless") for f in p[field]}
    require(isinstance(features, list) and 0 < len(features) <= 32
            and all(isinstance(f, str) and f in known for f in features),
            "Use 1-32 known observed features; see observation-routing.md")
    validate_controlled_refs(data.get("inputs", {}))
    reject_credentials(data)
    evidence = data.get("evidence_ids")
    require(isinstance(evidence, list) and 0 < len(evidence) <= 20
            and all(isinstance(e, str) for e in evidence), "Observation requires evidence_ids")
    source = case.check(data["source_check"])
    source_spec = json.loads(source["spec"])
    require(source_spec["target"] == data["target"], "Observation source belongs to another target")
    require(source_spec["target_version"] == data["target_version"], "Observation target version changed")
    require(case.effective_status(source) == "done", "Review the source observation before routing")
    allowed = {a["id"] for a in case.artifacts(source["latest_attempt"])}
    require(set(evidence) <= allowed, "Evidence must belong to the source check's current reviewed attempt")
    require(len(encode(data)) <= 5000, "Keep observations compact; store raw data as evidence")
    return source


def build_spec(data, procedure, source):
    inputs = {"resource": data["resource"], "parameters": data.get("inputs", {})}
    method = {key: procedure[key] for key in ("id", "skill_id", "capability_id", "steps", "acceptance")}
    version = hashlib.sha256(encode(method).encode("utf-8")).hexdigest()[:16]
    return {"target": data["target"], "target_version": data["target_version"],
            "identity_ref": data["identity_ref"], "check_type": procedure["id"],
            "inputs": inputs, "method_version": "procedure-" + version,
            "capability_id": procedure["capability_id"], "skill_id": procedure["skill_id"],
            "procedure_id": procedure["id"], "purpose": procedure["question"],
            "procedure_snapshot": procedure_card(procedure["id"]),
            "depends_on": [source["id"]] if source else []}


def initial_http_spec(target):
    text_field(target, "entry", 1000)
    parsed = urlsplit(target)
    require(parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password,
            "Automatic entry routing currently accepts an HTTP(S) URL without embedded credentials")
    procedure = next(p for p in procedures() if p["id"] == "entry-baseline")
    data = {"target": target, "resource": target, "target_version": "unversioned", "identity_ref": "anonymous"}
    return build_spec(data, procedure, None), tool_binding(data, procedure)


def local_binding(data, procedure):
    resource = data["resource"]
    # This adapter only reads the exact bound entry. It does not follow redirects,
    # expand host scope, carry credentials, or execute generated shell text.
    if procedure["id"] == "entry-baseline" and resource == data["target"]:
        url = urlsplit(resource)
        program = shutil.which("curl") or shutil.which("curl.exe")
        if (program and url.scheme in {"http", "https"} and url.hostname
                and not url.username and not url.password and data["identity_ref"] == "anonymous"):
            return {"status": "local_callable", "provider": "host", "tool": program,
                    "argv": [program, "--disable", "--globoff", "--silent", "--show-error",
                             "--max-time", "20", "--include", "--proto", "=http,https", "--url", resource]}
    if procedure["capability_id"] in {"code.inspect", "js.source"}:
        if any(value.lower().startswith(("http://", "https://")) for value in (data["target"], resource)):
            return None
        target, path = Path(data["target"]).resolve(), Path(resource).resolve()
        program = shutil.which("rg")
        if program and target.exists() and path.is_file() and (path == target or path.is_relative_to(target)):
            return {"status": "local_callable", "provider": "host", "tool": program,
                    "argv": [program, "--no-heading", "--line-number", "--max-count", "120", "-e", ".", "--", str(path)],
                    "limit": "At most 120 matching lines; use captured positions to continue, not a whole-file review."}
    return None


def tool_binding(data, procedure, environment=None, instance=None, mcp_profile=None):
    if procedure["id"] == "candidate-review":
        return {"status": "evidence_review_required", "provider": "host", "evidence_ids": data["evidence_ids"],
                "next": "Inspect the captured evidence and its controls; this does not imply a new target call"}
    local = local_binding(data, procedure)
    if local:
        return local
    if environment is not None:
        found = environment.lookup(procedure["capability_id"], instance)
        if found["bindings"]:
            binding = dict(found["bindings"][0])
            schema = binding.get("inputSchema", {})
            if len(encode(schema)) > 1800:
                binding.pop("inputSchema", None)
                binding["schema_source"] = "Use the current host's schema for this exact tool name"
            return dict(binding, status="mcp_host_call_required", capability=procedure["capability_id"],
                        next="Bind actual target/identity context, begin, call this host tool, then record/review")
    if mcp_profile:
        from fusion_mcp import configured_binding
        binding = configured_binding(mcp_profile, procedure["capability_id"])
        if binding:
            return binding
    route = next(r for r in manifest("execution-routes.json", "routes") if r["id"] == procedure["capability_id"])
    return {"status": "tool_selection_required", "capability": procedure["capability_id"],
            "candidates": route["choices"], "candidates_are_not_ready": True,
            "next": "Use a suitable existing host tool, or supply the current-agent verified environment index"}


def classify_procedures(case, data, source):
    mission = next(m for m in manifest("missions.json", "missions") if m["id"] == case.meta("config")["mission_id"])
    allowed = set(mission["core"] + mission["conditional"] + mission["closure"])
    features = set(data["features"])
    items = sorted(procedures(), key=lambda p: (-p["priority"], p["id"]))
    decisions, candidates = [], []
    for item in items:
        hits = sorted(features.intersection(item["any_features"]))
        if not hits:
            continue
        missing = sorted(set(item["requires"]) - features)
        missing += ["inputs." + key for key in item.get("required_inputs", [])
                    if not data.get("inputs", {}).get(key)]
        excluded = sorted(features.intersection(item["unless"]))
        decision = {"procedure_id": item["id"], "matched": hits}
        if item["skill_id"] not in allowed:
            decision.update(status="outside_mission")
        elif excluded:
            decision.update(status="suppressed", observed=excluded)
        elif missing:
            decision.update(status="blocked", missing=missing)
        else:
            spec = build_spec(data, item, source)
            identity = "CHK-" + validate_spec(spec)[:24]
            row = case.db.execute("SELECT * FROM checks WHERE id=?", (identity,)).fetchone()
            state = case.effective_status(dict(row)) if row else "unplanned"
            decision.update(status=state, check_id=identity)
            if state in {"pending", "unplanned"}:
                candidates.append((item, spec, decision, row is not None))
            elif state in ACTIVE:
                decision["next"] = "Review/reconcile the existing attempt; do not replay"
            elif state != "done":
                decision["next"] = "Inspect changed evidence/dependencies or provide an explicit retest reason"
        decisions.append(decision)
    return decisions, candidates


def select_executable(data, candidates, environment, instance, mcp_profile=None):
    # A working independent route may proceed while a higher-priority route lacks
    # a prerequisite/tool. Never silently substitute a tool with different semantics.
    fallback = None
    for item, spec, decision, existing in candidates:
        binding = tool_binding(data, item, environment, instance, mcp_profile)
        candidate = (item, spec, decision, existing, binding)
        if fallback is None:
            fallback = candidate
        if binding["status"] != "tool_selection_required":
            return candidate
    return fallback


def route_observation(case, data, environment=None, instance=None, maximum=6000, mcp_profile=None):
    source = validate_observation(case, data)
    decisions, candidates = classify_procedures(case, data, source)
    selected = select_executable(data, candidates, environment, instance, mcp_profile)
    result = {"status": "no_new_executable_check" if decisions else "no_matching_method",
              "target": data["target"], "resource": data["resource"],
              "decisions": decisions, "coverage": "Only matched procedures; not a claim of complete assessment"}
    if selected:
        item, spec, decision, existing, binding = selected
        if existing:
            spec = json.loads(case.check(decision["check_id"])["spec"])
        result.update(status="planned_not_executed", check_id=decision["check_id"],
                      selected=spec["procedure_snapshot"],
                      check={k: v for k, v in spec.items() if k != "procedure_snapshot"}, execution=binding,
                      next="Use this concrete method; inspect actual results, then route only newly supported facts")
    require(len(encode(result)) <= maximum, "context_budget_exceeded: narrow observations or increase --max-chars")
    if selected:
        if not existing:
            case.plan([spec])
            decision["status"] = "pending"
    with case.transaction():
        adapter = result.get("execution", {})
        hint = ({k: adapter[k] for k in ("provider", "name", "profile", "target_argument", "status")}
                if adapter.get("status") == "mcp_preflight_required" else None)
        case.event("observation_routed", source["id"], {"observation": data, "decisions": decisions,
                                                       "selected": result.get("check_id"), "adapter_hint": hint})
    return result


def dispatch_route(args, case, run_local):
    environment = None
    if args.environment:
        from fusion_environment import Environment
        require(args.agent and args.instance, "Routing environment requires agent and instance")
        environment = Environment(args.environment, args.agent)
    else:
        require(not args.agent and not args.instance, "Agent/instance require an environment index")
    # Reserve capture receipt space before execution; budget errors must not hide a call.
    budget = args.max_chars - 1600 if args.execute_local else args.max_chars
    result = route_observation(case, args.observation, environment, args.instance, budget,
                               getattr(args, "mcp_profile", None))
    if args.execute_local and result.get("execution", {}).get("status") == "local_callable":
        execution_args = argparse.Namespace(check=result["check_id"], argv=result["execution"]["argv"],
                                            timeout=30, cwd=None, retest_reason="")
        result["call"] = run_local(case, execution_args)
        result["status"] = result["call"].get("status", result["call"].get("decision"))
    return result
