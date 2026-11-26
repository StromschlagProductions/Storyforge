import json
import sqlite3
import subprocess
import sys
from threading import Event
from uuid import uuid4

import pytest

from storyforge import (ConflictError, ContextLimitError, Decision, Dialogue, FakeProvider,
                        Idea, InvalidModelResponse, Memory, ModelCancelled, ModelError,
                        ModelTimeout, Snapshot)


def _change(revision_id, ideas, *, description="Neuer Ansatz"):
    return json.dumps({"base_revision_id": str(revision_id), "description": description,
                       "ideas": [item.model_dump(mode="json") for item in ideas]})


def test_fake_dialog_und_gespraechspersistenz_ohne_kanonaenderung(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Signal")
    branch = memory.list_branches(project.id)[0]
    source = memory.get_revision(branch.head_id)
    idea = Idea(id=uuid4(), title="Funkspruch", premise="Ein Signal aus einem leeren Raum.")
    decision = Decision(id=uuid4(), target="Perspektive", action="behalten",
                        rationale="Erhöht Spannung", author="Autor")
    proposal = memory.propose(branch.id, source.id, Snapshot(ideas=[idea], decisions=[decision]), "Start")
    revision = memory.approve(proposal.id, approved_by="Autor", explicit_approval=True)
    provider = FakeProvider(["Eine mögliche Frage: Wer hört das Signal?", "Die Stille kann antworten."])
    dialog = Dialogue(memory, provider)
    first = dialog.ask(project.id, branch.id, "Welche Frage trägt den Stoff?")
    second = dialog.ask(project.id, branch.id, "Und akustisch?")
    assert first.proposal_id is None and second.proposal_id is None
    assert first.manifest["revision_id"] == str(revision.id)
    assert first.manifest["idea_ids"] == [str(idea.id)]
    assert first.manifest["decision_ids"] == [str(decision.id)]
    assert len(second.manifest["history_turn_ids"]) == 2
    assert [message["role"] for message in provider.requests[1].messages] == [
        "system", "user", "assistant", "user"]
    assert "Funkspruch" in provider.requests[0].messages[0]["content"]
    assert "Perspektive" in provider.requests[0].messages[0]["content"]
    assert memory.list_branches(project.id)[0].head_id == revision.id
    reopened = Memory(memory.path)
    turns = reopened.list_turns(project.id, branch.id)
    assert len(turns) == 4
    assert json.loads(turns[1]["manifest"])["decision_ids"] == [str(decision.id)]


def test_nur_aktives_projekt_und_variante_im_kontext(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    selected = memory.create_project("Ausgewähltes Projekt")
    other = memory.create_project("Fremdes Projekt")
    main = memory.list_branches(selected.id)[0]
    variant = memory.create_branch(selected.id, "Nicht gewählt", main.head_id)
    secret = Idea(id=uuid4(), title="Andere Variante", premise="Nur in der anderen Variante.")
    memory.approve(memory.propose(variant.id, variant.head_id, Snapshot(ideas=[secret]), "Abzweig").id,
                   approved_by="Autor", explicit_approval=True)
    provider = FakeProvider(["Gespräch möglich."])
    result = Dialogue(memory, provider).ask(selected.id, main.id, "Welche Stimmung passt?")
    context = json.dumps(provider.requests[0].messages, ensure_ascii=False)
    assert "Fremdes Projekt" not in context
    assert "Andere Variante" not in context
    assert str(other.id) not in context and str(variant.id) not in context
    assert result.manifest["branch_id"] == str(main.id)
    assert result.manifest["idea_ids"] == []
    assert next(item for item in memory.list_branches(selected.id) if item.id == variant.id).head_id != main.head_id


def test_strukturierter_entwurf_braucht_autorfreigabe_und_bleibt_bei_modellwechsel(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Klang")
    branch = memory.list_branches(project.id)[0]
    idea = Idea(id=uuid4(), title="Leere Bühne", premise="Ein Geräusch ohne Ursache.")
    provider = FakeProvider([_change(branch.head_id, [idea])], model="fake-a")
    result = Dialogue(memory, provider).ask(project.id, branch.id, "Entwirf eine Idee", structured=True)
    assert provider.requests[0].format_schema is not None
    assert result.proposal_id is not None
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert memory.get_proposal(result.proposal_id).snapshot.ideas == [idea]
    with pytest.raises(PermissionError):
        memory.approve(result.proposal_id, approved_by="Autor", explicit_approval=False)
    approved = memory.approve(result.proposal_id, approved_by="Autor", explicit_approval=True)
    assert approved.snapshot.ideas == [idea]
    with sqlite3.connect(memory.path) as db:
        schema_before = db.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
    other_provider = FakeProvider(["Eine alternative Deutung."], model="fake-b")
    answer = Dialogue(Memory(memory.path), other_provider).ask(project.id, branch.id, "Was nun?")
    assert answer.model == "fake-b" and answer.proposal_id is None
    assert memory.get_revision(memory.list_branches(project.id)[0].head_id).snapshot.ideas == [idea]
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall() == schema_before


@pytest.mark.parametrize("answer", ["kein JSON", "{}", '{"base_revision_id":"ungültig"}'])
def test_ungueltige_strukturantwort_ohne_aenderung(tmp_path, answer):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Funk")
    branch = memory.list_branches(project.id)[0]
    with pytest.raises(InvalidModelResponse):
        Dialogue(memory, FakeProvider([answer])).ask(project.id, branch.id, "Neue Idee", structured=True)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert memory.list_turns(project.id, branch.id) == []


def test_abbruch_timeout_und_providerfehler_ohne_aenderung(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Funk")
    branch = memory.list_branches(project.id)[0]
    cancel = Event()
    cancel.set()
    with pytest.raises(ModelCancelled):
        Dialogue(memory, FakeProvider(["Antwort"])).ask(project.id, branch.id, "Hallo", cancel=cancel)
    for error in (ModelTimeout("zu spät"), ModelError("offline")):
        with pytest.raises(type(error)):
            Dialogue(memory, FakeProvider([error])).ask(project.id, branch.id, "Hallo")
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert memory.list_turns(project.id, branch.id) == []


def test_veralteter_ki_vorschlag_und_geschuetzte_elemente(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Funk")
    branch = memory.list_branches(project.id)[0]
    protected = Idea(id=uuid4(), title="Signal", premise="Ein Ruf.", protected_elements=["Ruf"])
    approved = memory.approve(memory.propose(branch.id, branch.head_id,
                                              Snapshot(ideas=[protected]), "Start").id,
                              approved_by="Autor", explicit_approval=True)
    with pytest.raises(InvalidModelResponse):
        Dialogue(memory, FakeProvider([_change(approved.id, [])])).ask(
            project.id, branch.id, "Verändere den Stoff", structured=True)
    with pytest.raises(ConflictError):
        Dialogue(memory, FakeProvider([_change(branch.head_id, [protected])])).ask(
            project.id, branch.id, "Alter Entwurf", structured=True)
    current = _change(approved.id, [protected])
    first = Dialogue(memory, FakeProvider([current])).ask(project.id, branch.id, "Entwurf", structured=True)
    memory.approve(memory.propose(branch.id, approved.id, Snapshot(ideas=[protected]), "Parallel").id,
                   approved_by="Autor", explicit_approval=True)
    with pytest.raises(ConflictError):
        memory.approve(first.proposal_id, approved_by="Autor", explicit_approval=True)


def test_kontextgrenze_kuerzt_nur_gespraech_und_nie_entscheidungen(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Funk")
    branch = memory.list_branches(project.id)[0]
    decision = Decision(id=uuid4(), target="Klang", action="behalten",
                        rationale="Verbindlich", author="Autor")
    memory.approve(memory.propose(branch.id, branch.head_id,
                                  Snapshot(decisions=[decision]), "Regel").id,
                   approved_by="Autor", explicit_approval=True)
    provider = FakeProvider(["Antwort eins", "Antwort zwei"])
    dialog = Dialogue(memory, provider)
    dialog.ask(project.id, branch.id, "Erste Frage")
    system_length = len(provider.requests[0].messages[0]["content"])
    limited = Dialogue(memory, provider, max_context_chars=system_length + len("Zweite Frage"))
    second = limited.ask(project.id, branch.id, "Zweite Frage")
    assert second.manifest["history_turn_ids"] == []
    assert second.manifest["decision_ids"] == [str(decision.id)]
    with pytest.raises(ContextLimitError):
        Dialogue(memory, FakeProvider(["irrelevant"]), max_context_chars=10).ask(
            project.id, branch.id, "Dritte Frage")


def test_migration_von_sf001_schema(tmp_path):
    path = tmp_path / "legacy.db"
    memory = Memory(path)
    project = memory.create_project("Altes Projekt")
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE conversation_turns")
        db.execute("DROP TABLE creative_runs")
        db.execute("PRAGMA user_version = 1")
    reopened = Memory(path)
    assert reopened.get_project(project.id) == project
    assert reopened.list_turns(project.id, reopened.list_branches(project.id)[0].id) == []


def test_doppelte_ideen_ids_aus_modell_werden_abgelehnt(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Funk")
    branch = memory.list_branches(project.id)[0]
    duplicate = Idea(id=uuid4(), title="Echo", premise="Ein wiederkehrendes Geräusch.")
    response = _change(branch.head_id, [duplicate, duplicate])
    with pytest.raises(InvalidModelResponse):
        Dialogue(memory, FakeProvider([response])).ask(project.id, branch.id, "Ideen", structured=True)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert memory.list_turns(project.id, branch.id) == []


def test_manifest_entspricht_exakt_dem_gesendeten_projektkontext(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Klangprobe", universe_title="Synthetisches Universum")
    branch = memory.list_branches(project.id)[0]
    idea = Idea(id=uuid4(), title="Takt", premise="Ein unregelmäßiger Puls.")
    decision = Decision(id=uuid4(), target="Rhythmus", action="behalten",
                        rationale="Prägt den Stoff", author="Autor")
    revision = memory.approve(memory.propose(branch.id, branch.head_id,
                                              Snapshot(ideas=[idea], decisions=[decision]), "Start").id,
                              approved_by="Autor", explicit_approval=True)
    provider = FakeProvider(["Erste Antwort", "Zweite Antwort"])
    dialogue = Dialogue(memory, provider)
    dialogue.ask(project.id, branch.id, "Erste Frage")
    result = dialogue.ask(project.id, branch.id, "Zweite Frage")
    messages = provider.requests[1].messages
    core = json.loads(messages[0]["content"].split("Projektkontext:\n", 1)[1])
    manifest = result.manifest
    assert core["projekt"]["id"] == manifest["project_id"] == str(project.id)
    assert core["projekt"]["werk_id"] == manifest["work_id"]
    assert core["projekt"]["universum_id"] == manifest["universe_id"]
    assert core["variante"]["id"] == manifest["branch_id"] == str(branch.id)
    assert core["revision"] == {"id": manifest["revision_id"], "hash": manifest["revision_hash"]}
    assert core["revision"]["id"] == str(revision.id)
    assert [item["id"] for item in core["stoffideen"]] == manifest["idea_ids"]
    assert [item["id"] for item in core["autorenentscheidungen"]] == manifest["decision_ids"]
    turns = memory.list_turns(project.id, branch.id)
    assert manifest["history_turn_ids"] == [turn["id"] for turn in turns[:2]]
    assert [(message["role"], message["content"]) for message in messages[1:-1]] == [
        (turn["role"], turn["content"]) for turn in turns[:2]]
    assert messages[-1] == {"role": "user", "content": "Zweite Frage"}


def test_dialogverlauf_nach_vollstaendigem_prozessneustart(tmp_path):
    path = tmp_path / "Dialog äöü.sqlite3"
    first_process = """import json, sys
from storyforge import Dialogue, FakeProvider, Memory
m = Memory(sys.argv[1]); p = m.create_project('Synthetischer Dialog')
b = m.list_branches(p.id)[0]
Dialogue(m, FakeProvider(['Erste Antwort'])).ask(p.id, b.id, 'Erste Frage')
print(json.dumps({'project_id': str(p.id), 'branch_id': str(b.id)}))
"""
    result = subprocess.run([sys.executable, "-c", first_process, str(path)],
                            capture_output=True, text=True, check=True)
    ids = json.loads(result.stdout)
    second_process = """import json, sys
from uuid import UUID
from storyforge import Dialogue, FakeProvider, Memory
m = Memory(sys.argv[1]); p = UUID(sys.argv[2]); b = UUID(sys.argv[3])
fake = FakeProvider(['Zweite Antwort'])
r = Dialogue(m, fake).ask(p, b, 'Zweite Frage')
print(json.dumps({'history': r.manifest['history_turn_ids'],
                  'roles': [x['role'] for x in fake.requests[0].messages],
                  'turns': len(m.list_turns(p, b))}))
"""
    reopened = subprocess.run([sys.executable, "-c", second_process, str(path),
                               ids["project_id"], ids["branch_id"]],
                              capture_output=True, text=True, check=True)
    data = json.loads(reopened.stdout)
    assert len(data["history"]) == 2
    assert data["roles"] == ["system", "user", "assistant", "user"]
    assert data["turns"] == 4


def test_abbruch_nach_modellantwort_speichert_nichts(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Test")
    branch = memory.list_branches(project.id)[0]
    cancel = Event()

    class CancelOnReturn(FakeProvider):
        def generate(self, request, token=None):
            answer = super().generate(request, token)
            cancel.set()
            return answer

    for structured, answer in ((False, "Antwort"), (True, _change(branch.head_id, []))):
        cancel.clear()
        with pytest.raises(ModelCancelled):
            Dialogue(memory, CancelOnReturn([answer])).ask(
                project.id, branch.id, "Aufgabe", structured=structured, cancel=cancel)
    assert memory.list_turns(project.id, branch.id) == []
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM proposals").fetchone()[0] == 0


def test_konkurrenz_waehrend_modellaufruf_und_fremde_variante(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Test")
    other = memory.create_project("Anderes Projekt")
    branch = memory.list_branches(project.id)[0]
    foreign_branch = memory.list_branches(other.id)[0]
    provider = FakeProvider(["Darf nicht aufgerufen werden"])
    with pytest.raises(KeyError):
        Dialogue(memory, provider).ask(project.id, foreign_branch.id, "Frage")
    assert provider.requests == []

    class ChangeDuringCall(FakeProvider):
        def generate(self, request, token=None):
            answer = super().generate(request, token)
            memory.approve(memory.propose(branch.id, branch.head_id, Snapshot(), "Parallel").id,
                           approved_by="Autor", explicit_approval=True)
            return answer

    with pytest.raises(ConflictError):
        Dialogue(memory, ChangeDuringCall([_change(branch.head_id, [])])).ask(
            project.id, branch.id, "Entwurf", structured=True)
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM proposals WHERE status='offen'").fetchone()[0] == 0


def test_unterstuetzung_strukturierter_antworten_wird_vorher_geprueft(tmp_path):
    memory = Memory(tmp_path / "dialog.db")
    project = memory.create_project("Test")
    branch = memory.list_branches(project.id)[0]
    provider = FakeProvider(["Antwort"], capabilities=("text",))
    with pytest.raises(ValueError, match="strukturierten"):
        Dialogue(memory, provider).ask(project.id, branch.id, "Entwurf", structured=True)
    assert provider.requests == []
    assert memory.list_turns(project.id, branch.id) == []
