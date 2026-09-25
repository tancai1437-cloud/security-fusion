"""Durable case state. No network client, model calls, or third-party dependencies."""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

PACK = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
ACTIVE = ("running", "unknown", "review")
NOTE_KINDS = ("fact", "negative", "refuted", "hypothesis", "decision", "constraint", "blocker")
FINGERPRINT_FIELDS = (
    "target", "target_version", "identity_ref", "check_type",
    "inputs", "method_version", "capability_id",
)


class FusionError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FusionError(message)


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def manifest(name, field):
    return read_json(PACK / "manifests" / name)[field]


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reject_credentials(value):
    """Catch common credential fields; free text still requires caller redaction."""
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if not normalized.endswith("_ref"):
                require(normalized not in {
                    "password", "passwd", "token", "access_token", "refresh_token",
                    "authorization", "cookie", "api_key", "secret", "private_key",
                }, "Use a secure *_ref instead of credential field: " + str(key))
            reject_credentials(item)
    elif isinstance(value, list):
        for item in value:
            reject_credentials(item)


def text_field(value, name, maximum=2000):
    require(isinstance(value, str) and bool(value.strip()), name + " must be nonempty text")
    require(len(value) <= maximum, name + " exceeds character limit")
    return value


def validate_spec(spec):
    require(isinstance(spec, dict), "Each check must be an object")
    for field in FINGERPRINT_FIELDS:
        require(field in spec, "Missing check field: " + field)
        if field != "inputs":
            text_field(spec[field], field, 1000)
    require(isinstance(spec["inputs"], dict), "inputs must be an object")
    require(len(encode(spec["inputs"])) <= 32000, "Store large inputs as artifact references")
    modules = {m["id"]: m for m in manifest("specialists.json", "modules")}
    require(spec.get("skill_id") in modules, "Unknown skill_id")
    require(spec["capability_id"] in modules[spec["skill_id"]]["execution_routes"],
            "Capability is not registered for this specialist")
    text_field(spec.get("purpose"), "purpose", 1000)
    dependencies = spec.get("depends_on", [])
    require(isinstance(dependencies, list) and all(isinstance(d, str) for d in dependencies),
            "depends_on must be a list of check IDs or plan keys")
    if "key" in spec:
        require(isinstance(spec["key"], str) and
                bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", spec["key"])), "Invalid plan key")
    reject_credentials(spec)
    identity = {key: spec[key] for key in FINGERPRINT_FIELDS}
    return hashlib.sha256(encode(identity).encode("utf-8")).hexdigest()


SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE checks(
 id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, target TEXT NOT NULL, spec TEXT NOT NULL,
 deps TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 summary TEXT NOT NULL DEFAULT '', latest_attempt TEXT, expires REAL);
CREATE INDEX checks_target ON checks(target);
CREATE TABLE aliases(alias TEXT PRIMARY KEY, check_id TEXT NOT NULL REFERENCES checks(id));
CREATE TABLE attempts(
 id TEXT PRIMARY KEY, check_id TEXT NOT NULL REFERENCES checks(id),
 status TEXT NOT NULL, provider TEXT NOT NULL, tool TEXT NOT NULL,
 started REAL NOT NULL, finished REAL, summary TEXT NOT NULL DEFAULT '',
 retest_reason TEXT NOT NULL DEFAULT '', invocation_digest TEXT NOT NULL DEFAULT '',
 dependency_snapshot TEXT NOT NULL DEFAULT '{}');
CREATE UNIQUE INDEX one_active_attempt ON attempts(check_id)
 WHERE status IN ('running','unknown','review');
CREATE TABLE artifacts(
 id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id),
 path TEXT UNIQUE NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL);
CREATE TABLE notes(
 id TEXT PRIMARY KEY, check_id TEXT REFERENCES checks(id), kind TEXT NOT NULL,
 text TEXT NOT NULL, evidence TEXT NOT NULL, superseded INTEGER NOT NULL DEFAULT 0,
 created REAL NOT NULL);
CREATE TABLE events(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
 kind TEXT NOT NULL, entity TEXT NOT NULL, payload TEXT NOT NULL);
"""


class Case:
    def __init__(self, root):
        self.root = Path(root).resolve()
        path = self.root / "case.sqlite3"
        require(path.is_file() and not path.is_symlink(), "Case ledger not found")
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA synchronous=FULL")
        require(self.meta("schema_version") == SCHEMA_VERSION, "Unsupported case schema version")

    @classmethod
    def create(cls, root, config):
        require(isinstance(config, dict), "Case configuration must be an object")
        require(config.get("mission_id") in {m["id"] for m in manifest("missions.json", "missions")},
                "Unknown mission_id")
        text_field(config.get("objective"), "objective", 4000)
        text_field(config.get("scope"), "scope", 12000)
        constraints = config.get("constraints", [])
        require(isinstance(constraints, list), "constraints must be a list")
        for constraint in constraints:
            text_field(constraint, "constraint", 2000)
        reject_credentials(config)
        root = Path(root).resolve()
        require(root != PACK and PACK not in root.parents, "Keep case data outside the installed skill")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = root / "case.sqlite3"
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        except FileExistsError as exc:
            raise FusionError("Case already exists; use resume") from exc
        database = sqlite3.connect(path)
        try:
            database.executescript(SCHEMA)
            values = {
                "schema_version": SCHEMA_VERSION,
                "case_id": "CASE-" + uuid.uuid4().hex,
                "config": config, "created": time.time(),
            }
            database.executemany("INSERT INTO meta VALUES(?,?)",
                                 [(key, encode(value)) for key, value in values.items()])
            database.commit()
        finally:
            database.close()
        case = cls(root)
        with case.transaction():
            case.event("case_created", case.meta("case_id"), {})
        return case

    def close(self):
        self.db.close()

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def meta(self, key):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        require(row is not None, "Missing case metadata: " + key)
        return json.loads(row[0])

    def event(self, kind, entity, payload):
        self.db.execute("INSERT INTO events(at,kind,entity,payload) VALUES(?,?,?,?)",
                        (time.time(), kind, entity, encode(payload)))

    def check(self, identity):
        row = self.db.execute("SELECT * FROM checks WHERE id=? OR id="
                              "(SELECT check_id FROM aliases WHERE alias=?)",
                              (identity, identity)).fetchone()
        require(row is not None, "Unknown check ID or plan key")
        return dict(row)

    def attempt(self, identity):
        row = self.db.execute("SELECT * FROM attempts WHERE id=?", (identity,)).fetchone()
        require(row is not None, "Unknown attempt ID")
        return dict(row)

    def plan(self, specs):
        require(isinstance(specs, list) and specs, "Plan must be a nonempty list")
        identities = [(spec, validate_spec(spec)) for spec in specs]
        result = []
        with self.transaction():
            aliases = {r["alias"]: r["check_id"] for r in self.db.execute("SELECT * FROM aliases")}
            for spec, fingerprint in identities:
                identity = "CHK-" + fingerprint[:24]
                key = spec.get("key", identity)
                require(key not in aliases or aliases[key] == identity,
                        "Plan key already refers to another check; use a new key for changed conditions")
                aliases[key] = identity
                existing = self.db.execute("SELECT fingerprint FROM checks WHERE id=?", (identity,)).fetchone()
                require(existing is None or existing[0] == fingerprint, "Check ID collision")
                self.db.execute("INSERT OR IGNORE INTO checks(id,fingerprint,target,spec,deps) VALUES(?,?,?,?,?)",
                                (identity, fingerprint, spec["target"], encode(spec), "[]"))
                self.db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?)", (key, identity))
                result.append({"key": key, "check_id": identity, "existing": existing is not None})
            for (spec, _), item in zip(identities, result):
                dependencies = sorted({aliases.get(dep, dep) for dep in spec.get("depends_on", [])})
                for dependency in dependencies:
                    self.check(dependency)
                old = self.check(item["check_id"])
                if item["existing"]:
                    require(json.loads(old["deps"]) == dependencies, "Existing check dependencies differ")
                else:
                    self.db.execute("UPDATE checks SET deps=? WHERE id=?",
                                    (encode(dependencies), item["check_id"]))
                    self.event("check_planned", item["check_id"], {"key": item["key"]})
            graph = {r["id"]: json.loads(r["deps"]) for r in self.db.execute("SELECT id,deps FROM checks")}
            seen, active = set(), set()

            def visit(identity):
                require(identity not in active, "Dependency cycle")
                if identity in seen:
                    return
                active.add(identity)
                for dependency in graph[identity]:
                    visit(dependency)
                active.remove(identity)
                seen.add(identity)

            for identity in graph:
                visit(identity)
        return {"checks": result}

    def artifacts(self, attempt):
        return [dict(row) for row in self.db.execute(
            "SELECT id,path,sha256,bytes FROM artifacts WHERE attempt_id=? ORDER BY id", (attempt,))]

    def evidence_valid(self, attempt):
        artifacts = self.artifacts(attempt)
        if not artifacts:
            return False
        for artifact in artifacts:
            path = (self.root / artifact["path"]).resolve()
            if not path.is_relative_to(self.root) or not path.is_file():
                return False
            if path.stat().st_size != artifact["bytes"] or digest_file(path) != artifact["sha256"]:
                return False
        return True

    def historical_valid(self, check):
        """Verify immutable evidence and dependency versions, independent of reuse TTL."""
        if check["status"] != "done" or not self.evidence_valid(check["latest_attempt"]):
            return False
        snapshot = json.loads(self.attempt(check["latest_attempt"])["dependency_snapshot"])
        for identity in json.loads(check["deps"]):
            dependency = self.check(identity)
            if snapshot.get(identity) != dependency["latest_attempt"] or not self.historical_valid(dependency):
                return False
        return True

    def effective_status(self, check):
        if check["status"] != "done":
            return check["status"]
        if check["expires"] is not None and check["expires"] <= time.time():
            return "stale"
        spec = json.loads(check["spec"])
        if spec["target_version"] == "unversioned" and check["expires"] is None:
            return "stale"
        if not self.evidence_valid(check["latest_attempt"]):
            return "evidence_invalid"
        snapshot = json.loads(self.attempt(check["latest_attempt"])["dependency_snapshot"])
        for dependency in json.loads(check["deps"]):
            row = self.check(dependency)
            if self.effective_status(row) != "done" or snapshot.get(dependency) != row["latest_attempt"]:
                return "dependency_changed"
        return "done"

    def begin(self, identity, provider, tool, retest_reason="", invocation_digest=""):
        text_field(provider, "provider", 120)
        text_field(tool, "tool", 300)
        if retest_reason:
            text_field(retest_reason, "retest_reason", 1000)
        with self.transaction():
            check = self.check(identity)
            if invocation_digest and check["latest_attempt"]:
                require(self.attempt(check["latest_attempt"])["invocation_digest"] == invocation_digest,
                        "Command changed; plan a new check with updated inputs or method_version")
            state = self.effective_status(check)
            if state in ACTIVE:
                return {"decision": "hold", "status": state, "check_id": check["id"],
                        "attempt_id": check["latest_attempt"], "next": "Review or reconcile the existing attempt"}
            if state == "done" and not retest_reason:
                return {"decision": "reuse", "check_id": check["id"],
                        "attempt_id": check["latest_attempt"], "summary": check["summary"],
                        "evidence_ids": [a["id"] for a in self.artifacts(check["latest_attempt"])]}
            if state != "pending" and not retest_reason:
                return {"decision": "hold", "status": state, "check_id": check["id"],
                        "next": "Record the changed prerequisite or retest reason"}
            for dependency in json.loads(check["deps"]):
                if self.effective_status(self.check(dependency)) != "done":
                    return {"decision": "hold", "status": "dependency_blocked", "dependency": dependency}
            snapshot = {d: self.check(d)["latest_attempt"] for d in json.loads(check["deps"])}
            attempt = "CALL-" + uuid.uuid4().hex
            self.db.execute("INSERT INTO attempts(id,check_id,status,provider,tool,started,retest_reason,"
                            "invocation_digest,dependency_snapshot) VALUES(?,?,'running',?,?,?,?,?,?)",
                            (attempt, check["id"], provider, tool, time.time(), retest_reason,
                             invocation_digest, encode(snapshot)))
            self.db.execute("UPDATE checks SET status='running',latest_attempt=?,expires=NULL WHERE id=?",
                            (attempt, check["id"]))
            self.event("call_started", attempt, {"check_id": check["id"], "provider": provider,
                                               "tool": tool, "retest_reason": retest_reason})
        return {"decision": "execute", "check_id": check["id"], "attempt_id": attempt}

    def import_artifact(self, source):
        source = Path(source).resolve()
        require(source.is_file(), "Artifact source must exist")
        identity = "E-" + uuid.uuid4().hex
        directory = self.root / "evidence" / "artifacts"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        require(directory.resolve().is_relative_to(self.root), "Artifact directory escapes case")
        destination = directory / identity
        digest, size = hashlib.sha256(), 0
        with source.open("rb") as incoming, destination.open("xb") as outgoing:
            if os.name != "nt":
                os.chmod(destination, 0o600)
            for block in iter(lambda: incoming.read(1024 * 1024), b""):
                outgoing.write(block)
                digest.update(block)
                size += len(block)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        return {"id": identity, "path": destination.relative_to(self.root).as_posix(),
                "sha256": digest.hexdigest(), "bytes": size}

    def record(self, attempt_id, status, summary, paths=()):
        require(status in {"review", "failed", "blocked", "unknown"}, "Invalid recorded result status")
        text_field(summary, "summary", 1200)
        require(self.attempt(attempt_id)["status"] == "running", "Attempt is no longer running")
        require(status != "review" or bool(paths), "Review requires captured evidence")
        artifacts = [self.import_artifact(path) for path in paths]
        with self.transaction():
            require(self.attempt(attempt_id)["status"] == "running", "Attempt changed while recording")
            self.db.executemany("INSERT INTO artifacts VALUES(?,?,?,?,?)", [
                (a["id"], attempt_id, a["path"], a["sha256"], a["bytes"]) for a in artifacts])
            self.db.execute("UPDATE attempts SET status=?,finished=?,summary=? WHERE id=?",
                            (status, time.time(), summary, attempt_id))
            self.db.execute("UPDATE checks SET status=?,summary=? WHERE latest_attempt=?",
                            (status, summary, attempt_id))
            self.event("call_recorded", attempt_id, {"status": status, "evidence_ids": [a["id"] for a in artifacts]})
        return {"status": status, "attempt_id": attempt_id, "evidence_ids": [a["id"] for a in artifacts]}

    def review(self, attempt_id, verdict, summary, valid_for=0):
        require(verdict in {"done", "failed", "blocked"}, "Invalid review verdict")
        text_field(summary, "summary", 1200)
        require(math.isfinite(valid_for) and valid_for >= 0, "valid_for must be finite and nonnegative")
        with self.transaction():
            attempt = self.attempt(attempt_id)
            if attempt["status"] == verdict:
                if verdict == "done":
                    require(self.evidence_valid(attempt_id), "Missing or changed evidence")
                # A replay after compaction acknowledges the original review;
                # it must not renew freshness or silently rewrite its conclusion.
                return {"status": verdict, "attempt_id": attempt_id, "decision": "already_reviewed",
                        "summary": attempt["summary"], "freshness_renewed": False}
            require(attempt["status"] == "review", "Only captured results can be reviewed")
            if verdict == "done":
                self.validate_review_evidence(attempt, valid_for)
            expires = time.time() + valid_for if valid_for else None
            self.db.execute("UPDATE attempts SET status=?,summary=? WHERE id=?", (verdict, summary, attempt_id))
            self.db.execute("UPDATE checks SET status=?,summary=?,expires=? WHERE latest_attempt=?",
                            (verdict, summary, expires, attempt_id))
            self.event("result_reviewed", attempt_id, {"verdict": verdict, "summary": summary, "expires": expires})
        return {"status": verdict, "attempt_id": attempt_id}

    def validate_review_evidence(self, attempt, valid_for):
        require(self.evidence_valid(attempt["id"]), "Missing or changed evidence")
        check = self.check(attempt["check_id"])
        snapshot = json.loads(attempt["dependency_snapshot"])
        for dependency in json.loads(check["deps"]):
            row = self.check(dependency)
            # Historical observations survive reuse TTL expiry. Changed versions
            # and altered evidence still reject acceptance, including ancestors.
            require(self.historical_valid(row) and snapshot.get(dependency) == row["latest_attempt"],
                    "Dependency changed during this attempt; record a failed/blocked review")
        require(json.loads(check["spec"])["target_version"] != "unversioned" or valid_for > 0,
                "Unversioned targets require an explicit validity period")

    def reconcile(self, attempt_id, outcome, summary, paths):
        require(outcome in {"observed", "not_executed"}, "Invalid reconciliation outcome")
        text_field(summary, "summary", 1200)
        require(bool(paths), "Reconciliation requires evidence of remote state or results")
        require(self.attempt(attempt_id)["status"] in {"running", "unknown"}, "Attempt does not need reconciliation")
        artifacts = [self.import_artifact(path) for path in paths]
        status = "review" if outcome == "observed" else "failed"
        with self.transaction():
            require(self.attempt(attempt_id)["status"] in {"running", "unknown"}, "Attempt already reconciled")
            self.db.executemany("INSERT INTO artifacts VALUES(?,?,?,?,?)", [
                (a["id"], attempt_id, a["path"], a["sha256"], a["bytes"]) for a in artifacts])
            self.db.execute("UPDATE attempts SET status=?,summary=?,finished=? WHERE id=?",
                            (status, summary, time.time(), attempt_id))
            self.db.execute("UPDATE checks SET status=?,summary=? WHERE latest_attempt=?", (status, summary, attempt_id))
            self.event("call_reconciled", attempt_id, {"outcome": outcome, "summary": summary})
        return {"status": status, "attempt_id": attempt_id, "evidence_ids": [a["id"] for a in artifacts]}

    def note(self, kind, text, check_id=None, evidence_ids=(), supersedes=None):
        require(kind in NOTE_KINDS, "Unknown note kind; choose one of: " + ", ".join(NOTE_KINDS))
        text_field(text, "note", 2000)
        check_id = self.check(check_id)["id"] if check_id else None
        for identity in evidence_ids:
            require(self.db.execute("SELECT 1 FROM artifacts WHERE id=?", (identity,)).fetchone(),
                    "Unknown evidence ID in note")
        identity = "N-" + uuid.uuid4().hex
        with self.transaction():
            if supersedes:
                previous = self.db.execute("SELECT * FROM notes WHERE id=? AND superseded=0", (supersedes,)).fetchone()
                require(previous is not None and previous["check_id"] == check_id, "Invalid superseded note")
                self.db.execute("UPDATE notes SET superseded=1 WHERE id=?", (supersedes,))
            self.db.execute("INSERT INTO notes VALUES(?,?,?,?,?,0,?)",
                            (identity, check_id, kind, text, encode(list(evidence_ids)), time.time()))
            self.event("note_added", identity, {"kind": kind, "check_id": check_id, "supersedes": supersedes})
        return {"note_id": identity}
