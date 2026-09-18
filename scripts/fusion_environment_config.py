"""Generate managed MCP overlays without overwriting a user's agent settings."""
import json

from fusion_environment import atomic_write
from fusion_store import digest_file, require


def dsh_entry(provider, connection):
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    lines = ["    - id: " + quote("security-fusion-" + provider),
             "      name: '@deepseek-ai/dsh-mcp-client'", "      config:",
             "        serverName: " + quote(provider), "        transport: " + quote(connection["transport"])]
    for key in ("command", "args", "cwd", "url"):
        if key in connection:
            lines.append("        " + key + ": " + quote(connection[key]))
    for source, field in (("env_refs", "env"), ("header_refs", "headers")):
        if connection.get(source):
            lines.append("        " + field + ":")
            for name, variable in sorted(connection[source].items()):
                lines.append("          " + quote(name) + ": !!js process.env[" + quote(variable) + "]")
    lines.append("        toolCallTimeoutMs: 120000")
    return "\n".join(lines)


def render(agent, entries):
    if agent == "dsh":
        return "dsh-mcp.cordis.yml", "- insert:\n" + "\n".join(dsh_entry(p, c) for p, c in entries.items()) + "\n"
    configs = {}
    for provider, connection in entries.items():
        local = connection["transport"] == "stdio"
        if agent == "opencode":
            config = {"type": "local" if local else "remote", "enabled": True}
            if local:
                config["command"] = [connection["command"], *connection.get("args", [])]
                if "cwd" in connection:
                    config["cwd"] = connection["cwd"]
            else:
                config["url"] = connection["url"]
            for source, field in (("env_refs", "environment"), ("header_refs", "headers")):
                if connection.get(source):
                    config[field] = {k: "{env:" + v + "}" for k, v in connection[source].items()}
        else:
            require(not connection.get("env_refs") and not connection.get("header_refs"),
                    "Pi secret configuration must use the installed adapter's documented authentication mechanism")
            config = {k: connection[k] for k in ("command", "args", "cwd", "url") if k in connection}
        configs[provider] = config
    document = {"$schema": "https://opencode.ai/config.json", "mcp": configs} if agent == "opencode" else {"mcpServers": configs}
    return ("opencode-mcp.json" if agent == "opencode" else "pi-mcp.json"), json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def configure(environment, providers):
    require(bool(providers), "Select the providers needed for this task")
    entries = {}
    for provider in dict.fromkeys(providers):
        require(provider in environment.data["providers"], "Register the actual connection first: " + provider)
        if provider != "host":
            entries[provider] = environment.data["providers"][provider]["connection"]
    require(bool(entries), "Native host tools need no MCP configuration")
    name, content = render(environment.agent, entries)
    target = environment.root / "managed" / name
    require(target.parent.resolve().is_relative_to(environment.root), "Managed directory escapes environment")
    previous = environment.data.get("generated", {}).get(name)
    backup = None
    if target.exists():
        require(not target.is_symlink() and previous and digest_file(target) == previous["sha256"],
                "Managed output was changed outside bootstrap; preserve and reconcile it first")
        if target.read_text(encoding="utf-8") == content:
            return {"status": "unchanged_not_live_verified", "path": str(target)}
        backup = environment.root / "backups" / (previous["sha256"] + "-" + name)
        require(backup.parent.resolve().is_relative_to(environment.root), "Backup directory escapes environment")
        atomic_write(backup, target.read_text(encoding="utf-8"))
    atomic_write(target, content)
    # Even a generated overlay may be loaded live; prior receipts cannot prove the new configuration.
    affected = set(entries) | set(previous["providers"] if previous else [])
    for provider in affected:
        environment.data["providers"][provider]["verified"] = {}
    environment.data.setdefault("generated", {})[name] = {"sha256": digest_file(target), "providers": list(entries)}
    environment.save("configure", {"path": str(target), "backup": str(backup) if backup else None})
    return {"status": "configuration_generated_not_connected", "path": str(target),
            "backup": str(backup) if backup else None,
            "next": "Agent must merge/attach this overlay to its current host, reload, then verify actual calls"}
