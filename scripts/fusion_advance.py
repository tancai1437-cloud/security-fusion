"""Review one observed result and route its facts, without retyping ledger metadata."""
import json

from fusion_routing import dispatch_route
from fusion_store import read_json, require


def advance(args, case, run_local):
    source = case.check(args.check)
    spec = json.loads(source["spec"])
    require(source["latest_attempt"], "Source check has no captured result")
    require(case.effective_status(source) in {"review", "done"}, "Inspect/reconcile source before advancing")
    # Derive metadata from the explicitly selected source, never a global "last check".
    data = {"target": spec["target"], "target_version": spec["target_version"],
            "identity_ref": args.identity or spec["identity_ref"],
            "resource": args.resource or spec["inputs"].get("resource", spec["target"]),
            "source_check": source["id"],
            "evidence_ids": [a["id"] for a in case.artifacts(source["latest_attempt"])],
            "features": args.feature, "inputs": read_json(args.inputs) if args.inputs else {}}
    require(args.summary is not None or case.effective_status(source) == "done",
            "Read the captured evidence, then supply --summary to review it")
    require(not args.environment or (args.agent and args.instance), "Environment requires agent and instance")
    require(args.environment or not (args.agent or args.instance), "Agent/instance require environment")
    # Review is an explicit caller judgement, never inferred from exit code or tool success.
    if case.effective_status(source) == "review":
        from fusion_routing import validate_controlled_refs, procedures
        from fusion_store import encode, reject_credentials, text_field
        known = {f for p in procedures() for key in ("any_features", "requires", "unless") for f in p[key]}
        require(0 < len(args.feature) <= 32 and all(f in known for f in args.feature), "Unknown observed feature")
        validate_controlled_refs(data["inputs"])
        reject_credentials(data)
        text_field(data["resource"], "resource", 1000)
        text_field(data["identity_ref"], "identity_ref", 1000)
        require(len(encode(data)) <= 5000, "Keep observations compact")
        require(args.max_chars >= 6000, "advance requires at least the default 6000-character budget")
        # Remaining route failures do not undo a valid, explicit review; callers can retry routing.
        case.review(source["latest_attempt"], "done", args.summary, args.valid_for)
    args.observation = data
    args.max_chars -= 100  # Reserve the explicit source receipt within the caller's budget.
    result = dispatch_route(args, case, run_local)
    result["source_check"] = source["id"]
    return result
