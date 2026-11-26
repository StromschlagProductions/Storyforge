import json
import sqlite3
from uuid import uuid4

import pytest

from storyforge import ConflictError, Decision, Idea, Memory, Snapshot


def idea(title="Geheime Tür"):
    return Idea(id=uuid4(), title=title, premise="Eine Tür erscheint nur bei Stille.")


def decision():
    return Decision(id=uuid4(), target="Tonfall", action="beibehalten",
                    rationale="Trägt das Geheimnis", author="Autorin")


def test_neustart_ohne_skript_und_eindeutige_werke(tmp_path):
    path = tmp_path / "projekt.sqlite3"
    memory = Memory(path)
    first = memory.create_project("Testwerk", universe_title="Testuniversum")
    second = memory.create_project("Testwerk", universe_id=first.universe_id)
    reopened = Memory(path)
    assert reopened.get_project(first.id) == first
    assert reopened.get_project(second.id).universe_id == first.universe_id
    assert first.work_id != second.work_id
    assert reopened.get_revision(reopened.list_branches(first.id)[0].head_id).snapshot.ideas == []
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_variante_entscheidungen_und_wiederherstellung(tmp_path):
    memory = Memory(tmp_path / "projekt.db")
    project = memory.create_project("Synthese")
    original = memory.list_branches(project.id)[0]
    start = original.head_id
    alternative = memory.create_branch(project.id, "Andere Wendung", start)
    first_idea = idea()
    first_decision = decision()
    proposal = memory.propose(alternative.id, start,
                              Snapshot(ideas=[first_idea], decisions=[first_decision]), "Erster Entwurf")
    assert memory.get_revision(start).snapshot.ideas == []
    with pytest.raises(PermissionError):
        memory.approve(proposal.id, approved_by="Autorin", explicit_approval=False)
    assert next(b for b in memory.list_branches(project.id) if b.id == alternative.id).head_id == start
    approved = memory.approve(proposal.id, approved_by="Autorin", explicit_approval=True)
    assert memory.get_revision(next(b for b in memory.list_branches(project.id) if b.id == original.id).head_id).snapshot.ideas == []
    assert approved.snapshot.decisions == [first_decision]
    assert Memory(memory.path).get_revision(approved.id).snapshot.decisions == [first_decision]
    restore = memory.restore(alternative.id, start)
    assert restore.snapshot.decisions == [first_decision]
    restored = memory.approve(restore.id, approved_by="Autorin", explicit_approval=True)
    assert restored.snapshot.ideas == []
    assert restored.snapshot.decisions == [first_decision]
    assert memory.get_revision(approved.id).snapshot.ideas == [first_idea]


def test_veraltete_entwuerfe_und_ablehnung(tmp_path):
    memory = Memory(tmp_path / "projekt.db")
    project = memory.create_project("Spuren")
    branch = memory.list_branches(project.id)[0]
    a = memory.propose(branch.id, branch.head_id, Snapshot(ideas=[idea("A")]), "A")
    b = memory.propose(branch.id, branch.head_id, Snapshot(ideas=[idea("B")]), "B")
    memory.approve(a.id, approved_by="Autor", explicit_approval=True)
    with pytest.raises(ConflictError):
        memory.approve(b.id, approved_by="Autor", explicit_approval=True)
    with pytest.raises(ConflictError):
        memory.propose(branch.id, branch.head_id, Snapshot(), "alt")
    assert len(json.loads(memory.export_json(project.id))["revisions"]) == 2
    new_head = memory.list_branches(project.id)[0].head_id
    rejected = memory.propose(branch.id, new_head, Snapshot(), "Ablehnen")
    memory.reject(rejected.id)
    with pytest.raises(ValueError):
        memory.approve(rejected.id, approved_by="Autor", explicit_approval=True)
    assert memory.list_branches(project.id)[0].head_id == new_head


def test_rollback_bei_fehler_und_entscheidungsschutz(tmp_path, monkeypatch):
    memory = Memory(tmp_path / "projekt.db")
    project = memory.create_project("Echos")
    branch = memory.list_branches(project.id)[0]
    original = memory._insert_revision
    proposal = memory.propose(branch.id, branch.head_id, Snapshot(decisions=[decision()]), "Entscheidung")

    def failure(*args):
        original(*args)
        raise RuntimeError("Abbruch nach INSERT")

    monkeypatch.setattr(memory, "_insert_revision", failure)
    with pytest.raises(RuntimeError):
        memory.approve(proposal.id, approved_by="Autor", explicit_approval=True)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert len(json.loads(memory.export_json(project.id))["revisions"]) == 1
    monkeypatch.setattr(memory, "_insert_revision", original)
    approved = memory.approve(proposal.id, approved_by="Autor", explicit_approval=True)
    with pytest.raises(ValueError, match="Autorenentscheidungen"):
        memory.propose(branch.id, approved.id, Snapshot(), "Löschen")


def test_json_und_markdown_export(tmp_path):
    memory = Memory(tmp_path / "projekt.db")
    project = memory.create_project("Hörprobe")
    branch = memory.list_branches(project.id)[0]
    proposal = memory.propose(branch.id, branch.head_id, Snapshot(ideas=[idea()]), "Stoffidee")
    revision = memory.approve(proposal.id, approved_by="Autorin", explicit_approval=True)
    data = json.loads(memory.export_json(project.id))
    assert data["project"]["work_id"] == str(project.work_id)
    assert data["revisions"][-1]["content_hash"] == revision.content_hash
    assert data["revisions"][-1]["snapshot"]["ideas"][0]["title"] == "Geheime Tür"
    markdown = memory.export_markdown(project.id)
    assert "# Hörprobe" in markdown
    assert "Geheime Tür" in markdown
    assert "Variante: Original" in markdown
    assert json.loads(memory.export_file(project.id, tmp_path / "exports" / "projekt.json", format="json").read_text(encoding="utf-8")) == data
    assert memory.export_file(project.id, tmp_path / "exports" / "projekt.md", format="markdown").read_text(encoding="utf-8") == markdown
