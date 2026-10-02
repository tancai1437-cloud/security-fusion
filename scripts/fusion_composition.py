"""Compose existing method, tool capability and event-specific runtime contracts."""
from fusion_store import PACK, digest_file, manifest, require
from fusion_methods import specialist_card, execution_route

PHASES = ("execute", "recover", "review", "deliver")
HOSTS = ("dsh", "cli", "text")


def component_card(identity):
    item = next((x for x in manifest("components.json", "components") if x["id"] == identity), None)
    require(item is not None, "Unknown component")
    return item


def compose(skill, capability, phase="execute", host="cli"):
    require(phase in PHASES and host in HOSTS, "Unknown composition phase or host")
    card = specialist_card(skill)
    require(capability in card["allowed_capabilities"], "Capability does not belong to the selected specialist")
    components = [c for c in manifest("components.json", "components")
                  if phase in c["phases"] and c["kind"] in {"runtime", "quality"}]
    # Full catalogs, upstream descriptions and unrelated methods stay off the model hot path.
    runtime = {"phase": phase, "components": [c["id"] for c in components],
               "host": host, "binding": {"dsh": "requires_installed_host_adapter",
               "cli": "managed_commands_only", "text": "instructions_only_no_hooks"}[host],
               "activation": "composition does not attest installation, execute tools, or prove health"}
    phase_rule = {
        "execute": "取得当前问题所需证据；沿既有接口自动留痕，不逐个调用管理组件。",
        "recover": "先核对未决调用和节点复盘，再复用有效前置结果；缺口按证据指针读取。",
        "review": "结论/转向/阻塞时复盘，不每次读文件都复盘；证据不足保留未决。",
        "deliver": "沿当前专项交付；证据与完成条件有缺口时明确部分完成。",
    }
    runtime["rule"] = phase_rule[phase]
    return {"status": "composition_only", "target_action_executed": False,
            "composition_sha256": digest_file(PACK / "manifests/components.json"),
            "method": card,
            "execution": execution_route({"skill_id": skill, "capability_id": capability}),
            "runtime": runtime}
