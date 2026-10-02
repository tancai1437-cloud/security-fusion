"""Read-only checks for the explicitly selected purge/DSH composition. Never applies host patches."""
import json
from pathlib import Path

DSH_VERSION = "0.2.0-rc.2"
PURGE_VERSION = "1.1.47"


def purge_config(profile, runtime, dsh_home):
    if not runtime or not dsh_home:
        raise ValueError("--purge requires --runtime (actual SDK root) and --dsh-home (actual DSH_HOME)")
    runtime, dsh_home = Path(runtime).resolve(), Path(dsh_home).resolve()
    if not (runtime / "package.json").is_file() or not dsh_home.is_dir():
        raise ValueError("Select an existing runtime package root and DSH_HOME")
    sdk = runtime / "node_modules/@deepseek-ai"
    versions = {}
    for name in ("dsh-tools", "dsh-session", "dsh-llm", "dsh-web-app"):
        package = json.loads((sdk / name / "package.json").read_text(encoding="utf-8-sig"))
        versions[name] = package.get("version")
    if any(v != DSH_VERSION for v in versions.values()):
        raise ValueError("Purge composition requires reviewed DSH " + DSH_VERSION + "; found " + str(versions))
    purge = Path(profile) / "node_modules/dsh-purge/package.json"
    metadata = json.loads(purge.read_text(encoding="utf-8-sig"))
    if metadata.get("name") != "dsh-purge" or metadata.get("version") != PURGE_VERSION:
        raise ValueError("Review the installed dsh-purge interface before enabling this bridge; reviewed version: " + PURGE_VERSION)
    if metadata.get("dshTarget") != DSH_VERSION:
        raise ValueError("dsh-purge target version differs from this bridge")
    if not (sdk / "dsh-web-app/presets/standard.patch.yml").is_file():
        raise ValueError("Installed standard preset is missing; do not generate a guessed tool composition")
    if not (purge.parent / "lib/redteam/tools.js").is_file():
        raise ValueError("Installed dsh-purge data tools are missing")
    return {"integration": "dsh-purge", "runtime": str(runtime), "dshHome": str(dsh_home)}
