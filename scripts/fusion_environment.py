"""Private host capability index; discovery is never evidence of a usable tool."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import time
from urllib.parse import urlsplit
import uuid

from fusion_store import PACK, encode, read_json, require, digest_file, text_field


def fingerprint(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def machine_id():
    # A cooperative namespace, not authentication or a globally unique hardware ID.
    return fingerprint([platform.node(), platform.system(), platform.machine(), str(Path.home())])


def stamp(path):
    path = Path(path).resolve()
    info = path.stat()
    require(path.is_file(), "Expected a file")
    return {"path": str(path), "size": info.st_size, "mtime_ns": info.st_mtime_ns}


def fresh_file(item):
    try:
        return stamp(item["path"]) == item
    except OSError:
        return False


def recipes():
    return {p["id"]: p for p in read_json(PACK / "manifests/environment-providers.json")["providers"]}


def routes():
    return {r["id"]: r for r in read_json(PACK / "manifests/execution-routes.json")["routes"]}


def matches(tool, candidate, provider):
    if provider == "host":
        return tool.get("native_alias") == candidate
    name = tool["name"]
    return name == candidate or name.endswith("__" + candidate) or name.endswith("_" + candidate)


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not path.is_symlink(), "Refusing a symlink output")
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def validate_variable_refs(spec):
    for field in ("env_refs", "header_refs"):
        require(isinstance(spec.get(field, {}), dict), field + " must be an object")
        for key, variable in spec.get(field, {}).items():
            require(isinstance(key, str) and re.fullmatch(r"[A-Za-z0-9_-]+", key), "Invalid environment/header name")
            require(isinstance(variable, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", variable), "Use variable names, not secret values")


def validate_stdio(spec, watched):
    executable = text_field(spec.get("command"), "command")
    resolved = shutil.which(executable)
    require(resolved is not None, "Executable missing; install or supply its actual absolute path")
    spec = dict(spec, command=str(Path(resolved).resolve()))
    args = spec.get("args", [])
    require(isinstance(args, list) and all(isinstance(a, str) for a in args), "args must be strings")
    require(not any("$HOME" in a or a.startswith("~/") for a in args), "Resolve shell paths before registration")
    watched.append(spec["command"])
    watched.extend(a for a in args if Path(a).is_absolute() and Path(a).is_file())
    if spec.get("cwd"):
        require(Path(spec["cwd"]).is_absolute() and Path(spec["cwd"]).is_dir(), "cwd must be an existing absolute directory")
    require(not spec.get("header_refs") and "url" not in spec, "HTTP fields cannot configure stdio")
    return spec


def validate_connection(provider, spec):
    require(isinstance(spec, dict), "Connection must be an object")
    allowed = {"transport", "command", "args", "cwd", "env_refs", "url", "header_refs", "watch_files"}
    require(set(spec) <= allowed, "Unknown connection fields; credentials must use environment references")
    transport = spec.get("transport")
    require(transport in {"native", "stdio", "streamable-http"}, "Unsupported transport; SSE needs an upstream stdio proxy")
    require((provider == "host") == (transport == "native"), "Only host uses native transport")
    require(isinstance(spec.get("watch_files", []), list), "watch_files must be a list")
    watched = list(spec.get("watch_files", []))
    require(all(isinstance(p, str) and Path(p).is_absolute() for p in watched), "watch_files require absolute paths")
    validate_variable_refs(spec)
    if transport == "stdio":
        spec = validate_stdio(spec, watched)
    elif transport == "streamable-http":
        parsed = urlsplit(text_field(spec.get("url"), "url"))
        require(parsed.scheme in {"http", "https"} and parsed.hostname, "Invalid MCP URL")
        require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                "Keep credentials out of URLs; use header_refs")
        require(not any(k in spec for k in ("command", "args", "cwd", "env_refs")), "stdio fields cannot configure HTTP")
    else:
        require(set(spec) <= {"transport", "watch_files"}, "Native transport has no subprocess configuration")
    return spec, [stamp(p) for p in sorted(set(watched))]


def validate_smoke(check, tool_index, provider, root):
    capability, name = check.get("capability"), check.get("tool")
    require(capability in routes() and name in tool_index, "Unknown capability or unobserved tool")
    tool = tool_index[name]
    candidates = [c for c in routes()[capability]["choices"] if c["provider"] == provider]
    require(any(matches(tool, c, provider) for choice in candidates for c in choice["tool_candidates"]),
            "Observed tool does not implement the selected route")
    require(check.get("outcome") == "pass", "A failed smoke check cannot become ready")
    text_field(check.get("validation"), "semantic validation", 1200)
    require(check.get("scope") in {"local_fixture", "authorized_context"}, "Record the actual smoke scope")
    text_field(check.get("fixture_ref"), "fixture_ref", 500)
    artifact = Path(check["result_file"]).resolve()
    require(artifact.is_relative_to(root) and artifact.is_file(), "Save smoke results in the private environment directory")
    require(artifact.stat().st_size <= 8 * 1024 * 1024, "Smoke result too large; use a small fixture")
    result = read_json(artifact)
    require(isinstance(result, dict) and not result.get("isError") and result.get("error") is None,
            "Tool error cannot become ready")
    require(isinstance(result.get("content"), list) or isinstance(result.get("structuredContent"), dict),
            "Supply the actual tool result envelope")
    return {"capability": capability, "tool": tool, "result_file": str(artifact),
            "result_sha256": digest_file(artifact), "validation": check["validation"],
            "scope": check["scope"], "fixture_ref": check["fixture_ref"]}


class Environment:
    def __init__(self, root, agent):
        self.root = Path(root).resolve()
        require(not self.root.is_relative_to(PACK), "Environment data belongs outside the installed Skill")
        require(agent in {"dsh", "opencode", "pi"}, "Specify the current host agent")
        self.agent = agent
        self.path = self.root / "environment.json"
        require(not self.path.is_symlink(), "Refusing a symlink index")
        self.data = read_json(self.path) if self.path.exists() else {
            "schema_version": 1, "machine": machine_id(), "agent": agent,
            "root": str(self.root), "providers": {}, "scan": {}, "events": []}
        require(self.data.get("schema_version") == 1, "Unsupported environment index")
        require(self.data.get("machine") == machine_id() and self.data.get("agent") == agent
                and self.data.get("root") == str(self.root), "Environment belongs to a different machine, agent or path")

    def save(self, kind, detail):
        # Full action history is on disk, never included in the model-facing index.
        self.data["events"].append({"at": time.time(), "kind": kind, "detail": detail})
        atomic_write(self.path, encode(self.data) + "\n")

    def scan(self, search_roots=()):
        roots = [Path(p).expanduser().resolve() for p in search_roots]
        roots += [self.root / "providers", Path.home() / "tools", Path.home() / ".local/share/security-fusion/providers"]
        found = {}
        for provider, recipe in recipes().items():
            executables = {name: shutil.which(name) for name in recipe["executables"]}
            files = set()
            for root in roots:
                for marker in recipe["markers"]:
                    for candidate in (root / marker, root / provider / marker, root / (provider + "-mcp-server") / marker,
                                      root / ("hexstrike-ai" if provider == "hexstrike" else provider + "-mcp") / marker):
                        if candidate.is_file():
                            files.add(str(candidate.resolve()))
            found[provider] = {"executables": executables, "entrypoint_candidates": sorted(files),
                               "status": "detected_unverified" if files or any(executables.values()) else "not_detected"}
        self.data["scan"] = {"at": time.time(), "providers": found, "search_roots": list(map(str, roots))}
        self.save("scan", {"provider_count": len(found)})
        return {"status": "scanned", "providers": {p: {"found": [n for n, path in v["executables"].items() if path],
                "missing": [n for n, path in v["executables"].items() if not path],
                "entrypoint_candidates": v["entrypoint_candidates"]} for p, v in found.items()},
                "note": "PATH and bounded directory discovery only; absence is not proof of system-wide absence"}

    def register(self, provider, spec):
        require(provider in recipes(), "Unknown provider")
        spec, watched = validate_connection(provider, spec)
        digest = fingerprint(spec)
        previous = self.data["providers"].get(provider)
        if previous and previous["connection_sha256"] == digest and previous["watched"] == watched:
            return {"status": "unchanged", "connection_sha256": digest}
        self.data["providers"][provider] = {"connection": spec, "connection_sha256": digest,
                "watched": watched, "verified": {}, "blocked": None}
        self.save("register", {"provider": provider, "connection_sha256": digest})
        return {"status": "registered_not_verified", "connection_sha256": digest}

    def verify(self, provider, receipt, instance, valid_for=3600):
        require(isinstance(valid_for, (int, float)) and math.isfinite(valid_for) and 1 <= valid_for <= 86400,
                "Verification TTL must be between 1 and 86400 seconds")
        entry = self.data["providers"].get(provider)
        require(entry is not None, "Register connection before verification")
        require(all(fresh_file(f) for f in entry["watched"]), "Executable/configuration changed; register again")
        require(receipt.get("instance") == instance and bool(instance), "Receipt must be from this host instance")
        require(receipt.get("connection_sha256") == entry["connection_sha256"], "Receipt refers to another connection")
        observed = receipt.get("observed_at")
        require(isinstance(observed, (int, float)) and math.isfinite(observed) and -30 <= time.time() - observed <= 300,
                "Fresh host observation required (within 300 seconds)")
        observed_tools = receipt.get("tools")
        require(isinstance(observed_tools, list) and 0 < len(observed_tools) <= 512, "Supply actual host tool schemas")
        tool_index = {}
        for tool in observed_tools:
            require(isinstance(tool, dict) and isinstance(tool.get("inputSchema"), dict), "Tool needs inputSchema")
            name = text_field(tool.get("name"), "tool name", 256)
            require(name not in tool_index, "Duplicate observed tool")
            tool_index[name] = tool
        checks = receipt.get("checks")
        require(isinstance(checks, list) and 0 < len(checks) <= 100, "Supply actual per-capability smoke checks")
        verified = {}
        for check in checks:
            item = validate_smoke(check, tool_index, provider, self.root)
            key = item["capability"] + ":" + item["tool"]["name"]
            require(key not in verified, "Duplicate capability/tool check")
            verified[key] = dict(item, instance=instance, connection_sha256=entry["connection_sha256"],
                expires=observed + valid_for, observed_at=observed, manifest_sha256=fingerprint(routes()))
        entry["verified"].update(verified)
        entry["blocked"] = None
        self.data.setdefault("blockers", {}).pop(provider, None)
        self.save("verify", {"provider": provider, "instance": instance, "bindings": list(verified)})
        return {"status": "verified", "bindings": len(verified), "basis": "actual_host_results_and_agent_semantic_review"}

    def invalidate(self, provider, reason):
        require(provider in recipes(), "Unknown provider")
        reason = text_field(reason, "reason", 1000)
        self.data.setdefault("blockers", {})[provider] = reason
        if provider in self.data["providers"]:
            self.data["providers"][provider]["verified"] = {}
            self.data["providers"][provider]["blocked"] = reason
        self.save("invalidate", {"provider": provider, "reason": reason})
        return {"status": "blocked", "provider": provider, "reason": reason}

    def binding_state(self, entry, checked, instance):
        if entry["blocked"]:
            return "blocked"
        if checked["instance"] != instance:
            return "host_verification_required"
        if checked["expires"] <= time.time():
            return "expired"
        if checked["manifest_sha256"] != fingerprint(routes()) or not all(fresh_file(f) for f in entry["watched"]):
            return "configuration_changed"
        path = Path(checked["result_file"])
        try:
            if not path.is_file() or digest_file(path) != checked["result_sha256"]:
                return "evidence_invalid"
        except OSError:
            return "evidence_invalid"
        return "ready"

    def lookup(self, capability, instance, schemas=True):
        require(capability in routes(), "Unknown capability")
        text_field(instance, "host instance", 256)
        bindings, gaps = [], []
        for choice in routes()[capability]["choices"]:
            provider = choice["provider"]
            entry = self.data["providers"].get(provider)
            checked = [v for v in entry["verified"].values() if v["capability"] == capability] if entry else []
            states = []
            for item in checked:
                status = self.binding_state(entry, item, instance)
                states.append(status)
                if status == "ready":
                    binding = {"provider": provider, "name": item["tool"]["name"],
                        "status": "ready", "observed_at": item["observed_at"], "expires": item["expires"],
                        "verification_scope": item["scope"], "target_context": "must_bind_per_case"}
                    if schemas:
                        binding["inputSchema"] = item["tool"]["inputSchema"]
                    bindings.append(binding)
            if not any(s == "ready" for s in states):
                gaps.append({"provider": provider, "status": states[0] if states else
                             ("blocked" if provider in self.data.get("blockers", {}) else
                              "registered_not_verified" if entry else "unregistered"),
                             "reason": self.data.get("blockers", {}).get(provider) or (entry["blocked"] if entry else None)})
        return {"capability": capability, "status": "ready" if bindings else "setup_required", "bindings": bindings,
                "gaps": gaps, "guarantee": "verified fixture only; target permissions/context still apply"}

    def plan(self, capabilities, instance):
        require(bool(capabilities), "Choose current task capabilities; do not install every alternative")
        items = [self.lookup(c, instance, schemas=False) for c in dict.fromkeys(capabilities)]
        needed = set()
        for item in items:
            if item["status"] == "ready":
                continue
            choices = routes()[item["capability"]]["choices"]
            candidates = [c for c in choices if c["provider"] not in self.data.get("blockers", {})] or choices
            # Prefer an existing current-agent connection over installing a new alternative.
            fallback = "ghidra" if any(c["provider"] == "ghidra" for c in candidates) else candidates[0]["provider"]
            generic = {"python", "python3", "java", "node", "npx", "pnpm", "uv", "git", "rg"}
            for choice in candidates:
                detected = self.data.get("scan", {}).get("providers", {}).get(choice["provider"], {})
                if detected.get("entrypoint_candidates") or any(path for name, path in detected.get("executables", {}).items() if name not in generic):
                    fallback = choice["provider"]
                    break
            provider = next((c["provider"] for c in candidates if c["provider"] in self.data["providers"]), fallback)
            needed.add(provider)
        return {"status": "ready" if all(i["status"] == "ready" for i in items) else "reconcile_required",
                "capabilities": items, "providers_to_reconcile": sorted(needed),
                "next": "Automatically reuse/install, register, attach to current host, smoke-test and verify; repeat plan"}
