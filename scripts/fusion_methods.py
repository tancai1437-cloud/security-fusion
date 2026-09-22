"""Deliver the actual specialist instructions, from their single Markdown source."""
from pathlib import PurePosixPath
import re

from fusion_store import PACK, digest_file, manifest, require


def specialist_card(skill):
    module = next((m for m in manifest("specialists.json", "modules") if m["id"] == skill), None)
    require(module is not None, "Unknown specialist")
    source = (PACK / module["path"]).resolve()
    require(source.is_relative_to(PACK), "Specialist source escapes skill")
    text = source.read_text(encoding="utf-8")
    # These labels are the pack's authoring contract, checked by validate_pack.
    # Do not maintain a second, gradually diverging summary of each methodology.
    method = re.search(r"^输入：[^\n]*\n\n(.*?)\n执行路由：", text, re.M | re.S)
    completion = re.search(r"^完成条件：(.+)$", text, re.M)
    outputs = re.search(r"^阶段输出[^\n]+", text, re.M)
    require(method and completion and outputs, "Specialist is missing method/completion/output sections")
    names = [item.split("：", 1)[0] for item in re.findall(r"`([^`]+)`", outputs[0])]
    require(bool(names), "Specialist has no stage outputs")
    paths = []
    for name in names:
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and ".." not in relative.parts and ":" not in name
                and "\\" not in name, "Invalid specialist output path")
        paths.append(name if skill == "fusion-report" else f"specialists/{skill}/{name}")
    return {"skill_id": skill, "title": module["title"], "source": str(source),
            "source_sha256": digest_file(source), "method": method[1].strip(),
            "completion": completion[1].strip(), "stage_outputs": paths,
            "allowed_capabilities": module["execution_routes"]}


def execution_route(spec, provider=None, tool=None):
    route = next((r for r in manifest("execution-routes.json", "routes")
                  if r["id"] == spec["capability_id"]), None)
    require(route is not None, "Unknown capability")
    result = {"skill_id": spec["skill_id"], "capability_id": route["id"],
              "required_input": route["required_input"], "expected_output": route["expected_output"]}
    if provider is not None:
        result.update(provider=provider, tool=tool)
    return result


def check_guidance(spec):
    return {"specialist": specialist_card(spec["skill_id"]), "route": execution_route(spec)}
