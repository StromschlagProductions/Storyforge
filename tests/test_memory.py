import json
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
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


def test_vollstaendiger_prozessneustart(tmp_path):
    path = tmp_path / "Neustart äöü.sqlite3"
    create = """import json, sys
from uuid import uuid4
from storyforge import Memory, Snapshot, Idea, Decision
m = Memory(sys.argv[1])
p = m.create_project('Hörspiel ohne Skript')
b = m.list_branches(p.id)[0]
s = Snapshot(ideas=[Idea(id=uuid4(), title='Klangspur', premise='Ein fernes Signal.')],
             decisions=[Decision(id=uuid4(), target='Stimme', action='behalten',
                                 rationale='Wichtig', author='Autor')])
r = m.approve(m.propose(b.id, b.head_id, s, 'Entwurf').id,
              approved_by='Autor', explicit_approval=True)
print(json.dumps({'project': str(p.id), 'revision': str(r.id)}))
"""
    result = subprocess.run([sys.executable, "-c", create, str(path)],
                            check=True, capture_output=True, text=True)
    ids = json.loads(result.stdout)
    read = """import json, sys
from uuid import UUID
from storyforge import Memory
m = Memory(sys.argv[1])
p = m.get_project(UUID(sys.argv[2]))
r = m.get_revision(UUID(sys.argv[3]))
print(json.dumps({'title': p.title, 'idea': r.snapshot.ideas[0].title,
                  'decision': r.snapshot.decisions[0].action}))
"""
    reopened = subprocess.run([sys.executable, "-c", read, str(path),
                               ids["project"], ids["revision"]],
                              check=True, capture_output=True, text=True)
    assert json.loads(reopened.stdout) == {
        "title": "Hörspiel ohne Skript", "idea": "Klangspur", "decision": "behalten"}


def test_ungueltige_eingaben_veraendern_keinen_stand(tmp_path):
    memory = Memory(tmp_path / "projekt.db")
    with pytest.raises(ValueError):
        memory.create_project("   ")
    with pytest.raises(ValueError):
        memory.create_project("Projekt", work_title="  ")
    with pytest.raises(ValueError):
        memory.create_project("Projekt", universe_title="  ")
    with pytest.raises(KeyError):
        memory.create_project("Projekt", universe_id=uuid4())
    project = memory.create_project("Projekt")
    branch = memory.list_branches(project.id)[0]
    with pytest.raises(ValidationError):
        Snapshot.model_validate({"ideas": [{"id": str(uuid4()), "title": "X"}]})
    duplicate = idea()
    with pytest.raises(ValueError, match="eindeutig"):
        memory.propose(branch.id, branch.head_id, Snapshot(ideas=[duplicate, duplicate]), "doppelt")
    with pytest.raises(ValueError):
        memory.create_branch(project.id, "   ", branch.head_id)
    with pytest.raises(PermissionError):
        memory.approve(uuid4(), approved_by=" ", explicit_approval=True)
    assert memory.list_branches(project.id) == [branch]
    assert len(json.loads(memory.export_json(project.id))["revisions"]) == 1


def test_konkurrierende_instanz_und_exportkonsistenz(tmp_path):
    path = tmp_path / "projekt.db"
    first = Memory(path)
    project = first.create_project("Echo")
    original = first.list_branches(project.id)[0]
    variant = first.create_branch(project.id, "Variante", original.head_id)
    second = Memory(path)
    stale = first.propose(original.id, original.head_id, Snapshot(ideas=[idea("alt")]), "alt")
    current = second.propose(original.id, original.head_id, Snapshot(ideas=[idea("neu")]), "neu")
    second.approve(current.id, approved_by="Autor", explicit_approval=True)
    with pytest.raises(ConflictError):
        first.approve(stale.id, approved_by="Autor", explicit_approval=True)
    data = json.loads(first.export_json(project.id))
    revisions = {revision["id"]: revision for revision in data["revisions"]}
    assert all(branch["head_id"] in revisions for branch in data["branches"])
    assert next(branch for branch in data["branches"] if branch["id"] == str(variant.id))["head_id"] == str(original.head_id)
    markdown = first.export_markdown(project.id)
    assert "neu" in markdown
    assert "alt" not in markdown
    assert len(revisions) == 2


def test_export_ueberschreibt_datei_und_prueft_format(tmp_path):
    memory = Memory(tmp_path / "projekt.db")
    project = memory.create_project("Öffentliches Testprojekt")
    path = tmp_path / "Ausgabe ü" / "projekt.md"
    path.parent.mkdir()
    path.write_text("alt", encoding="utf-8")
    memory.export_file(project.id, path, format="markdown")
    assert path.read_text(encoding="utf-8") == memory.export_markdown(project.id)
    with pytest.raises(ValueError):
        memory.export_file(project.id, path, format="xml")
    assert list(path.parent.iterdir()) == [path]
