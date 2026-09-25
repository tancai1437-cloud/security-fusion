#!/usr/bin/env python3
"""Portable, file-backed helpers for security-fusion. Python 3.9+ stdlib only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from fusion_store import Case, FusionError, NOTE_KINDS, encode, read_json, require
from fusion_views import bounded, catalog, query, report, resume, write_view
from fusion_scope_cli import add_commands, binding_options, execute_bound, memory_query_options
from fusion_workspace import Workspace
from fusion_start import add_start_command, start
from fusion_methods import check_guidance, execution_route
from fusion_routing import dispatch_route
from fusion_advance import advance
from fusion_mcp import mcp_run


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    add_start_command(commands)
    listing = commands.add_parser("catalog", help="Read only one routing layer or capability")
    selectors = listing.add_mutually_exclusive_group()
    for name in ("mission", "skill", "capability"):
        selectors.add_argument("--" + name)
    listing.add_argument("--inventory")
    listing.add_argument("--environment", help="Private verified environment index")
    listing.add_argument("--agent", choices=["dsh", "opencode", "pi"])
    listing.add_argument("--instance", help="Current host instance; prevents reusing another host's readiness")
    listing.add_argument("--max-chars", type=int, default=6000)
    add_commands(commands)
    for name in ("init", "plan", "route", "advance", "mcp-run", "begin", "record", "review", "reconcile", "note", "resume", "query", "report", "run"):
        command = commands.add_parser(name)
        command.add_argument("--case", required=True)
        if name != "init":
            binding_options(command)
        if name in {"init", "plan", "route"}:
            command.add_argument("--input", required=True)
        if name in {"route", "advance"}:
            command.add_argument("--mcp-profile", help="Optional explicit-target stdio adapter to match by capability")
            command.add_argument("--environment")
            command.add_argument("--agent", choices=["dsh", "opencode", "pi"])
            command.add_argument("--instance")
            command.add_argument("--execute-local", action="store_true")
            command.add_argument("--max-chars", type=int, default=6000)
        if name == "advance":
            command.add_argument("--check", required=True, help="Explicit source check; never chooses the latest case/check")
            command.add_argument("--summary", help="Caller judgement after inspecting the source evidence")
            command.add_argument("--valid-for", type=float, default=0)
            command.add_argument("--feature", action="append", required=True)
            command.add_argument("--resource")
            command.add_argument("--identity")
            command.add_argument("--inputs", help="Only method-specific inputs; source metadata is derived")
        if name in {"begin", "run", "mcp-run"}:
            command.add_argument("--check", required=True)
            command.add_argument("--retest-reason", default="")
        if name == "mcp-run":
            command.add_argument("--profile", required=True, help="Private explicit-target stdio adapter profile")
            command.add_argument("--arguments", required=True, help="Actual MCP tool arguments JSON")
            command.add_argument("--timeout", type=float, default=60)
        if name == "begin":
            command.add_argument("--provider", required=True)
            command.add_argument("--tool", required=True)
            command.add_argument("--context")
        if name in {"record", "review", "reconcile"}:
            command.add_argument("--attempt", required=True)
            command.add_argument("--summary", required=True)
        if name in {"record", "reconcile"}:
            command.add_argument("--artifact", action="append", default=[])
        if name == "record":
            command.add_argument("--status", required=True, choices=["review", "failed", "blocked", "unknown"])
            command.add_argument("--mcp-result", help="Local file containing the full MCP CallToolResult")
        if name == "review":
            command.add_argument("--verdict", required=True, choices=["done", "failed", "blocked"])
            command.add_argument("--valid-for", type=float, default=0)
        if name == "reconcile":
            command.add_argument("--outcome", required=True, choices=["observed", "not_executed"])
        if name == "note":
            command.add_argument("--kind", required=True, choices=NOTE_KINDS)
            command.add_argument("--text", required=True)
            command.add_argument("--evidence", action="append", default=[])
            command.add_argument("--supersedes")
        if name in {"note", "resume", "query"}:
            command.add_argument("--check")
        if name in {"resume", "query"}:
            command.add_argument("--max-chars", type=int, default=6000)
        if name == "resume":
            memory_query_options(command, recovery=True)
        if name == "query":
            command.add_argument("--kind", choices=["checks", "notes", "events", "attempts"], required=True)
            command.add_argument("--offset", type=int, default=0)
            command.add_argument("--limit", type=int, default=10)
            command.add_argument("--target", help="Exact canonical target; filters checks or their notes")
        if name == "run":
            command.add_argument("--timeout", type=float, default=300)
            command.add_argument("--cwd", help="Defaults to the case directory")
            command.add_argument("argv", nargs=argparse.REMAINDER)
    return root


def local_run(case, args):
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    require(bool(argv), "run requires -- followed by an executable and its arguments")
    require(0 < args.timeout <= 86400, "timeout must be between 0 and 86400 seconds")
    cwd = Path(args.cwd).resolve() if args.cwd else case.root
    require(cwd.is_dir(), "Working directory does not exist")
    spec = json.loads(case.check(args.check)["spec"])
    parameters = spec["inputs"].get("parameters", spec["inputs"])
    expected = parameters.get("expected_exit_codes", [0]) if isinstance(parameters, dict) else [0]
    require(isinstance(expected, list) and 1 <= len(expected) <= 4
            and all(type(code) is int and -(2 ** 31) <= code < 2 ** 32 for code in expected),
            "expected_exit_codes requires 1-4 integer process exit codes")
    expected = sorted(set(expected))
    require(expected == [0] or spec["capability_id"] == "memory.reproduce",
            "Nonzero expected exits are only supported for explicit memory.reproduce checks")
    invocation = {"argv": argv, "cwd": str(cwd)}
    if expected != [0]:
        invocation["expected_exit_codes"] = expected
    command_digest = hashlib.sha256(encode(invocation).encode("utf-8")).hexdigest()
    route = execution_route(spec, "host", Path(argv[0]).name)
    receipt = case.begin(args.check, "host", route["tool"], args.retest_reason, command_digest)
    if receipt["decision"] != "execute":
        return dict(receipt, route=route)
    attempt = receipt["attempt_id"]
    capture = case.root / "captures" / attempt
    capture.mkdir(parents=True, exist_ok=False, mode=0o700)
    require(capture.resolve().is_relative_to(case.root), "Capture path escapes case")
    stdout, stderr = capture / "stdout", capture / "stderr"
    state, code, detail = "unknown", None, "Interrupted; reconcile before retrying"
    started = time.time()
    with stdout.open("xb") as out, stderr.open("xb") as err:
        if os.name != "nt":
            os.chmod(stdout, 0o600)
            os.chmod(stderr, 0o600)
        try:
            process = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err, shell=False)
            try:
                code = process.wait(timeout=args.timeout)
                state = "review" if code in expected else "failed"
                detail = f"Local process exited {code}; inspect captured output before accepting completion"
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                detail = "Timeout; parent process stopped; child/remote effects may remain; reconcile before retrying"
        except OSError as exc:
            state, detail = "blocked", "Process launch failed: " + type(exc).__name__
        finally:
            out.flush()
            err.flush()
            os.fsync(out.fileno())
            os.fsync(err.fileno())
    execution = {"attempt_id": attempt, "route": route, "command_sha256": command_digest, "returncode": code,
                 "expected_exit_codes": expected,
                 "status": state, "started": started, "finished": time.time(), "summary": detail}
    write_view(case, f"captures/{attempt}/receipt.json", encode(execution) + "\n")
    recorded = case.record(attempt, state, detail, [stdout, stderr, capture / "receipt.json"])
    return dict(recorded, route=route, returncode=code, capture_dir=f"captures/{attempt}")


def record_result(args, case):
    status, paths = args.status, list(args.artifact)
    if args.mcp_result:
        result = read_json(args.mcp_result)
        require(isinstance(result, dict), "MCP result must be an object")
        require("isError" not in result or isinstance(result["isError"], bool), "Invalid MCP isError")
        if result.get("isError") or result.get("error") is not None:
            status = "failed"
        paths.append(args.mcp_result)
    return case.record(args.attempt, status, args.summary, paths)


def dispatch(args, case):
    command = args.command
    if command == "route":
        return dispatch_route(args, case, local_run)
    if command == "advance":
        return advance(args, case, local_run)
    if command == "mcp-run":
        return mcp_run(case, args)
    if command == "plan":
        specs = read_json(args.input)
        guidance = check_guidance(specs[0]) if specs else None
        result = case.plan(specs)["checks"]
        return {"total": len(result), "checks": result[:10], "omitted": max(0, len(result) - 10),
                "guidance": guidance,
                "next": "query --kind checks or resume --check <plan-key>"}
    if command == "begin":
        route = execution_route(json.loads(case.check(args.check)["spec"]), args.provider, args.tool)
        return dict(case.begin(args.check, args.provider, args.tool, args.retest_reason), route=route)
    if command == "record":
        return record_result(args, case)
    if command == "review":
        return case.review(args.attempt, args.verdict, args.summary, args.valid_for)
    if command == "reconcile":
        return case.reconcile(args.attempt, args.outcome, args.summary, args.artifact)
    if command == "note":
        return case.note(args.kind, args.text, args.check, args.evidence, args.supersedes)
    if command in {"resume", "query"}:
        with case.transaction():
            if command == "resume":
                return resume(case, args.check, args.max_chars, args.binding, args.experiences)
            return bounded(query(case, args.kind, args.offset, args.limit, args.check, args.target), args.max_chars)
    if command == "report":
        return report(case)
    if command == "run":
        return local_run(case, args)
    raise FusionError("Unknown command")


def main(argv=None):
    args = parser().parse_args(argv)
    case = None
    try:
        if args.command == "start":
            result = start(args, local_run)
        elif args.command == "catalog":
            require(not args.inventory or args.capability, "--inventory requires --capability")
            if args.environment:
                from fusion_environment import Environment
                require(args.capability and args.agent and args.instance and not args.inventory,
                        "--environment requires capability, agent and instance; cannot combine --inventory")
                result = bounded(Environment(args.environment, args.agent).lookup(args.capability, args.instance), args.max_chars)
            else:
                require(not args.agent and not args.instance, "Agent/instance require --environment")
                result = bounded(catalog(args.mission, args.skill, args.capability,
                                         read_json(args.inventory) if args.inventory else None), args.max_chars)
        elif args.command == "init":
            case = Case.create(args.case, read_json(args.input))
            result = {"status": "created", "case_id": case.meta("case_id")}
        elif args.command == "workspace-init":
            workspace = Workspace.create(args.workspace)
            try:
                result = {"workspace_id": workspace.setting("workspace_id"), "search_engine": workspace.setting("search_engine")}
            finally:
                workspace.close()
        else:
            case = Case(args.case)
            if args.command == "identify":
                result = {"case_id": case.meta("case_id"), "config": case.meta("config")}
                pinned = case.db.execute("SELECT value FROM meta WHERE key='workspace_binding'").fetchone()
                if pinned:
                    binding = json.loads(pinned[0])
                    workspace = Workspace(binding["workspace_path"])
                    try:
                        workspace.registration(case)
                        owner = workspace.db.execute("SELECT id FROM sessions WHERE case_id=? AND active=1",
                                                     (case.meta("case_id"),)).fetchone()
                        result["binding_hint"] = dict(binding, session=owner["id"] if owner else None)
                    finally:
                        workspace.close()
            else:
                result = execute_bound(args, case, dispatch)
        print(encode(result))
        return 0
    except (FusionError, OSError, sqlite3.Error, json.JSONDecodeError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, FusionError) else type(exc).__name__ + ": check input, ledger and file access"
        print(encode({"status": "error", "error": message}), file=sys.stderr)
        return 2
    finally:
        if case is not None:
            case.close()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
