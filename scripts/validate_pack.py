"""Validate the fusion instruction pack's offline references and task graph."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))

def unique_index(items, label):
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate IDs in {label}")
    return {item["id"]: item for item in items}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    evidence = read_json("sources.lock.json")
    source_index = unique_index(evidence["sources"], "sources")
    modules = unique_index(read_json("manifests/specialists.json")["modules"], "modules")
    execution = read_json("manifests/execution-routes.json")
    providers = unique_index(execution["providers"], "providers")
    routes = unique_index(execution["routes"], "routes")
    missions = unique_index(read_json("manifests/missions.json")["missions"], "missions")
    used_routes = set()
    for source in source_index.values():
        require(bool(re.fullmatch(r"[0-9a-f]{40}", source.get("blob_sha", ""))),
                f"Missing observed source fingerprint: {source['id']}")
    for module in modules.values():
        path = (ROOT / module["path"]).resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), f"Missing module: {module['id']}")
        require(bool(module["execution_routes"]), f"No execution routes: {module['id']}")
        for route in module["execution_routes"]:
            require(route in routes, f"{module['id']} references unknown route {route}")
            used_routes.add(route)
        for source in module["source_ids"]:
            require(source in source_index, f"Unknown source {source}")
    for route in routes.values():
        require(bool(route["choices"]), f"No providers for {route['id']}")
        for choice in route["choices"]:
            provider = providers.get(choice["provider"])
            require(provider is not None, f"Unknown provider in {route['id']}")
            require(bool(choice["tool_candidates"]), f"No tool candidates for {route['id']}")
    require(used_routes == set(routes), "Unreferenced execution routes")
    for provider in providers.values():
        if provider["id"] != "host":
            require(bool(provider["source_ids"]), f"No upstream basis: {provider['id']}")
        for source in provider["source_ids"]:
            require(source in source_index, f"Unknown provider source {source}")
    for mission in missions.values():
        for module in mission["core"] + mission["conditional"] + mission["closure"]:
            require(module in modules, f"Unknown module in {mission['id']}: {module}")
        require(mission["closure"][-1] == "fusion-report", f"No reporting closure: {mission['id']}")
        require("fusion-validate" in mission["closure"], f"No validation closure: {mission['id']}")
    example = read_json("examples/web-api-plan.json")
    require(example["example_only"] and example["status"] == "planned_not_executed",
            "Example must be clearly distinguished from an actual run")
    require(example["mission_id"] in missions, "Unknown example mission")
    work = unique_index(example["workitems"], "example workitems")
    for item in work.values():
        require(item["skill_id"] in modules, f"Unknown example skill {item['skill_id']}")
        allowed = set(modules[item["skill_id"]]["execution_routes"])
        require(set(item["execution_routes"]) <= allowed, f"Skill/route mismatch: {item['id']}")
        require(item["status"] == "pending", "Example must not claim actual completion")
        for dep in item["depends_on"]:
            require(dep in work, f"Missing dependency {dep}")
    visited, active = set(), set()
    def visit(item_id):
        require(item_id not in active, f"Dependency cycle at {item_id}")
        if item_id in visited:
            return
        active.add(item_id)
        for dep in work[item_id]["depends_on"]:
            visit(dep)
        active.remove(item_id)
        visited.add(item_id)
    for item_id in work:
        visit(item_id)
    for entry in example["not_applicable"]:
        require(entry["skill_id"] in modules and entry["reason"], "Invalid applicability record")
    link_count = 0
    for markdown in ROOT.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "C:/")):
                continue
            resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
            require(resolved.is_relative_to(ROOT) and resolved.exists(),
                    f"Broken local reference: {markdown.relative_to(ROOT)} -> {target}")
            link_count += 1
    result = {
        "status": "PASS",
        "validation_kind": "offline_references_and_dependency_graph",
        "missions": len(missions),
        "specialists": len(modules),
        "mcp_providers": len(providers) - 1,
        "execution_capabilities": len(routes),
        "upstream_projects": len({s["repo"] for s in source_index.values()}),
        "upstream_files": len(source_index),
        "example_workitems": len(work),
        "local_links_checked": link_count,
        "live_mcp_integration": "NOT_RUN",
        "model_routing_effectiveness": "NOT_MEASURED"
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        sys.exit(1)
