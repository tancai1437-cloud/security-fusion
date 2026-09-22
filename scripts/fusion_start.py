"""Start one concrete check using the existing case and session guards."""
import argparse
from pathlib import Path

from fusion_store import Case, PACK, read_json, reject_credentials, require, text_field, validate_spec
from fusion_workspace import Workspace, file_lock
from fusion_methods import check_guidance
from fusion_routing import initial_http_spec


def add_start_command(commands):
    command = commands.add_parser("start", help="Bind a case, plan its first check, and optionally run it")
    for name in ("case", "workspace", "session", "input"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--expect-case", help="Required to reopen an existing case; never takes over another session")
    command.add_argument("--timeout", type=float, default=300)
    command.add_argument("--cwd", help="Defaults to the case directory")
    command.add_argument("--execute-local", action="store_true", help="Execute the built-in read-only HTTP entry adapter")
    command.add_argument("argv", nargs=argparse.REMAINDER)


def start_input(args):
    task = read_json(args.input)
    require(isinstance(task, dict), "Start input must be an object")
    require(isinstance(task.get("config"), dict), "Start input requires a case config")
    text_field(task.get("project"), "project", 160)
    text_field(args.session, "session", 160)
    targets = task.get("targets")
    require(isinstance(targets, list) and targets, "Start input requires explicit canonical targets")
    for target in targets:
        text_field(target, "target", 1000)
    require(not (task.get("entry") and task.get("check")), "Use entry or check, not both")
    if task.get("entry"):
        require(task["config"].get("mission_id") in {"pentest", "src", "redteam", "ai-assessment"},
                "HTTP entry discovery is not the starting method for this mission")
        task["check"], task["entry_binding"] = initial_http_spec(task["entry"])
    require(not args.execute_local or task.get("entry"), "Automatic local execution requires entry mode")
    require(not (args.execute_local and args.argv), "Choose built-in entry execution or an explicit command")
    check = task.get("check")
    validate_spec(check)
    require(check["target"] in targets, "First check target is outside the case binding")
    require(not check.get("depends_on"), "First check must have no dependencies; add later checks with plan")
    reject_credentials(task)
    require(0 < args.timeout <= 86400, "timeout must be between 0 and 86400 seconds")
    if args.cwd:
        require(Path(args.cwd).resolve().is_dir(), "Working directory does not exist")
    return task


def open_workspace(root):
    root = Path(root).resolve()
    require(root != PACK and PACK not in root.parents, "Keep workspace data outside the installed skill")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Serialize first-time setup across different cases sharing one registry.
    with file_lock(root / "initialize.lock"):
        if (root / "workspace.sqlite3").exists():
            return Workspace(root)
        return Workspace.create(root)


def open_case(args, task):
    root = Path(args.case).resolve()
    if (root / "case.sqlite3").exists():
        require(args.expect_case, "Existing case: use identify/resume, or start with --expect-case")
        case = Case(root)
        try:
            require(case.meta("case_id") == args.expect_case, "Wrong expected case ID")
            require(case.meta("config") == task["config"], "Case config changed; inspect scope or create a new case")
        except BaseException:
            case.close()
            raise
        return case
    require(not args.expect_case, "Expected case ledger is missing; do not recreate historical state")
    require(not root.exists() or (root.is_dir() and not any(root.iterdir())),
            "Existing case directory has data but no ledger; inspect or migrate it before starting")
    return Case.create(root, task["config"])


def start(args, run_local):
    task = start_input(args)
    guidance = check_guidance(task["check"])
    workspace = open_workspace(args.workspace)
    case = None
    try:
        case = open_case(args, task)
        binding = workspace.bind(case, args.session, task["project"], case.meta("case_id"), task["targets"])
        with workspace.operation(case, args.session):
            workspace.require_target(case, task["check"]["target"])
            planned = case.plan([task["check"]])["checks"][0]
            args.check = planned["check_id"]
            args.retest_reason = ""
            result = {"case_id": binding["case_id"], "case_path": str(case.root),
                      "project": binding["project"], "session": args.session, "check_id": args.check,
                      "guidance": guidance}
            if task.get("entry_binding"):
                result["entry_binding"] = task["entry_binding"]
                if args.execute_local and task["entry_binding"]["status"] == "local_callable":
                    args.argv = task["entry_binding"]["argv"]
            if args.argv:
                result["execution"] = run_local(case, args)
                result["next"] = "Inspect captured evidence; review only when the check's completion conditions hold."
            else:
                result["status"] = "planned_not_executed"
                result["next"] = "Run this check, or verify its MCP capability/context and use begin -> host call -> record."
            return result
    finally:
        if case is not None:
            case.close()
        workspace.close()
