#!/usr/bin/env python3
"""Install the observed-execution adapter into an explicitly selected DSH profile."""
import argparse
import datetime
import json
from pathlib import Path
import re
import shutil

PACK = Path(__file__).resolve().parents[1]
FILES = ("dsh.mjs", "dsh-runtime.mjs", "dsh-execution.mjs", "dsh-routing.mjs")
BEGIN = "# BEGIN security-fusion managed adapter"
END = "# END security-fusion managed adapter"
NAME = "security-fusion-host"


def merge_managed(existing, entry):
    if not isinstance(existing, dict) or set(existing) != {"insert"} or len(existing["insert"]) != 1:
        raise ValueError("Malformed managed adapter insertion")
    prior = existing["insert"][0]
    if prior.get("id") != NAME or prior.get("name") != entry["name"]:
        raise ValueError("An unmanaged security-fusion entry exists; reconcile it before installing")
    return {**prior, **entry, "config": {**prior.get("config", {}), **entry["config"]}}


def json_patch(text, entry, uninstall):
    entries = json.loads(text)
    if not isinstance(entries, list):
        raise ValueError("DSH patch must be an array")
    previous = None
    for item in entries:
        if NAME in json.dumps(item):
            if previous is not None:
                raise ValueError("Duplicate adapter entries")
            entry = merge_managed(item, entry)
            previous = item
    entries = [item for item in entries if item is not previous]
    if not uninstall:
        entries.append({"insert": [entry]})
    return json.dumps(entries, ensure_ascii=False, indent=2) + "\n"


def extract_managed(text, entry):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError("Incomplete or duplicate managed adapter markers")
    if BEGIN not in text:
        return text, entry
    start, stop = text.index(BEGIN), text.index(END) + len(END)
    if stop < start:
        raise ValueError("Malformed managed adapter markers")
    block = text[start + len(BEGIN):text.index(END)].strip()
    if not block.startswith("- "):
        raise ValueError("Malformed managed adapter insertion")
    entry = merge_managed(json.loads(block[2:]), entry)
    return text[:start] + text[stop:].lstrip("\r\n"), entry


def validate_yaml_array(text):
    lines = [x.strip() for x in text.splitlines() if x.strip() and not x.lstrip().startswith("#")]
    if lines[:1] == ["---"]:
        lines = lines[1:]
    if lines and (not lines[0].startswith("- ") or {"---", "..."}.intersection(lines)):
        raise ValueError("Expected a single YAML patch array; existing configuration left unchanged")
    if re.search(r"\bid\s*:\s*['\"]?security-fusion-host\b", text):
        raise ValueError("An unmanaged security-fusion entry exists; reconcile it before installing")


def patch_text(text, entry, uninstall=False):
    """Own only the delimited insertion; preserve unrelated user configuration."""
    if text.lstrip().startswith("["):
        return json_patch(text, entry, uninstall)
    text, entry = extract_managed(text, entry)
    validate_yaml_array(text)
    if uninstall:
        return text if text.strip() else "[]\n"
    insertion = "- " + json.dumps({"insert": [entry]}, ensure_ascii=False)
    return text.rstrip() + ("\n\n" if text.strip() else "") + BEGIN + "\n" + insertion + "\n" + END + "\n"


def validate_profile(profile, state_dir):
    if not profile.is_dir() or not (profile / "package.json").is_file():
        raise ValueError("Select an existing DSH profile directory containing package.json")
    package = json.loads((profile / "package.json").read_text(encoding="utf-8-sig"))
    if not isinstance(package.get("dsh", {}).get("profile"), dict):
        raise ValueError("package.json does not declare a DSH profile")
    if state_dir == PACK or PACK in state_dir.parents:
        raise ValueError("Keep private runtime state outside the installed skill")
    if (profile / "cordis.patch.yml").is_symlink():
        raise ValueError("Refusing to change a linked patch file")


def validate_owned_directory(directory):
    if directory.resolve() != directory:
        raise ValueError("Managed adapter directory must not be a symlink")
    marker = directory / "managed.json"
    if directory.exists() and (not marker.is_file() or json.loads(marker.read_text()).get("owner") != NAME):
        raise ValueError("Adapter directory is not owned by this installer")


def copy_adapter(directory):
    if any(not (PACK / "adapters" / name).is_file() for name in FILES):
        raise ValueError("Incomplete skill: install the full adapter directory")
    for name in FILES:
        if (directory / name).is_symlink():
            raise ValueError("Refusing to overwrite linked adapter code")
    directory.mkdir(exist_ok=True, mode=0o700)
    for name in FILES:
        shutil.copy2(PACK / "adapters" / name, directory / name)
    (directory / "managed.json").write_text(json.dumps({"owner": NAME, "skill_root": str(PACK)}), encoding="utf-8")


def write_patch(profile, patch, original, updated):
    if updated == original:
        return {}
    result = {}
    if patch.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = profile / ("cordis.patch.security-fusion-" + timestamp + ".bak")
        shutil.copy2(patch, backup)
        result["backup"] = str(backup)
    temporary = profile / "cordis.patch.security-fusion.tmp"
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(updated)
    temporary.chmod(0o600)
    temporary.replace(patch)
    return result


def install(profile, state_dir, python, *, uninstall=False, dry_run=False):
    profile, state_dir = Path(profile).resolve(), Path(state_dir).resolve()
    validate_profile(profile, state_dir)
    directory = profile / NAME
    validate_owned_directory(directory)
    patch = profile / "cordis.patch.yml"
    original = patch.read_text(encoding="utf-8-sig") if patch.exists() else ""
    entry = {"id": NAME, "name": "./" + NAME + "/dsh.mjs",
             "config": {"skillRoot": str(PACK), "stateDir": str(state_dir), "python": python}}
    updated = patch_text(original, entry, uninstall)
    result = {"status": "preview" if dry_run else "removed" if uninstall else "configured_requires_restart",
              "profile": str(profile), "patch": str(patch), "state_dir": str(state_dir),
              "runtime_verified": False, "preserved": "Existing profile settings and case state"}
    if dry_run:
        return result
    if not uninstall:
        copy_adapter(directory)
    result.update(write_patch(profile, patch, original, updated))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Actual target Agent profile, not the skill directory")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--python", default="python3")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = install(args.profile, args.state_dir, args.python, uninstall=args.uninstall, dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
