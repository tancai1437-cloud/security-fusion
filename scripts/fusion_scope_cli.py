"""CLI integration for session guards, context ownership, and experience retrieval."""
import json

from fusion_memory import Memory
from fusion_store import ACTIVE, read_json, require
from fusion_views import bounded
from fusion_workspace import Workspace

COMMANDS = {"bind", "handoff", "context-set", "context-release", "memory-add", "memory-review",
            "memory-show", "memory-embed", "memory-search"}


def binding_options(command):
    command.add_argument("--workspace", required=True, help="Shared private registry, outside the skill")
    command.add_argument("--session", required=True, help="Explicit host/conversation binding ID")


def memory_query_options(command, recovery=False):
    command.add_argument("--memory-query" if recovery else "--query", required=not recovery)
    command.add_argument("--skill", required=not recovery)
    command.add_argument("--include-general", action="store_true")
    command.add_argument("--embedding", help="Optional query embedding JSON; never calls an embedding service")
    command.add_argument("--min-cosine", type=float, default=0.5)


def add_commands(commands):
    init = commands.add_parser("workspace-init")
    init.add_argument("--workspace", required=True)
    identify = commands.add_parser("identify", help="Inspect case ID and scope before explicit binding")
    identify.add_argument("--case", required=True)
    for name in sorted(COMMANDS):
        command = commands.add_parser(name)
        command.add_argument("--case", required=True)
        binding_options(command)
        configure_command(command, name)


def configure_command(command, name):
    if name == "bind":
        command.add_argument("--project", required=True)
        command.add_argument("--expect-case", required=True)
        command.add_argument("--target", action="append", required=True)
    if name == "handoff":
        command.add_argument("--to-session", required=True)
        command.add_argument("--reason", required=True)
    if name in {"context-set", "context-release"}:
        command.add_argument("--slot", required=True)
    if name in {"context-set", "memory-add", "memory-embed"}:
        command.add_argument("--input", required=True)
    if name == "memory-add":
        command.add_argument("--note", required=True)
        command.add_argument("--supersedes")
    if name in {"memory-show", "memory-review", "memory-embed"}:
        command.add_argument("--memory", required=True)
    if name == "memory-review":
        command.add_argument("--verdict", required=True, choices=["accept", "reject", "retire"])
        command.add_argument("--scope", choices=["project", "general"], default="project")
        command.add_argument("--validation", required=True)
        command.add_argument("--redacted", action="store_true")
        command.add_argument("--valid-for", type=int, default=0)
    if name == "memory-show":
        command.add_argument("--include-general", action="store_true")
        command.add_argument("--max-chars", type=int, default=6000)
    if name == "memory-search":
        memory_query_options(command)
        command.add_argument("--limit", type=int, default=3)
        command.add_argument("--max-chars", type=int, default=1800)


def search(memory, registration, args, query_text, maximum):
    return memory.search(registration["project"], args.skill, query_text, args.include_general,
                         read_json(args.embedding) if args.embedding else None,
                         args.min_cosine, getattr(args, "limit", 3), maximum)


def scope_command(args, case, workspace, registration):
    memory = Memory(workspace)
    project = registration["project"]
    if args.command == "context-set":
        return workspace.context_set(case, args.slot, read_json(args.input))
    if args.command == "context-release":
        return workspace.context_release(case, args.slot)
    if args.command == "memory-add":
        return memory.candidate(case, read_json(args.input), args.note, args.supersedes)
    if args.command == "memory-review":
        return memory.review(case, args.memory, args.verdict, args.scope, args.validation, args.redacted, args.valid_for)
    if args.command == "memory-show":
        return bounded(memory.show(project, args.memory, args.include_general), args.max_chars)
    if args.command == "memory-embed":
        return memory.embed(project, args.memory, read_json(args.input))
    if args.command == "memory-search":
        return search(memory, registration, args, args.query, args.max_chars)
    require(False, "Unknown scoped command")


def prepare_execution(args, case, workspace):
    if args.command == "plan":
        specs = read_json(args.input)
        require(isinstance(specs, list), "Plan must be a list")
        for spec in specs:
            require(isinstance(spec, dict), "Check must be an object")
            workspace.require_target(case, spec.get("target"))
    if args.command not in {"begin", "run"}:
        return None
    check = case.check(args.check)
    workspace.require_target(case, json.loads(check["spec"])["target"])
    if args.command == "begin" and args.provider != "host":
        state = case.effective_status(check)
        needs_call = state == "pending" or (state not in ACTIVE and bool(args.retest_reason))
        if needs_call:
            require(args.context is not None, "Native MCP execution requires --context and a fresh context observation")
            return workspace.context_check(case, args.check, args.provider, args.context)
    return None


def execute_bound(args, case, dispatch):
    workspace = Workspace(args.workspace)
    try:
        if args.command == "bind":
            return workspace.bind(case, args.session, args.project, args.expect_case, args.target)
        if args.command == "handoff":
            return workspace.handoff(case, args.session, args.to_session, args.reason)
        with workspace.operation(case, args.session) as registration:
            args.binding = {"workspace_id": workspace.setting("workspace_id"), "project": registration["project"],
                            "session": args.session, "case_id": case.meta("case_id"),
                            "scope_digest": registration["scope_digest"]}
            if args.command in COMMANDS:
                return scope_command(args, case, workspace, registration)
            context = prepare_execution(args, case, workspace)
            if args.command == "resume":
                args.experiences = None
                if args.memory_query:
                    require(bool(args.skill), "--memory-query requires --skill")
                    args.experiences = search(Memory(workspace), registration, args, args.memory_query, args.max_chars)
            result = dispatch(args, case)
            if context and result.get("decision") == "execute":
                with case.transaction():
                    case.event("context_checked", result["attempt_id"], context)
            return result
    finally:
        workspace.close()
