"""Small stdio MCP execution adapter. No host configuration changes or installs."""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

from fusion_methods import execution_route
from fusion_store import FusionError, encode, manifest, read_json, require, text_field
from fusion_views import write_view


VERSIONS = {"2025-06-18", "2025-03-26", "2024-11-05"}
MAX_MESSAGE = 8 * 1024 * 1024


def configured_binding(profile_path, capability):
    """Expose only a selected adapter, never its command/env or a fabricated readiness claim."""
    profile = read_json(profile_path)
    require(isinstance(profile, dict), "MCP profile must be an object")
    require(profile.get("transport") == "stdio" and profile.get("context_mode") == "explicit-target",
            "Adapter requires stdio with explicit-target context; use host protocol for stateful tools")
    bindings = profile.get("bindings")
    require(isinstance(bindings, dict), "Profile requires capability bindings")
    binding = bindings.get(capability)
    if binding is None:
        return None
    require(isinstance(binding, dict), "Capability binding must be an object")
    route = next(r for r in manifest("execution-routes.json", "routes") if r["id"] == capability)
    provider = profile.get("provider")
    require(provider != "host" and provider in {c["provider"] for c in route["choices"]},
            "Provider is not mapped to this capability")
    return {"status": "mcp_preflight_required", "provider": provider,
            "name": text_field(binding.get("tool"), "tool", 300), "capability": capability,
            "target_argument": text_field(binding.get("target_argument"), "target_argument", 120),
            "profile": str(Path(profile_path).resolve()),
            "next": "mcp-run --check <check_id> --profile <profile> --arguments <actual-arguments.json>; live preflight occurs before call"}


class StdioClient:
    """One connection per explicit-target call; never inherit a host's selected page/project."""

    def __init__(self, command, cwd, env, stderr, timeout):
        self.deadline = time.monotonic() + timeout
        self.messages = queue.Queue(maxsize=32)
        self.stopped = threading.Event()
        self.serial = 0
        self.last_response = None
        self.process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=stderr, shell=False, bufsize=0)
        self.output = io.BufferedReader(self.process.stdout)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            while not self.stopped.is_set():
                line = self.output.readline(MAX_MESSAGE + 1)
                if not line:
                    raise FusionError("MCP connection closed")
                require(len(line) <= MAX_MESSAGE and line.endswith(b"\n"), "MCP message exceeds limit")
                message = json.loads(line.decode("utf-8"))
                require(isinstance(message, dict) and message.get("jsonrpc") == "2.0", "Invalid MCP message")
                while not self.stopped.is_set():
                    try:
                        self.messages.put(message, timeout=0.1)
                        break
                    except queue.Full:
                        pass
        except (OSError, ValueError, UnicodeError) as exc:
            while not self.stopped.is_set():
                try:
                    self.messages.put(FusionError("MCP read failed: " + type(exc).__name__), timeout=0.1)
                    break
                except queue.Full:
                    pass

    def send(self, message):
        payload = (encode(dict(jsonrpc="2.0", **message)) + "\n").encode("utf-8")
        require(len(payload) <= 65536, "Keep MCP arguments small; use artifact references")
        outcome = queue.Queue(maxsize=1)
        def write():
            try:
                remaining = memoryview(payload)
                while remaining:
                    count = self.process.stdin.write(remaining)
                    if not count:
                        raise OSError("MCP input closed")
                    remaining = remaining[count:]
                outcome.put(None)
            except OSError as exc:
                outcome.put(exc)
        sender = threading.Thread(target=write, daemon=True)
        sender.start()
        try:
            result = outcome.get(timeout=max(0.001, self.deadline - time.monotonic()))
        except queue.Empty as exc:
            self.process.kill()
            raise FusionError("MCP send timed out") from exc
        if result is not None:
            raise result

    def request(self, method, params):
        self.serial += 1
        identity = self.serial
        self.send({"id": identity, "method": method, "params": params})
        while True:
            remaining = self.deadline - time.monotonic()
            require(remaining > 0, "MCP request timed out")
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise FusionError("MCP request timed out") from exc
            if isinstance(message, Exception):
                raise message
            if "method" in message:
                if "id" in message:
                    # No sampling, roots, elicitation, or nested agents are advertised.
                    reply = {"id": message["id"], "result": {}} if message["method"] == "ping" else {
                        "id": message["id"], "error": {"code": -32601, "message": "Unsupported client request"}}
                    self.send(reply)
                continue
            require(message.get("id") == identity, "Unexpected MCP response ID")
            self.last_response = message
            if "error" in message:
                raise FusionError("MCP protocol error; inspect private response")
            require(isinstance(message.get("result"), dict), "Invalid MCP result")
            return message["result"]

    def tool(self, name):
        hello = self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                             "clientInfo": {"name": "security-fusion", "version": "1"}})
        require(hello.get("protocolVersion") in VERSIONS, "Unsupported MCP protocol version")
        require(isinstance(hello.get("capabilities"), dict) and "tools" in hello["capabilities"],
                "MCP server does not advertise tools")
        self.send({"method": "notifications/initialized"})
        cursor, seen = None, set()
        for _ in range(20):
            page = self.request("tools/list", {"cursor": cursor} if cursor else {})
            require(isinstance(page.get("tools"), list), "Invalid MCP tool list")
            for tool in page["tools"]:
                require(isinstance(tool, dict), "Invalid MCP tool entry")
                if tool.get("name") == name:
                    require(isinstance(tool.get("inputSchema"), dict), "Missing tool inputSchema")
                    return tool
            cursor = page.get("nextCursor")
            if not cursor:
                break
            require(isinstance(cursor, str) and cursor not in seen, "Invalid MCP pagination cursor")
            seen.add(cursor)
        raise FusionError("Configured tool not found in this connection's tools/list")

    def close(self):
        self.stopped.set()
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=1)
        self.reader.join(timeout=1)
        if not self.reader.is_alive():
            self.output.close()


def profile_call(case, args):
    profile, arguments = read_json(args.profile), read_json(args.arguments)
    require(isinstance(profile, dict) and isinstance(arguments, dict), "Profile and arguments must be objects")
    require(profile.get("transport") == "stdio" and profile.get("context_mode") == "explicit-target",
            "Adapter requires stdio with explicit-target context; use host protocol for stateful tools")
    command = profile.get("command")
    require(isinstance(command, list) and command and all(isinstance(v, str) and v for v in command),
            "Profile command must be an argv list for an already installed server")
    spec = json.loads(case.check(args.check)["spec"])
    provider = text_field(profile.get("provider"), "provider", 120)
    route = next(r for r in manifest("execution-routes.json", "routes") if r["id"] == spec["capability_id"])
    require(provider != "host" and provider in {c["provider"] for c in route["choices"]},
            "Provider is not mapped to this capability")
    bindings = profile.get("bindings")
    require(isinstance(bindings, dict), "Profile requires capability bindings")
    binding = bindings.get(spec["capability_id"])
    require(isinstance(binding, dict), "Profile has no binding for this check's capability")
    name = text_field(binding.get("tool"), "tool", 300)
    target_arg = text_field(binding.get("target_argument"), "target_argument", 120)
    require(arguments.get(target_arg) == spec["target"], "MCP target argument must equal the bound check target")
    if spec["identity_ref"] != "anonymous":
        identity_arg = text_field(binding.get("identity_argument"), "identity_argument", 120)
        require(arguments.get(identity_arg) == spec["identity_ref"], "MCP identity argument does not match check")
    require(math.isfinite(args.timeout) and 0 < args.timeout <= 3600, "MCP timeout must be in (0, 3600]")
    require(len(encode(arguments)) <= 32000, "Keep MCP arguments small")
    cwd = Path(profile.get("cwd", Path(args.profile).resolve().parent)).resolve()
    require(cwd.is_dir(), "MCP working directory does not exist")
    env = os.environ.copy()
    require("env" not in profile, "Use env_refs instead of inline environment credentials")
    refs = profile.get("env_refs", {})
    require(isinstance(refs, dict), "env_refs must be an object")
    for destination, source in refs.items():
        text_field(destination, "environment name", 160)
        require(isinstance(source, str) and source in os.environ, "Required MCP environment variable is missing")
        env[destination] = os.environ[source]
    digest = hashlib.sha256(encode({"profile": profile, "arguments": arguments,
                                   "env_refs": {k: env[k] for k in refs}, "cwd": str(cwd)}).encode()).hexdigest()
    return spec, provider, name, command, arguments, cwd, env, digest, target_arg


def mcp_run(case, args):
    spec, provider, name, command, arguments, cwd, env, digest, target_arg = profile_call(case, args)
    route = execution_route(spec, provider, name)
    receipt = case.begin(args.check, provider, name, args.retest_reason, digest)
    if receipt["decision"] != "execute":
        return dict(receipt, route=route)
    attempt = receipt["attempt_id"]
    capture = case.root / "captures" / attempt
    capture.mkdir(mode=0o700, parents=True, exist_ok=False)
    require(capture.resolve().is_relative_to(case.root), "Capture path escapes case")
    client, sent, state = None, False, "blocked"
    detail = "MCP preflight did not complete"
    paths = []
    started = time.time()
    try:
        with (capture / "stderr").open("xb") as stderr:
            if os.name != "nt":
                os.chmod(capture / "stderr", 0o600)
            paths.append(capture / "stderr")
            try:
                client = StdioClient(command, cwd, env, stderr, args.timeout)
                tool = client.tool(name)
                schema = tool["inputSchema"]
                require(schema.get("type") == "object", "Unsupported MCP input schema")
                require(target_arg in schema.get("properties", {}), "Target argument absent from live tool schema")
                require(all(k in arguments for k in schema.get("required", [])), "Missing required MCP arguments")
                write_view(case, f"captures/{attempt}/tool.json", encode(tool) + "\n")
                paths.append(capture / "tool.json")
                # Persist intent before sending. Interruption from here is unresolved, never auto-retried.
                with case.transaction():
                    case.event("mcp_call_sending", attempt, {"tool": name, "invocation_sha256": digest,
                                                           "context_mode": "explicit-target"})
                sent = True
                result = client.request("tools/call", {"name": name, "arguments": arguments})
                write_view(case, f"captures/{attempt}/result.json", encode(result) + "\n")
                paths.append(capture / "result.json")
                require("task" not in result and isinstance(result.get("content"), list),
                        "Incomplete/task MCP result; reconcile before retrying")
                require("isError" not in result or isinstance(result["isError"], bool), "Invalid MCP isError")
                state = "failed" if result.get("isError") or result.get("error") is not None else "review"
                detail = "MCP tool returned an error" if state == "failed" else "MCP result captured; inspect evidence before completion"
            finally:
                if client:
                    client.close()
    except (FusionError, OSError, ValueError, TypeError) as exc:
        state = "unknown" if sent else "blocked"
        reason = str(exc) if isinstance(exc, FusionError) else type(exc).__name__
        detail = ("MCP outcome uncertain; reconcile before retrying" if sent else "MCP preflight failed") + ": " + reason
        if client and client.last_response:
            write_view(case, f"captures/{attempt}/last-response.json", encode(client.last_response) + "\n")
            paths.append(capture / "last-response.json")
    execution = {"attempt_id": attempt, "route": route, "status": state, "summary": detail,
                 "started": started, "finished": time.time(), "invocation_sha256": digest,
                 "tool_call_sent": sent, "connection": "new_stdio_explicit_target",
                 "host_registration": "not_modified_or_claimed"}
    write_view(case, f"captures/{attempt}/receipt.json", encode(execution) + "\n")
    paths.append(capture / "receipt.json")
    recorded = case.record(attempt, state, detail, paths)
    return dict(recorded, route=route, capture_dir=f"captures/{attempt}", tool_call_sent=sent,
                next="Inspect result.json, then advance with observed facts; unknown results require reconcile")
