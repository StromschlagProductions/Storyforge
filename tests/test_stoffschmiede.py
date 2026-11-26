import json
import sqlite3
from collections import Counter
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest

from storyforge import (ConflictError, Decision, FakeProvider, Idea, InvalidModelResponse,
                        Memory, ModelCancelled, ModelTimeout, NarrativeLibrary, Snapshot,
                        Stoffschmiede)


CARDS = Path(__file__).resolve().parents[1] / "library" / "cards"


def _response(revision_id, card_ids, *, count=3):
    return json.dumps({"base_revision_id": str(revision_id), "candidates": [
        {"title": f"Teststoff {i + 1}", "premise": f"Eine synthetische Prämisse {i + 1}.",
         "narrative_promise": "Eine neue Wahrnehmung der Testwelt.",
         "mechanism": f"Mechanismus {i + 1}",
         "mechanism_card_id": card_ids[i] if i < len(card_ids) else None,
         "central_mystery": None, "personal_conflict": "Eine Entscheidung unter Unsicherheit.",
         "development": "Der Konflikt verändert die Ausgangslage.",
         "audio_potential": "Ein Geräusch erhält eine neue Bedeutung.",
         "fictional_assumptions": ["Synthetische Weltannahme"],
         "research_questions": [], "weaknesses": ["Mögliche Wiederholung"],
         "used_card_ids": [card_ids[i]] if i < len(card_ids) else []}
        for i in range(count)]}, ensure_ascii=False)


def _setup(tmp_path):
    memory = Memory(tmp_path / "stoffe.sqlite3")
    project = memory.create_project("Synthetisches Werk")
    branch = memory.list_branches(project.id)[0]
    library = NarrativeLibrary.load(CARDS)
    return memory, project, branch, library


def test_alle_produktiven_karten_und_aufgabenwahl():
    library = NarrativeLibrary.load(CARDS)
    cards = library.filter()
    assert len(cards) == 59
    assert Counter(card.category for card in cards) == {"M": 16, "N": 16, "D": 17, "A": 10}
    assert all(card.source and card.version >= 1 for card in cards)
    assert all(all(library.get(other).id == other for other in card.related_ids) for card in cards)
    assert [card.id for card in library.select("stoffidee", keywords={"klang"}, limit=3).cards]
    assert [card.id for card in library.select("geheimnis", keywords={"hinweise"}, limit=3).cards]
    assert [card.id for card in library.select("dramaturgie", categories={"D"}, limit=3).cards]


def test_stoffschmiede_ohne_skript_persistiert_unverbindlich(tmp_path):
    memory, project, branch, library = _setup(tmp_path)
    selector = Stoffschmiede(memory, FakeProvider([]), library)
    selected = selector.select_cards("Ein Klang und ein Geheimnis", limit=3)
    ids = [card.id for card in selected.cards]
    assert len(ids) == 3 and len({card[0] for card in ids}) == 3
    provider = FakeProvider([_response(branch.head_id, ids)], model="fake-v02")
    result = Stoffschmiede(memory, provider, library).develop(
        project.id, branch.id, "Ein Klang und ein Geheimnis", count=3, card_limit=3)
    assert len(result.candidates) == 3
    assert len({item.mechanism for item in result.candidates}) == 3
    assert [item.mechanism_card_id for item in result.candidates] == ids
    assert result.reflection is None
    assert result.manifest["cards"] == [{"id": card.id, "version": card.version}
                                         for card in selected.cards]
    assert result.manifest["mechanism_assignments"] == ids
    assert provider.requests[0].format_schema is not None
    context = provider.requests[0].messages[0]["content"]
    assert [item["id"] for item in json.loads(context.split("Projektkontext:\n", 1)[1])["wissenskarten"]] == ids
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert memory.list_turns(project.id, branch.id) == []
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM proposals").fetchone()[0] == 0
    stored = Memory(memory.path).get_creative_run(result.id)
    assert stored["model"] == "fake-v02"
    assert stored["revision_id"] == str(branch.head_id)
    assert stored["manifest"] == result.manifest
    assert len(stored["candidates"]) == 3


def test_fallback_und_optionale_reflexion(tmp_path):
    memory, project, branch, library = _setup(tmp_path)
    selector = Stoffschmiede(memory, FakeProvider([]), library)
    selected = selector.select_cards("Ein völlig neues Testwort", limit=3)
    assert len(selected.cards) == 3
    assert all("Fallback" in reason for reason in selected.reasons)
    ids = [card.id for card in selected.cards]
    reflection = {"strengths": ["Klarer Kontrast"], "risks": ["Ähnliche Figuren"],
                  "questions": ["Was hört die Figur zuerst?"]}
    provider = FakeProvider([_response(branch.head_id, ids), json.dumps(reflection)])
    run = Stoffschmiede(memory, provider, library).develop(
        project.id, branch.id, "Ein völlig neues Testwort", count=3, card_limit=3, reflect=True)
    assert len(provider.requests) == 2
    assert run.reflection.strengths == ["Klarer Kontrast"]
    assert memory.get_creative_run(run.id)["reflection"] == reflection
    assert memory.list_branches(project.id)[0].head_id == branch.head_id


@pytest.mark.parametrize("alter", [
    lambda payload: "kein JSON",
    lambda payload: json.dumps({**payload, "candidates": payload["candidates"][:2]}),
    lambda payload: json.dumps({**payload, "base_revision_id": str(uuid4())}),
    lambda payload: json.dumps({**payload, "candidates": [
        {**payload["candidates"][0], "used_card_ids": ["M99"]}, *payload["candidates"][1:]]}),
    lambda payload: json.dumps({**payload, "candidates": [
        payload["candidates"][0], {**payload["candidates"][1], "mechanism": "Mechanismus 1"},
        payload["candidates"][2]]}),
])
def test_ungueltige_antworten_werden_nicht_gespeichert(tmp_path, alter):
    memory, project, branch, library = _setup(tmp_path)
    ids = [card.id for card in Stoffschmiede(memory, FakeProvider([]), library).select_cards("Klang", limit=3).cards]
    original = json.loads(_response(branch.head_id, ids))
    provider = FakeProvider([alter(original)])
    with pytest.raises((InvalidModelResponse, ConflictError)):
        Stoffschmiede(memory, provider, library).develop(project.id, branch.id, "Klang", count=3, card_limit=3)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0


def test_timeout_abbruch_und_ungueltige_reflexion(tmp_path):
    memory, project, branch, library = _setup(tmp_path)
    for error in (ModelTimeout("spät"), ModelCancelled("abgebrochen")):
        with pytest.raises(type(error)):
            Stoffschmiede(memory, FakeProvider([error]), library).develop(project.id, branch.id, "Klang")
    cancel = Event()
    cancel.set()
    with pytest.raises(ModelCancelled):
        Stoffschmiede(memory, FakeProvider(["unbenutzt"]), library).develop(
            project.id, branch.id, "Klang", cancel=cancel)
    ids = [card.id for card in Stoffschmiede(memory, FakeProvider([]), library).select_cards("Klang").cards]
    with pytest.raises(InvalidModelResponse):
        Stoffschmiede(memory, FakeProvider([_response(branch.head_id, ids), "keine Reflexion"]), library).develop(
            project.id, branch.id, "Klang", reflect=True)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0


def test_autorenentscheidung_und_projektisolation(tmp_path):
    memory, project, branch, library = _setup(tmp_path)
    other = memory.create_project("Fremdes Werk")
    other_head = memory.list_branches(other.id)[0].head_id
    alternative = memory.create_branch(project.id, "Andere Fassung", branch.head_id)
    decision = Decision(id=uuid4(), target="Ton", action="behalten", rationale="Wichtig", author="Autor")
    revision = memory.approve(memory.propose(branch.id, branch.head_id,
                                              Snapshot(decisions=[decision]), "Entscheidung").id,
                              approved_by="Autor", explicit_approval=True)
    secret = Idea(id=uuid4(), title="Anderer Stoff", premise="Nur alternative Fassung.")
    memory.approve(memory.propose(alternative.id, alternative.head_id,
                                  Snapshot(ideas=[secret]), "Alternative").id,
                   approved_by="Autor", explicit_approval=True)
    ids = [card.id for card in Stoffschmiede(memory, FakeProvider([]), library).select_cards("Klang", limit=3).cards]
    provider = FakeProvider([_response(revision.id, ids)])
    run = Stoffschmiede(memory, provider, library).develop(project.id, branch.id, "Klang", card_limit=3)
    context = json.dumps(provider.requests[0].messages, ensure_ascii=False)
    assert "Anderer Stoff" not in context and "Fremdes Werk" not in context
    assert "Ton" in context and str(decision.id) in context
    assert run.manifest["decision_ids"] == [str(decision.id)]
    main_head = next(item.head_id for item in memory.list_branches(project.id) if item.id == branch.id)
    assert memory.get_revision(main_head).snapshot.decisions == [decision]
    draft = Stoffschmiede(memory, FakeProvider([]), library).stage_candidate(run.id, run.candidates[0].id)
    assert draft.snapshot.decisions == [decision]
    assert next(item.head_id for item in memory.list_branches(project.id) if item.id == branch.id) == main_head
    assert memory.list_branches(other.id)[0].head_id == other_head


def test_ausgewaehlter_stoffkeim_erstellt_nur_entwurf_und_prueft_revision(tmp_path):
    memory, project, branch, library = _setup(tmp_path)
    forge = Stoffschmiede(memory, FakeProvider([]), library)
    ids = [card.id for card in forge.select_cards("Klang", limit=3).cards]
    forge = Stoffschmiede(memory, FakeProvider([_response(branch.head_id, ids)]), library)
    run = forge.develop(project.id, branch.id, "Klang", card_limit=3)
    proposal = forge.stage_candidate(run.id, run.candidates[0].id)
    assert proposal.snapshot.ideas[-1].title == run.candidates[0].title
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    with pytest.raises(PermissionError):
        memory.approve(proposal.id, approved_by="Autor", explicit_approval=False)
    memory.approve(memory.propose(branch.id, branch.head_id, Snapshot(), "Parallel").id,
                   approved_by="Autor", explicit_approval=True)
    with pytest.raises(ConflictError):
        forge.stage_candidate(run.id, run.candidates[1].id)
    with pytest.raises(ConflictError):
        memory.approve(proposal.id, approved_by="Autor", explicit_approval=True)
    with pytest.raises(KeyError):
        forge.stage_candidate(run.id, uuid4())


def test_migration_von_sf002_schema(tmp_path):
    path = tmp_path / "alt.sqlite3"
    memory = Memory(path)
    project = memory.create_project("Altes Projekt")
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE creative_runs")
        db.execute("PRAGMA user_version = 2")
    reopened = Memory(path)
    assert reopened.get_project(project.id) == project
    assert reopened.list_branches(project.id)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3


def test_leere_bibliothek_erfindet_keine_karten_ids(tmp_path):
    memory = Memory(tmp_path / "leer.sqlite3")
    project = memory.create_project("Synthetisches Werk")
    branch = memory.list_branches(project.id)[0]
    library = NarrativeLibrary([])
    provider = FakeProvider([_response(branch.head_id, [])])
    forge = Stoffschmiede(memory, provider, library)
    assert forge.select_cards("Ohne passende Karte", limit=3).cards == ()
    run = forge.develop(project.id, branch.id, "Ohne passende Karte", card_limit=3)
    assert run.manifest["cards"] == []
    assert all(seed.mechanism_card_id is None and seed.used_card_ids == [] for seed in run.candidates)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id


def test_prozessneustart_manifest_und_freier_prompt(tmp_path):
    import subprocess
    import sys

    memory, project, branch, library = _setup(tmp_path)
    ids = [card.id for card in Stoffschmiede(memory, FakeProvider([]), library).select_cards(
        "Klang", limit=3).cards]
    provider = FakeProvider([_response(branch.head_id, ids)])
    run = Stoffschmiede(memory, provider, library).develop(project.id, branch.id, "Klang", card_limit=3)
    assert len(provider.requests) == 1
    request = provider.requests[0]
    context = json.loads(request.messages[0]["content"].split("Projektkontext:\n", 1)[1])
    assert [(card["id"], card["version"]) for card in context["wissenskarten"]] == [
        (card["id"], card["version"]) for card in run.manifest["cards"]]
    assert context["revision"]["id"] == run.manifest["revision_id"]
    assert context["variante"]["id"] == run.manifest["branch_id"]
    assert "keine Handlungsschablonen" in request.messages[-1]["content"]
    assert "Weder Kartenfelder noch Prüffragen" in request.messages[-1]["content"]
    code = ("import json,sys; from uuid import UUID; from storyforge import Memory; "
            "m=Memory(sys.argv[1]); r=m.get_creative_run(UUID(sys.argv[2])); "
            "print(json.dumps({'manifest':r['manifest'],'candidates':r['candidates'],"
            "'head':str(m.list_branches(UUID(sys.argv[3]))[0].head_id)}))")
    output = subprocess.check_output([sys.executable, "-c", code, str(memory.path),
                                      str(run.id), str(project.id)], text=True)
    restored = json.loads(output)
    assert restored["manifest"] == run.manifest
    assert restored["candidates"] == [seed.model_dump(mode="json") for seed in run.candidates]
    assert restored["head"] == str(branch.head_id)


def test_falsche_mechanismuskarte_und_abbruch_nach_antwort(tmp_path):
    memory, project, branch, library = _setup(tmp_path)
    ids = [card.id for card in Stoffschmiede(memory, FakeProvider([]), library).select_cards(
        "Klang", limit=3).cards]
    payload = json.loads(_response(branch.head_id, ids))
    payload["candidates"][0]["mechanism_card_id"] = ids[1]
    with pytest.raises(InvalidModelResponse):
        Stoffschmiede(memory, FakeProvider([json.dumps(payload)]), library).develop(
            project.id, branch.id, "Klang", card_limit=3)

    cancel = Event()

    class CancellingProvider(FakeProvider):
        def generate(self, request, event=None):
            result = super().generate(request, event)
            cancel.set()
            return result

    with pytest.raises(ModelCancelled):
        Stoffschmiede(memory, CancellingProvider([_response(branch.head_id, ids)]), library).develop(
            project.id, branch.id, "Klang", card_limit=3, cancel=cancel)
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0


def test_windows_konsolenausgabe_zeigt_alle_stofffelder(tmp_path):
    import importlib.util

    memory, project, branch, library = _setup(tmp_path)
    ids = [card.id for card in Stoffschmiede(memory, FakeProvider([]), library).select_cards(
        "Klang", limit=3).cards]
    run = Stoffschmiede(memory, FakeProvider([_response(branch.head_id, ids)]), library).develop(
        project.id, branch.id, "Klang", card_limit=3)
    script = Path(__file__).resolve().parents[1] / "scripts" / "stoffschmiede_smoke.py"
    spec = importlib.util.spec_from_file_location("stoffschmiede_smoke", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = module.format_result(run)
    assert all(value in output for value in (
        run.candidates[0].title, run.candidates[0].premise,
        run.candidates[0].narrative_promise, run.candidates[0].personal_conflict,
        run.candidates[0].development, run.candidates[0].audio_potential,
        run.candidates[0].fictional_assumptions[0], run.candidates[0].weaknesses[0]))
    assert output.count("=== Stoffkeim") == 3
