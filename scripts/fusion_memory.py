"""Reviewed, namespace-filtered experience cards; case facts stay in their own ledger."""
import json
import sqlite3
import time
import uuid

from fusion_store import encode, manifest, reject_credentials, require, text_field
from fusion_search import embedding, fallback_bm25, fused, text_digest, tokens
from fusion_views import bounded

SCHEMA = """
CREATE TABLE memories(
 id TEXT PRIMARY KEY,origin_project TEXT NOT NULL,scope TEXT NOT NULL DEFAULT 'project',
 state TEXT NOT NULL DEFAULT 'candidate',skill TEXT NOT NULL,document TEXT NOT NULL,
 digest TEXT NOT NULL,search_text TEXT NOT NULL,source TEXT NOT NULL,
 supersedes TEXT REFERENCES memories(id),expires REAL,
 UNIQUE(origin_project,digest));
CREATE TABLE embedding_models(model TEXT PRIMARY KEY,dimensions INTEGER NOT NULL);
CREATE TABLE embeddings(
 memory_id TEXT NOT NULL REFERENCES memories(id),model TEXT NOT NULL REFERENCES embedding_models(model),
 vector TEXT NOT NULL,PRIMARY KEY(memory_id,model));
"""


def initialize_memory(database):
    database.executescript(SCHEMA)
    engine = "fts5"
    try:
        database.execute("CREATE VIRTUAL TABLE memory_fts USING fts5(terms)")
    except sqlite3.OperationalError as exc:
        if "no such module" not in str(exc):
            raise
        engine = "python_bm25"
    database.execute("INSERT INTO settings VALUES('search_engine',?)", (engine,))


def validate_document(document):
    require(isinstance(document, dict), "Experience must be an object")
    allowed = {"title", "lesson", "conditions", "counterexamples", "tags", "skill_id"}
    require(set(document) == allowed, "Experience fields must be title/lesson/conditions/counterexamples/tags/skill_id")
    text_field(document["title"], "title", 160)
    text_field(document["lesson"], "lesson", 1200)
    for field in ("conditions", "counterexamples", "tags"):
        require(isinstance(document[field], list) and 1 <= len(document[field]) <= 8, field + " must be a nonempty short list")
        for item in document[field]:
            text_field(item, field, 300)
    require(document["skill_id"] in {m["id"] for m in manifest("specialists.json", "modules")}, "Unknown experience skill")
    reject_credentials(document)
    require(len(encode(document)) <= 4000, "Distill the experience into a small card")


class Memory:
    def __init__(self, workspace):
        self.workspace = workspace
        self.db = workspace.db

    def row(self, identity):
        row = self.db.execute("SELECT rowid,* FROM memories WHERE id=?", (identity,)).fetchone()
        require(row is not None, "Unknown experience ID")
        return dict(row)

    def source(self, case, note_id):
        note = case.db.execute("SELECT * FROM notes WHERE id=? AND superseded=0", (note_id,)).fetchone()
        require(note is not None and note["check_id"] is not None, "Use an active check-scoped source note")
        require(note["kind"] in {"fact", "negative", "refuted", "decision"}, "Unresolved hypotheses are not reusable evidence")
        check = case.check(note["check_id"])
        require(case.effective_status(check) == "done", "Source check must have valid completed evidence")
        evidence_ids = json.loads(note["evidence"])
        require(bool(evidence_ids), "Source note must cite evidence")
        artifacts = []
        for identity in evidence_ids:
            row = case.db.execute("SELECT * FROM artifacts WHERE id=?", (identity,)).fetchone()
            require(row is not None and case.evidence_valid(row["attempt_id"]), "Source evidence missing or changed")
            attempt = case.attempt(row["attempt_id"])
            owner = case.check(attempt["check_id"])
            require(owner["latest_attempt"] == attempt["id"] and case.effective_status(owner) == "done",
                    "Source evidence must belong to a currently valid completed check")
            artifacts.append({"id": identity, "sha256": row["sha256"]})
        return {"case_id": case.meta("case_id"), "note_id": note_id, "check_id": check["id"],
                "attempt_id": check["latest_attempt"], "note_digest": text_digest(note["text"]),
                "evidence": artifacts}

    def candidate(self, case, document, note_id, supersedes=None):
        validate_document(document)
        project = self.workspace.registration(case)["project"]
        source = self.source(case, note_id)
        digest = text_digest(encode(document))
        with self.workspace.transaction():
            old = self.db.execute("SELECT id FROM memories WHERE origin_project=? AND digest=?", (project, digest)).fetchone()
            if old:
                return {"memory_id": old["id"], "existing": True}
            if supersedes:
                previous = self.row(supersedes)
                require(previous["origin_project"] == project and previous["skill"] == document["skill_id"],
                        "Cannot supersede another project's experience or a different specialist")
            identity = "M-" + uuid.uuid4().hex
            search_text = " ".join([document["title"], document["lesson"]] +
                                   document["conditions"] + document["counterexamples"] + document["tags"])
            cursor = self.db.execute("INSERT INTO memories(id,origin_project,skill,document,digest,search_text,source,supersedes)"
                                     " VALUES(?,?,?,?,?,?,?,?)",
                                     (identity, project, document["skill_id"], encode(document), digest,
                                      search_text, encode(source), supersedes))
            if self.workspace.setting("search_engine") == "fts5":
                self.db.execute("INSERT INTO memory_fts(rowid,terms) VALUES(?,?)",
                                (cursor.lastrowid, " ".join(tokens(search_text))))
            self.workspace.audit("memory_candidate", {"memory_id": identity, "source": source})
        return {"memory_id": identity, "state": "candidate", "text_sha256": digest}

    def review(self, case, identity, verdict, scope, validation, redacted=False, valid_for=0):
        require(verdict in {"accept", "reject", "retire"}, "Invalid experience verdict")
        require(scope in {"project", "general"}, "Invalid experience scope")
        text_field(validation, "validation", 1000)
        with self.workspace.transaction():
            row = self.row(identity)
            require(row["origin_project"] == self.workspace.registration(case)["project"], "Cannot review another project's experience")
            expires = row["expires"]
            if verdict == "accept":
                require(row["state"] in {"candidate", "active"}, "Rejected or retired versions cannot be reactivated; create a revised candidate")
                require(redacted, "Review redaction and applicability before accepting")
                require(isinstance(valid_for, int) and 0 < valid_for <= 365 * 86400, "Use a validity period of 1..31536000 seconds")
                old_source = json.loads(row["source"])
                require(old_source["case_id"] == case.meta("case_id"), "Revalidate in the source case")
                require(self.source(case, old_source["note_id"]) == old_source, "Source changed since distillation; create a new candidate")
                expires = time.time() + valid_for
            state = {"accept": "active", "reject": "rejected", "retire": "retired"}[verdict]
            self.db.execute("UPDATE memories SET state=?,scope=?,expires=? WHERE id=?", (state, scope, expires, identity))
            if verdict == "accept" and row["supersedes"]:
                self.db.execute("UPDATE memories SET state='retired' WHERE id=?", (row["supersedes"],))
            self.workspace.audit("memory_review", {"memory_id": identity, "verdict": verdict, "scope": scope,
                                                  "validation": validation, "redacted": redacted, "expires": expires})
        return {"memory_id": identity, "state": state, "scope": scope, "expires": expires}

    def show(self, project, identity, include_general=False):
        row = self.row(identity)
        own = row["origin_project"] == project
        public = include_general and row["scope"] == "general" and row["state"] == "active" and (row["expires"] or 0) > time.time()
        require(own or public, "Experience is outside this project's namespace")
        result = {"memory_id": identity, "state": row["state"], "scope": row["scope"],
                  "document": json.loads(row["document"]), "text_sha256": row["digest"], "expires": row["expires"]}
        if own:
            result["embedding_text"] = row["document"]
            result["source"] = json.loads(row["source"])
        return result

    def embed(self, project, identity, data):
        row = self.row(identity)
        require(row["origin_project"] == project, "Cannot index another project's experience")
        model, vector = embedding(data, row["digest"])
        with self.workspace.transaction():
            config = self.db.execute("SELECT dimensions FROM embedding_models WHERE model=?", (model,)).fetchone()
            require(config is None or config["dimensions"] == len(vector), "Embedding dimensions changed; use a new model/version ID")
            self.db.execute("INSERT OR IGNORE INTO embedding_models VALUES(?,?)", (model, len(vector)))
            self.db.execute("INSERT OR REPLACE INTO embeddings VALUES(?,?,?)", (identity, model, encode(vector)))
            self.workspace.audit("memory_embedded", {"memory_id": identity, "model": model, "text_sha256": row["digest"]})
        return {"memory_id": identity, "model": model, "dimensions": len(vector)}

    def eligible(self, project, skill, include_general):
        clause = "(origin_project=? AND scope='project')"
        if include_general:
            clause = "(" + clause + " OR scope='general')"
        return ("state='active' AND expires>? AND skill=? AND " + clause,
                [time.time(), skill, project])

    def lexical(self, where, params, terms):
        if not terms:
            return []
        if self.workspace.setting("search_engine") == "fts5":
            match = " OR ".join('"' + term + '"' for term in sorted(set(terms)))
            rows = self.db.execute("SELECT m.id FROM memory_fts JOIN memories m ON m.rowid=memory_fts.rowid "
                                   "WHERE memory_fts MATCH ? AND " + where +
                                   " ORDER BY bm25(memory_fts),m.id LIMIT 100", [match] + params)
            return [r["id"] for r in rows]
        rows = self.db.execute("SELECT id,search_text FROM memories WHERE " + where, params).fetchall()
        return fallback_bm25(rows, terms)[:100]

    def semantic(self, where, params, query_text, data, minimum):
        require(0 < minimum <= 1, "min-cosine must be between 0 and 1")
        model, vector = embedding(data, text_digest(query_text))
        config = self.db.execute("SELECT dimensions FROM embedding_models WHERE model=?", (model,)).fetchone()
        require(config is not None and config["dimensions"] == len(vector), "No compatible embedding model/dimensions")
        rows = self.db.execute("SELECT m.id,e.vector FROM memories m JOIN embeddings e ON e.memory_id=m.id"
                               " WHERE e.model=? AND " + where + " LIMIT 10001", [model] + params)
        scored = []
        for index, row in enumerate(rows):
            require(index < 10000, "Exact vector scan exceeds 10000 eligible cards; narrow the namespace or use an indexed backend")
            similarity = sum(a * b for a, b in zip(vector, json.loads(row["vector"])))
            if similarity >= minimum:
                scored.append((similarity, row["id"]))
        return [identity for _, identity in sorted(scored, key=lambda item: (-item[0], item[1]))[:100]]

    def search(self, project, skill, query_text, include_general=False, data=None, minimum=0.5, limit=3, maximum=1800):
        with self.workspace.transaction():
            return self._search(project, skill, query_text, include_general, data, minimum, limit, maximum)

    def _search(self, project, skill, query_text, include_general, data, minimum, limit, maximum):
        text_field(query_text, "query", 1000)
        require(skill in {m["id"] for m in manifest("specialists.json", "modules")}, "Unknown specialist")
        require(1 <= limit <= 10, "limit must be between 1 and 10")
        where, params = self.eligible(project, skill, include_general)
        lexical = self.lexical(where, params, tokens(query_text))
        semantic = self.semantic(where, params, query_text, data, minimum) if data else []
        ranking = fused(lexical, semantic)
        result = {"engine": self.workspace.setting("search_engine") + ("+cosine+rrf" if data else ""),
                  "namespace": {"project": project, "include_general": include_general},
                  "use": "method_hints_not_target_facts_or_completion", "items": [], "omitted": 0}
        seen = set()
        candidates = []
        for identity, reasons in ranking:
            row = self.row(identity)
            if row["digest"] in seen:
                continue
            seen.add(row["digest"])
            candidates.append({"memory_id": identity, "scope": row["scope"], "document": json.loads(row["document"]),
                               "expires": row["expires"], "matched_by": reasons})
        result["omitted"] = len(candidates)
        for card in candidates[:limit]:
            result["items"].append(card)
            result["omitted"] -= 1
            if len(encode(result)) > maximum:
                result["items"].pop()
                result["omitted"] += 1
                if not result["items"]:
                    require(False, "context_budget_exceeded: full experience conditions do not fit; narrow or increase budget")
                break
        return bounded(result, maximum)
