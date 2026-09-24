"""Concrete bounded adapters for the specialist procedures shipped with this pack."""
from pathlib import Path
import shutil
import sys


def local_file(data):
    if any(value.lower().startswith(("http://", "https://")) for value in (data["target"], data["resource"])):
        return None
    target, path = Path(data["target"]).resolve(), Path(data["resource"]).resolve()
    return path if path.is_file() and (path == target or target.is_dir() and path.is_relative_to(target)) else None


def specialist_binding(data, procedure, evidence_paths=None):
    identity = procedure["id"]
    scripts = Path(__file__).resolve().parent
    helper = {"binary-profile": "fusion_binary_profile.py", "crash-triage": "fusion_crash_triage.py"}.get(identity)
    # Only the router supplies these paths from the current reviewed source's
    # hash-checked artifacts; an observation cannot invent an evidence binding.
    evidence_path = (evidence_paths or {}).get(data["resource"]) if identity == "crash-triage" else None
    path = evidence_path or (local_file(data) if (helper or identity == "managed-context")
                             and not data["resource"].startswith("evidence:") else None)
    if helper and path:
        argv = [sys.executable, "-X", "utf8", str(scripts / helper), str(path)]
        if identity == "binary-profile" and data["target_version"].startswith("sha256:"):
            argv += ["--expected-sha256", data["target_version"][7:]]
    elif identity == "proxy-trust" and data["resource"] == data["target"] and data["identity_ref"] == "anonymous":
        argv = [sys.executable, "-X", "utf8", str(scripts / "fusion_proxy_probe.py"), data["resource"]]
    elif identity == "managed-context" and path and shutil.which("ilspycmd"):
        # List types first; never dump a whole assembly into the active context.
        argv = [shutil.which("ilspycmd"), "-l", "c", str(path)]
    else:
        return None
    return {"status": "local_callable", "provider": "host", "tool": argv[0], "argv": argv,
            "limit": "Read the captured output before review; successful execution alone is not a finding"}
