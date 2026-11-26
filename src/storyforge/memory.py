"""SQLite-Speicher und Freigabeablauf für SF-001."""

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from .models import Branch, Project, Proposal, Revision, Snapshot


class ConflictError(ValueError):
    """Der Entwurf basiert auf einer veralteten Revision."""


class NotFoundError(KeyError):
    """Eine angeforderte ID existiert nicht."""


def _dump(snapshot: Snapshot) -> str:
    return snapshot.model_dump_json()


def _hash(snapshot: Snapshot) -> str:
    canonical = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Memory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def _migrate(self):
        with self._connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 3:
                raise RuntimeError(f"Unbekannte Datenbankversion: {version}")
            if version == 0:
                db.executescript("""
                        BEGIN IMMEDIATE;
                        CREATE TABLE universes (
                            id TEXT PRIMARY KEY, title TEXT NOT NULL
                        );
                        CREATE TABLE projects (
                            id TEXT PRIMARY KEY, title TEXT NOT NULL,
                            universe_id TEXT REFERENCES universes(id)
                        );
                        CREATE TABLE works (
                            id TEXT PRIMARY KEY, project_id TEXT NOT NULL UNIQUE REFERENCES projects(id),
                            title TEXT NOT NULL
                        );
                        CREATE TABLE revisions (
                            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                            branch_id TEXT NOT NULL, parent_id TEXT REFERENCES revisions(id),
                            created_at TEXT NOT NULL, author TEXT NOT NULL,
                            description TEXT NOT NULL, content_hash TEXT NOT NULL,
                            snapshot TEXT NOT NULL
                        );
                        CREATE TABLE branches (
                            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                            name TEXT NOT NULL, head_id TEXT NOT NULL REFERENCES revisions(id),
                            UNIQUE(project_id, name)
                        );
                        CREATE TABLE proposals (
                            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                            branch_id TEXT NOT NULL REFERENCES branches(id),
                            base_revision_id TEXT NOT NULL REFERENCES revisions(id),
                            description TEXT NOT NULL, snapshot TEXT NOT NULL,
                            status TEXT NOT NULL CHECK(status IN ('offen', 'übernommen', 'abgelehnt'))
                        );
                        PRAGMA user_version = 1;
                        COMMIT;
                    """)
                version = 1
            if version == 1:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE conversation_turns (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL REFERENCES projects(id),
                        branch_id TEXT NOT NULL REFERENCES branches(id),
                        revision_id TEXT NOT NULL REFERENCES revisions(id),
                        role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        manifest TEXT,
                        model TEXT,
                        proposal_id TEXT REFERENCES proposals(id)
                    );
                    CREATE INDEX conversation_turns_context
                        ON conversation_turns(project_id, branch_id, created_at);
                    PRAGMA user_version = 2;
                    COMMIT;
                """)
                version = 2
            if version == 2:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE creative_runs (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL REFERENCES projects(id),
                        branch_id TEXT NOT NULL REFERENCES branches(id),
                        revision_id TEXT NOT NULL REFERENCES revisions(id),
                        created_at TEXT NOT NULL,
                        model TEXT NOT NULL,
                        task TEXT NOT NULL,
                        manifest TEXT NOT NULL,
                        candidates TEXT NOT NULL,
                        reflection TEXT,
                        metrics TEXT NOT NULL
                    );
                    PRAGMA user_version = 3;
                    COMMIT;
                """)

    def create_project(self, title: str, *, work_title: str | None = None,
                       universe_title: str | None = None, universe_id: UUID | None = None) -> Project:
        if not title.strip():
            raise ValueError("Projekttitel fehlt")
        if work_title is not None and not work_title.strip():
            raise ValueError("Werktitel fehlt")
        if universe_id and universe_title:
            raise ValueError("Universum per ID oder neuem Titel wählen")
        project_id, work_id, branch_id, revision_id = (uuid4() for _ in range(4))
        with self._connection() as db, db:
            if universe_title is not None:
                if not universe_title.strip():
                    raise ValueError("Universumstitel fehlt")
                universe_id = uuid4()
                db.execute("INSERT INTO universes VALUES (?, ?)", (str(universe_id), universe_title))
            if universe_id and not db.execute("SELECT 1 FROM universes WHERE id=?", (str(universe_id),)).fetchone():
                raise NotFoundError(universe_id)
            db.execute("INSERT INTO projects VALUES (?, ?, ?)",
                       (str(project_id), title, str(universe_id) if universe_id else None))
            db.execute("INSERT INTO works VALUES (?, ?, ?)", (str(work_id), str(project_id), work_title or title))
            self._insert_revision(db, revision_id, project_id, branch_id, None, "System", "Projekt angelegt", Snapshot())
            db.execute("INSERT INTO branches VALUES (?, ?, ?, ?)",
                       (str(branch_id), str(project_id), "Original", str(revision_id)))
        return self.get_project(project_id)

    def get_project(self, project_id: UUID) -> Project:
        with self._connection() as db:
            row = db.execute("""SELECT p.id, p.title, w.id AS work_id, w.title AS work_title,
                u.id AS universe_id, u.title AS universe_title FROM projects p
                JOIN works w ON w.project_id=p.id LEFT JOIN universes u ON u.id=p.universe_id
                WHERE p.id=?""", (str(project_id),)).fetchone()
        if row is None:
            raise NotFoundError(project_id)
        return Project.model_validate(dict(row))

    def list_branches(self, project_id: UUID) -> list[Branch]:
        self.get_project(project_id)
        with self._connection() as db:
            rows = db.execute("SELECT * FROM branches WHERE project_id=? ORDER BY name", (str(project_id),)).fetchall()
        return [Branch.model_validate(dict(row)) for row in rows]

    def get_revision(self, revision_id: UUID) -> Revision:
        with self._connection() as db:
            row = db.execute("SELECT * FROM revisions WHERE id=?", (str(revision_id),)).fetchone()
        if row is None:
            raise NotFoundError(revision_id)
        return Revision.model_validate({**dict(row), "snapshot": json.loads(row["snapshot"])})

    def create_branch(self, project_id: UUID, name: str, from_revision_id: UUID) -> Branch:
        if not name.strip():
            raise ValueError("Variantenname fehlt")
        source = self.get_revision(from_revision_id)
        if source.project_id != project_id:
            raise ValueError("Revision gehört zu anderem Projekt")
        branch_id = uuid4()
        with self._connection() as db, db:
            db.execute("INSERT INTO branches VALUES (?, ?, ?, ?)",
                       (str(branch_id), str(project_id), name, str(from_revision_id)))
        return Branch(id=branch_id, project_id=project_id, name=name, head_id=from_revision_id)

    def propose(self, branch_id: UUID, base_revision_id: UUID, snapshot: Snapshot,
                description: str) -> Proposal:
        snapshot = Snapshot.model_validate(snapshot)
        if len({idea.id for idea in snapshot.ideas}) != len(snapshot.ideas):
            raise ValueError("Stoffideen-IDs müssen eindeutig sein")
        if len({decision.id for decision in snapshot.decisions}) != len(snapshot.decisions):
            raise ValueError("Entscheidungs-IDs müssen eindeutig sein")
        with self._connection() as db, db:
            branch = db.execute("SELECT * FROM branches WHERE id=?", (str(branch_id),)).fetchone()
            if branch is None:
                raise NotFoundError(branch_id)
            if branch["head_id"] != str(base_revision_id):
                raise ConflictError("Veraltete Ausgangsrevision")
            previous = self.get_revision(base_revision_id).snapshot
            if snapshot.decisions[:len(previous.decisions)] != previous.decisions:
                raise ValueError("Autorenentscheidungen dürfen nicht entfernt oder geändert werden")
            proposal_id = uuid4()
            db.execute("INSERT INTO proposals VALUES (?, ?, ?, ?, ?, ?, 'offen')",
                       (str(proposal_id), branch["project_id"], str(branch_id),
                        str(base_revision_id), description, _dump(snapshot)))
        return self.get_proposal(proposal_id)

    def get_proposal(self, proposal_id: UUID) -> Proposal:
        with self._connection() as db:
            row = db.execute("SELECT * FROM proposals WHERE id=?", (str(proposal_id),)).fetchone()
        if row is None:
            raise NotFoundError(proposal_id)
        return Proposal.model_validate({**dict(row), "snapshot": json.loads(row["snapshot"])})

    def list_turns(self, project_id: UUID, branch_id: UUID, *, limit: int = 20) -> list[dict]:
        if limit < 0:
            raise ValueError("Limit darf nicht negativ sein")
        with self._connection() as db:
            rows = db.execute("""SELECT * FROM (
                SELECT rowid AS sequence, * FROM conversation_turns WHERE project_id=? AND branch_id=?
                ORDER BY sequence DESC LIMIT ?
            ) ORDER BY sequence""", (str(project_id), str(branch_id), limit)).fetchall()
        return [dict(row) for row in rows]

    def save_exchange(self, project_id: UUID, branch_id: UUID, revision_id: UUID,
                      user_text: str, answer: str, manifest: dict, model: str,
                      proposal_id: UUID | None = None) -> tuple[UUID, UUID]:
        """Speichert beide Gesprächsbeiträge zusammen, getrennt von Revisionen."""
        user_id, assistant_id = uuid4(), uuid4()
        stamp = datetime.now(timezone.utc).isoformat()
        with self._connection() as db, db:
            db.execute("""INSERT INTO conversation_turns
                (id, project_id, branch_id, revision_id, role, content, created_at)
                VALUES (?, ?, ?, ?, 'user', ?, ?)""",
                (str(user_id), str(project_id), str(branch_id), str(revision_id), user_text, stamp))
            db.execute("""INSERT INTO conversation_turns
                (id, project_id, branch_id, revision_id, role, content, created_at, manifest, model, proposal_id)
                VALUES (?, ?, ?, ?, 'assistant', ?, ?, ?, ?, ?)""",
                (str(assistant_id), str(project_id), str(branch_id), str(revision_id), answer, stamp,
                 json.dumps(manifest, ensure_ascii=False), model, str(proposal_id) if proposal_id else None))
        return user_id, assistant_id

    def save_creative_run(self, project_id: UUID, branch_id: UUID, revision_id: UUID,
                          model: str, task: str, manifest: dict, candidates: list[dict],
                          reflection: dict | None = None, metrics: dict | None = None) -> UUID:
        """Speichert ein unverbindliches Ergebnis getrennt von Revisionen."""
        run_id = uuid4()
        with self._connection() as db, db:
            db.execute("""INSERT INTO creative_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (str(run_id), str(project_id), str(branch_id), str(revision_id),
                        datetime.now(timezone.utc).isoformat(), model, task,
                        json.dumps(manifest, ensure_ascii=False),
                        json.dumps(candidates, ensure_ascii=False),
                        json.dumps(reflection, ensure_ascii=False) if reflection is not None else None,
                        json.dumps(metrics or {}, ensure_ascii=False)))
        return run_id

    def get_creative_run(self, run_id: UUID) -> dict:
        with self._connection() as db:
            row = db.execute("SELECT * FROM creative_runs WHERE id=?", (str(run_id),)).fetchone()
        if row is None:
            raise NotFoundError(run_id)
        result = dict(row)
        for field in ("manifest", "candidates", "reflection", "metrics"):
            result[field] = json.loads(result[field]) if result[field] is not None else None
        return result

    def reject(self, proposal_id: UUID):
        with self._connection() as db, db:
            changed = db.execute("UPDATE proposals SET status='abgelehnt' WHERE id=? AND status='offen'",
                                 (str(proposal_id),)).rowcount
            if not changed:
                raise ValueError("Offener Entwurf nicht gefunden")

    def approve(self, proposal_id: UUID, *, approved_by: str, explicit_approval: bool) -> Revision:
        if not explicit_approval or not approved_by.strip():
            raise PermissionError("Ausdrückliche Autorfreigabe erforderlich")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT * FROM proposals WHERE id=?", (str(proposal_id),)).fetchone()
                if row is None:
                    raise NotFoundError(proposal_id)
                if row["status"] != "offen":
                    raise ValueError("Entwurf ist nicht offen")
                branch = db.execute("SELECT head_id FROM branches WHERE id=?", (row["branch_id"],)).fetchone()
                if branch["head_id"] != row["base_revision_id"]:
                    raise ConflictError("Veraltete Ausgangsrevision")
                snapshot = Snapshot.model_validate_json(row["snapshot"])
                revision_id = uuid4()
                self._insert_revision(db, revision_id, UUID(row["project_id"]), UUID(row["branch_id"]),
                                      UUID(row["base_revision_id"]), approved_by, row["description"], snapshot)
                changed = db.execute("UPDATE branches SET head_id=? WHERE id=? AND head_id=?",
                                     (str(revision_id), row["branch_id"], row["base_revision_id"])).rowcount
                if changed != 1:
                    raise ConflictError("Veraltete Ausgangsrevision")
                db.execute("UPDATE proposals SET status='übernommen' WHERE id=?", (str(proposal_id),))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.get_revision(revision_id)

    def restore(self, branch_id: UUID, revision_id: UUID, *, description: str = "Revision wiederherstellen") -> Proposal:
        source = self.get_revision(revision_id)
        with self._connection() as db:
            branch = db.execute("SELECT * FROM branches WHERE id=?", (str(branch_id),)).fetchone()
        if branch is None:
            raise NotFoundError(branch_id)
        if source.project_id != UUID(branch["project_id"]):
            raise ValueError("Revision gehört zu anderem Projekt")
        current = self.get_revision(UUID(branch["head_id"]))
        snapshot = Snapshot(ideas=source.snapshot.ideas, decisions=current.snapshot.decisions)
        return self.propose(branch_id, current.id, snapshot, description)

    def _insert_revision(self, db, revision_id, project_id, branch_id, parent_id, author, description, snapshot):
        db.execute("INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (str(revision_id), str(project_id), str(branch_id), str(parent_id) if parent_id else None,
                    datetime.now(timezone.utc).isoformat(), author, description, _hash(snapshot), _dump(snapshot)))

    def export_json(self, project_id: UUID) -> str:
        project, branches, revisions = self._export_data(project_id)
        payload = {"schema_version": 1, "project": project.model_dump(mode="json"),
                   "branches": [branch.model_dump(mode="json") for branch in branches],
                   "revisions": [revision.model_dump(mode="json") for revision in revisions]}
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def export_markdown(self, project_id: UUID) -> str:
        project, branches, revisions = self._export_data(project_id)
        by_id = {revision.id: revision for revision in revisions}
        lines = [f"# {project.title}", "", f"Projekt-ID: `{project.id}`  ",
                 f"Werk: {project.work_title} (`{project.work_id}`)  ",
                 f"Universum: {project.universe_title or 'keines'}", ""]
        for branch in branches:
            revision = by_id[branch.head_id]
            lines += [f"## Variante: {branch.name}", "", f"Revision: `{revision.id}`", "", "### Stoffideen", ""]
            for idea in revision.snapshot.ideas:
                lines += [f"- **{idea.title}** (`{idea.id}`): {idea.premise}"]
            if not revision.snapshot.ideas:
                lines += ["- Keine Stoffideen."]
            lines += ["", "### Autorenentscheidungen", ""]
            for decision in revision.snapshot.decisions:
                lines += [f"- **{decision.target}**: {decision.action} – {decision.rationale} ({decision.author})"]
            if not revision.snapshot.decisions:
                lines += ["- Keine Entscheidungen."]
            lines += [""]
        return "\n".join(lines)

    def _export_data(self, project_id: UUID) -> tuple[Project, list[Branch], list[Revision]]:
        # Ein SQLite-Lese-Snapshot verhindert gemischte Revisionsstände bei paralleler Freigabe.
        with self._connection() as db:
            db.execute("BEGIN")
            row = db.execute("""SELECT p.id, p.title, w.id AS work_id, w.title AS work_title,
                u.id AS universe_id, u.title AS universe_title FROM projects p
                JOIN works w ON w.project_id=p.id LEFT JOIN universes u ON u.id=p.universe_id
                WHERE p.id=?""", (str(project_id),)).fetchone()
            if row is None:
                raise NotFoundError(project_id)
            project = Project.model_validate(dict(row))
            branch_rows = db.execute("SELECT * FROM branches WHERE project_id=? ORDER BY name",
                                     (str(project_id),)).fetchall()
            revision_rows = db.execute("SELECT * FROM revisions WHERE project_id=? ORDER BY created_at, rowid",
                                       (str(project_id),)).fetchall()
        branches = [Branch.model_validate(dict(item)) for item in branch_rows]
        revisions = [Revision.model_validate({**dict(item), "snapshot": json.loads(item["snapshot"])})
                     for item in revision_rows]
        return project, branches, revisions

    def export_file(self, project_id: UUID, path: str | Path, *, format: str) -> Path:
        """Schreibt einen Export atomar in die angegebene Datei."""
        if format not in {"json", "markdown"}:
            raise ValueError("Format muss 'json' oder 'markdown' sein")
        content = self.export_json(project_id) if format == "json" else self.export_markdown(project_id)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=target.parent, prefix=f".{target.name}.",
                                             delete=False) as file:
                temporary = Path(file.name)
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return target
