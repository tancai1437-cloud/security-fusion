#!/usr/bin/env python3
"""Agent-driven environment reconciliation: inspect, reuse/install, attach, verify, index."""
import argparse
import json
from pathlib import Path
import sys

from fusion_environment import Environment, recipes
from fusion_environment_config import configure
from fusion_store import FusionError, encode, manifest, read_json, require
from fusion_views import bounded
from fusion_workspace import file_lock


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("scan", "plan", "recipe", "register", "configure", "verify", "invalidate", "index"):
        command = commands.add_parser(name)
        command.add_argument("--root", required=True, help="Private environment directory outside the Skill")
        command.add_argument("--agent", required=True, choices=["dsh", "opencode", "pi"])
        command.add_argument("--max-chars", type=int, default=6000)
        if name in {"plan", "verify", "index"}:
            command.add_argument("--instance", required=True, help="Current host/process scope; use session ID if unavailable")
        if name in {"recipe", "register", "verify", "invalidate"}:
            command.add_argument("--provider", required=True, choices=list(recipes()))
        if name in {"register", "verify"}:
            command.add_argument("--input", required=True)
        if name == "configure":
            command.add_argument("--provider", action="append", required=True, choices=list(recipes()))
        if name == "scan":
            command.add_argument("--search-root", action="append", default=[])
        if name == "plan":
            command.add_argument("--capability", action="append", default=[])
            command.add_argument("--skill", action="append", default=[])
        if name == "index":
            command.add_argument("--capability", required=True)
        if name == "verify":
            command.add_argument("--valid-for", type=float, default=3600)
        if name == "invalidate":
            command.add_argument("--reason", required=True)
    return root


def dispatch(args, environment):
    if args.command == "scan":
        return environment.scan(args.search_root)
    if args.command == "recipe":
        return recipes()[args.provider]
    if args.command == "plan":
        capabilities = list(args.capability)
        modules = {m["id"]: m for m in manifest("specialists.json", "modules")}
        for skill in args.skill:
            require(skill in modules, "Unknown specialist")
            capabilities.extend(modules[skill]["execution_routes"])
        return environment.plan(capabilities, args.instance)
    if args.command == "register":
        return environment.register(args.provider, read_json(args.input))
    if args.command == "configure":
        return configure(environment, args.provider)
    if args.command == "verify":
        return environment.verify(args.provider, read_json(args.input), args.instance, args.valid_for)
    if args.command == "invalidate":
        return environment.invalidate(args.provider, args.reason)
    return environment.lookup(args.capability, args.instance)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        # Check namespace before creating a directory or lock.
        environment = Environment(args.root, args.agent)
        environment.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        require(not (environment.root / ".bootstrap.lock").is_symlink(), "Refusing a symlink lock")
        with file_lock(environment.root / ".bootstrap.lock"):
            environment = Environment(args.root, args.agent)
            result = dispatch(args, environment)
        print(encode(bounded(result, args.max_chars)))
        return 0
    except (FusionError, OSError, ValueError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, FusionError) else type(exc).__name__ + ": inspect input and private environment files"
        print(encode({"status": "error", "error": message}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
