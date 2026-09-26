"""Explicit session/case bindings and cooperative tool-context ownership."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from fusion_store import PACK, encode, require, text_field

SCHEMA = """
CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE cases(id TEXT PRIMARY KEY,path TEXT UNIQUE NOT NULL,project TEXT NOT NULL,
 scope_digest TEXT NOT NULL,targets TEXT NOT NULL);
CREATE TABLE sessions(id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),
 active INTEGER NOT NULL,created REAL NOT NULL);
CREATE UNIQUE INDEX one_writer ON sessions(case_id) WHERE active=1;
CREATE TABLE contexts(slot TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),
 provider TEXT NOT NULL,observation TEXT NOT NULL);
CREATE TABLE audit(seq INTEGER PRIMARY KEY,at REAL NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL);
"""


def scope_digest(case):
    return hashlib.sha256(encode(case.meta("config")).encode("utf-8")).hexdigest()


@contextlib.contextmanager
def file_lock(path):
    """Crash-released cooperative lock, held across a local CLI operation."""
    stream = path.open("a+b")
    locked = False
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            require(False, "case_busy: another local operation is still running")
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)
        stream.close()


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        path = self.root / "workspace.sqlite3"
        require(path.is_file() and not path.is_symlink(), "Workspace not found; run workspace-init")
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA synchronous=FULL")
        require(self.setting("schema") == "1", "Unsupported workspace schema")

    @classmethod
    def create(cls, root):
        from fusion_memory import initialize_memory
        root = Path(root).resolve()
        require(root != PACK and PACK not in root.parents, "Keep workspace data outside the installed skill")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = root / "workspace.sqlite3"
        require(not path.exists(), "Workspace already exists; reuse it")
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        database = sqlite3.connect(path)
        try:
            database.executescript(SCHEMA)
            database.executemany("INSERT INTO settings VALUES(?,?)",
                                 [("schema", "1"), ("workspace_id", "WS-" + uuid.uuid4().hex)])
            initialize_memory(database)
            database.commit()
        finally:
            database.close()
        return cls(root)

    def close(self):
        self.db.close()

    def setting(self, key):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        require(row is not None, "Workspace setting missing: " + key)
        return row[0]

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def audit(self, kind, payload):
        self.db.execute("INSERT INTO audit(at,kind,payload) VALUES(?,?,?)", (time.time(), kind, encode(payload)))

    def lock_path(self, case):
        name = hashlib.sha256(case.meta("case_id").encode("utf-8")).hexdigest()
        return self.root / (name + ".lock")

    def registration(self, case):
        pinned = case.db.execute("SELECT value FROM meta WHERE key='workspace_binding'").fetchone()
        require(pinned is not None, "Case has no workspace binding")
        pinned = json.loads(pinned[0])
        require(pinned["workspace_id"] == self.setting("workspace_id") and pinned["workspace_path"] == str(self.root),
                "Case is pinned to another workspace registry")
        row = self.db.execute("SELECT * FROM cases WHERE id=?", (case.meta("case_id"),)).fetchone()
        require(row is not None, "Case is not bound in this workspace")
        require(row["path"] == str(case.root) and row["scope_digest"] == scope_digest(case),
                "case_snapshot_mismatch: path or scope changed; inspect before proceeding")
        require(row["project"] == pinned["project"] and json.loads(row["targets"]) == pinned["targets"],
                "Case registration does not match its pinned project/targets")
        return dict(row)

    def bind(self, case, session, project, expected_id, targets):
        text_field(session, "session", 160)
        text_field(project, "project", 160)
        require(expected_id == case.meta("case_id"), "Wrong expected case ID")
        require(isinstance(targets, list) and targets, "Bind explicit canonical targets")
        for target in targets:
            text_field(target, "target", 1000)
        targets = sorted(set(targets))
        existing_targets = {r[0] for r in case.db.execute("SELECT DISTINCT target FROM checks")}
        require(existing_targets <= set(targets), "Existing checks include targets outside this binding")
        identity = case.meta("case_id")
        with file_lock(self.lock_path(case)), self.transaction():
            binding = {"workspace_id": self.setting("workspace_id"), "workspace_path": str(self.root),
                       "project": project, "targets": targets}
            pinned = case.db.execute("SELECT value FROM meta WHERE key='workspace_binding'").fetchone()
            require(pinned is None or json.loads(pinned[0]) == binding,
                    "Case is already pinned to another registry/project/target set")
            old = self.db.execute("SELECT * FROM cases WHERE id=?", (identity,)).fetchone()
            if old:
                registration = self.registration(case)
                require(registration["project"] == project and json.loads(registration["targets"]) == targets,
                        "Case project/targets are immutable; create a new case for changed scope")
            else:
                self.db.execute("INSERT INTO cases VALUES(?,?,?,?,?)",
                                (identity, str(case.root), project, scope_digest(case), encode(targets)))
            session_row = self.db.execute("SELECT * FROM sessions WHERE id=?", (session,)).fetchone()
            if session_row:
                require(session_row["case_id"] == identity and session_row["active"],
                        "Session is bound elsewhere or retired; use a new explicit session ID")
            else:
                require(not self.db.execute("SELECT 1 FROM sessions WHERE case_id=? AND active=1", (identity,)).fetchone(),
                        "Case already has an owner; use handoff")
                self.db.execute("INSERT INTO sessions VALUES(?,?,1,?)", (session, identity, time.time()))
                self.audit("session_bound", {"session": session, "case_id": identity, "project": project})
            with case.transaction():
                pinned = case.db.execute("SELECT value FROM meta WHERE key='workspace_binding'").fetchone()
                require(pinned is None or json.loads(pinned[0]) == binding, "Concurrent registry binding changed")
                case.db.execute("INSERT OR IGNORE INTO meta VALUES('workspace_binding',?)", (encode(binding),))
        return {"session": session, "case_id": identity, "project": project, "targets": targets}

    def check_session(self, case, session):
        registration = self.registration(case)
        row = self.db.execute("SELECT * FROM sessions WHERE id=?", (session,)).fetchone()
        require(row is not None and row["active"] and row["case_id"] == registration["id"],
                "session_case_mismatch: refuse to read or write another case")
        return registration

    @contextlib.contextmanager
    def operation(self, case, session):
        with file_lock(self.lock_path(case)):
            registration = self.check_session(case, session)
            yield registration

    def handoff(self, case, session, successor, reason):
        text_field(successor, "successor session", 160)
        text_field(reason, "handoff reason", 1000)
        with self.operation(case, session), self.transaction():
            require(not self.db.execute("SELECT 1 FROM sessions WHERE id=?", (successor,)).fetchone(),
                    "Successor session ID already exists")
            self.db.execute("UPDATE sessions SET active=0 WHERE id=?", (session,))
            self.db.execute("INSERT INTO sessions VALUES(?,?,1,?)", (successor, case.meta("case_id"), time.time()))
            self.audit("handoff", {"from": session, "to": successor, "reason": reason, "case_id": case.meta("case_id")})
        return {"session": successor, "case_id": case.meta("case_id"), "unresolved_calls": "preserved"}

    def require_target(self, case, target):
        require(target in json.loads(self.registration(case)["targets"]), "Target is outside the case binding")

    def context_set(self, case, slot, observation):
        text_field(slot, "slot", 300)
        require(isinstance(observation, dict), "Context observation must be an object")
        for key in ("provider", "context_id", "target", "identity_ref", "evidence_ref"):
            text_field(observation.get(key), key, 1000)
        self.require_target(case, observation["target"])
        self.check_observation_age(observation)
        with self.transaction():
            self.require_resource_owner(case, slot, observation)
            row = self.db.execute("SELECT * FROM contexts WHERE slot=?", (slot,)).fetchone()
            require(row is None or row["case_id"] == case.meta("case_id"), "Tool context is owned by another case")
            if row:
                previous = json.loads(row["observation"])
                changed = any(previous[k] != observation[k] for k in ("provider", "context_id", "target", "identity_ref"))
                pending = case.db.execute("SELECT 1 FROM attempts WHERE provider=? AND status IN ('running','unknown','review')",
                                          (row["provider"],)).fetchone()
                require(not (changed and pending), "Resolve pending provider calls before switching context")
            self.db.execute("INSERT OR REPLACE INTO contexts VALUES(?,?,?,?)",
                            (slot, case.meta("case_id"), observation["provider"], encode(observation)))
            self.audit("context_observed", {"slot": slot, "case_id": case.meta("case_id"), "observation": observation})
        return {"slot": slot, "case_id": case.meta("case_id"), "health": "caller_observed_not_independently_probed"}

    def require_resource_owner(self, case, slot, observation):
        # Slot names are aliases, not isolation boundaries. Run this inside the
        # registry write transaction so two cases cannot both claim the resource.
        for row in self.db.execute("SELECT * FROM contexts WHERE slot<>?", (slot,)):
            other = json.loads(row["observation"])
            same = (other["provider"], other["context_id"]) == (observation["provider"], observation["context_id"])
            if same:
                require(row["case_id"] == case.meta("case_id"), "Tool resource is owned by another case, even under a different slot")
                require(False, "Tool resource already has a slot in this case; reuse or explicitly release that slot")

    @staticmethod
    def check_observation_age(observation):
        observed = observation.get("observed_at")
        require(isinstance(observed, (float, int)) and not isinstance(observed, bool) and
                -30 <= time.time() - observed <= 300, "Context observation missing or stale; observe again")

    def context_check(self, case, check_id, provider, slot):
        check = case.check(check_id)
        spec = json.loads(check["spec"])
        self.require_target(case, spec["target"])
        row = self.db.execute("SELECT * FROM contexts WHERE slot=?", (slot,)).fetchone()
        require(row is not None and row["case_id"] == case.meta("case_id") and row["provider"] == provider,
                "Missing or mismatched tool context binding")
        observed = json.loads(row["observation"])
        self.require_resource_owner(case, slot, observed)
        self.check_observation_age(observed)
        require(observed["target"] == spec["target"] and observed["identity_ref"] == spec["identity_ref"],
                "Tool target or identity does not match this check")
        return {"slot": slot, "observation": observed}

    def context_release(self, case, slot):
        with self.transaction():
            row = self.db.execute("SELECT * FROM contexts WHERE slot=?", (slot,)).fetchone()
            require(row is not None and row["case_id"] == case.meta("case_id"), "Context is not owned by this case")
            require(not case.db.execute("SELECT 1 FROM attempts WHERE provider=? AND status IN ('running','unknown','review')",
                                        (row["provider"],)).fetchone(), "Resolve pending provider calls before releasing context")
            self.db.execute("DELETE FROM contexts WHERE slot=?", (slot,))
            self.audit("context_released", {"slot": slot, "case_id": case.meta("case_id")})
        return {"released": slot}
