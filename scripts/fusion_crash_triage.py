"""Classify saved sanitizer diagnostics; never execute samples or infer exploitability."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

MAX_LOG = 2 * 1024 * 1024
PATTERNS = (
    ("stack-buffer-overflow", r"AddressSanitizer: stack-buffer-overflow\b"),
    ("heap-buffer-overflow", r"AddressSanitizer: heap-buffer-overflow\b"),
    ("global-buffer-overflow", r"AddressSanitizer: global-buffer-overflow\b"),
    ("heap-use-after-free", r"AddressSanitizer: heap-use-after-free\b"),
    ("stack-use-after-return", r"AddressSanitizer: stack-use-after-return\b"),
    ("stack-use-after-scope", r"AddressSanitizer: stack-use-after-scope\b"),
    ("double-free", r"AddressSanitizer: attempting double-free\b"),
    ("stack-exhaustion", r"AddressSanitizer: stack-overflow\b"),
    ("fatal-signal", r"AddressSanitizer: (?:SEGV|DEADLYSIGNAL)\b"),
    ("undefined-behavior", r"runtime error: .+"),
)


def triage(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        raw = stream.read(MAX_LOG + 1)
    if len(raw) > MAX_LOG:
        raise ValueError("Log exceeds 2 MiB; select and preserve a diagnostic excerpt first")
    lines = raw.decode("utf-8", errors="replace").splitlines()
    events, frames = [], []
    event_count = 0
    for number, line in enumerate(lines, 1):
        for kind, pattern in PATTERNS:
            if re.search(pattern, line):
                event_count += 1
                if len(events) < 16:
                    events.append({"kind": kind, "line": number, "text": line[:500]})
                break
        if len(frames) < 8 and re.match(r"\s*#\d+\s", line):
            frames.append({"line": number, "text": line[:500]})
    kinds = sorted({event["kind"] for event in events})
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "classification": kinds or ["unclassified"], "diagnostics": events, "frames": frames,
            "omitted_diagnostics": max(0, event_count - len(events)), "executed_sample": False,
            "feature_hints": ["crash.classified"] if events else [],
            "verdict": "diagnostic_only" if events else "insufficient_evidence",
            "next": "Bind sample/build/input hashes, reproduce in the bound test environment, then compare a negative control",
            "limits": "Log assertions are untrusted observations; stack exhaustion is not a stack buffer overwrite; no exploitability claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log")
    args = parser.parse_args()
    try:
        print(json.dumps(triage(args.log), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
