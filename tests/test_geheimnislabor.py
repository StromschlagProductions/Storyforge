import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest

from storyforge import (Arbeitsweise, Beobachtung, ConflictError, FakeProvider, Geheimnislabor,
                        Idea, InvalidModelResponse, Memory, ModelCancelled, ModelTimeout,
                        NarrativeLibrary, Snapshot)

CARDS = Path(__file__).resolve().parents[1] / "library" / "cards"


def setup(tmp_path):
    memory = Memory(tmp_path / "mystery.sqlite3")
    project = memory.create_project("Synthetisches Rätselwerk")
    branch = memory.list_branches(project.id)[0]
    library = NarrativeLibrary.load(CARDS)
    return memory, project, branch, library


def answer(observations=None, *, count=2, protected=()):
    observations = observations or [{"id": str(uuid4()), "beschreibung": "Ein Glockenton erklingt nachts."}]
    hypotheses = [{"id": str(uuid4()), "bezeichnung": f"Erklärung {i}",
                   "verborgener_mechanismus": f"Mechanismus {i}",
                   "notwendige_annahmen": [], "widersprueche": [],
                   "offene_fragen": ["Woher stammt der Ton?"],
                   "hinweise": ["Ein wiederkehrender Klang"],
                   "falsche_faehrten": ["Eine wahre, falsch gedeutete Spur"],
                   "vorbereitung": "Der Ton wird früh gehört.",
                   "enthuellung": "Der Ton bekommt eine neue Bedeutung.",
                   "emotionale_folgen": ["Die Figur zweifelt."],
                   "hoerspielpotenzial": "Klangperspektive", "recherchebedarf": [],
                   "verwendete_karten_ids": []} for i in range(count)]
    return {"beobachtungen": observations,
            "interpretationen": [{"beobachtung_id": observations[0]["id"],
                                   "deutung": "Die Figur vermutet ein Signal."}],
            "hypothesen": hypotheses,
            "matrix": [{"beobachtung_id": o["id"], "hypothese_id": h["id"],
                        "zustand": "ungeklärt" if i else "widerspricht",
                        "begruendung": "Es fehlen überprüfbare Angaben."}
                       for o in observations for i, h in enumerate(hypotheses)],
            "bewusst_mehrdeutig": True,
            "schutzpruefungen": [{"element": element, "status": "bewahrt",
                                  "begruendung": "Das Element bleibt genannt."} for element in protected]}


@pytest.mark.parametrize("mode", list(Arbeitsweise))
def test_alle_arbeitsweisen_ohne_skript_und_ohne_kanonwechsel(tmp_path, mode):
    memory, project, branch, library = setup(tmp_path)
    payload = answer(count=1 if mode == Arbeitsweise.PRUEFUNG else 2)
    provider = FakeProvider([json.dumps(payload, ensure_ascii=False)])
    lab = Geheimnislabor(memory, provider, library)
    truth = "Ein synthetisches Schallsignal." if mode == Arbeitsweise.VORWAERTS else None
    result = lab.develop(project.id, branch.id, "Ein rätselhafter Glockenton", mode=mode,
                         given_truth=truth)
    assert result.entwurf.bewusst_mehrdeutig
    assert len(result.entwurf.matrix) == len(result.entwurf.beobachtungen) * len(result.entwurf.hypothesen)
    assert all(item.zustand in ("widerspricht", "ungeklärt") for item in result.entwurf.matrix)
    assert len(provider.requests) == 1
    context = json.loads(provider.requests[0].messages[0]["content"].split("Projektkontext:\n", 1)[1])
    assert [(card["id"], card["version"]) for card in context["wissenskarten"]] == [
        (card["id"], card["version"]) for card in result.manifest["cards"]]
    assert result.manifest["mode"] == mode.value
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert memory.list_turns(project.id, branch.id) == []
    assert lab.get_result(result.id) == result


def test_prozessneustart_isolation_und_schutzpruefung(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    other = memory.create_project("Fremdes synthetisches Werk")
    alternative = memory.create_branch(project.id, "Andere Variante", branch.head_id)
    idea = Idea(id=uuid4(), title="Testidee", premise="Testprämisse",
                protected_elements=["Der Glockenton bleibt hörbar"])
    memory.approve(memory.propose(branch.id, branch.head_id, Snapshot(ideas=[idea]), "Schutz").id,
                   approved_by="Autor", explicit_approval=True)
    head = next(item.head_id for item in memory.list_branches(project.id) if item.id == branch.id)
    observation = Beobachtung(id=uuid4(), beschreibung="Ein Ton erklingt zweimal.")
    payload = answer([observation.model_dump(mode="json")], protected=idea.protected_elements)
    payload["schutzpruefungen"][0]["status"] = "verletzt"
    provider = FakeProvider([json.dumps(payload, ensure_ascii=False)])
    lab = Geheimnislabor(memory, provider, library)
    result = lab.develop(project.id, branch.id, "Andere Erklärung", mode=Arbeitsweise.ALTERNATIVEN,
                         observations=(observation,))
    assert result.entwurf.schutzpruefungen[0].status == "verletzt"
    assert result.manifest["protected_elements"] == idea.protected_elements
    assert "Fremdes synthetisches Werk" not in str(provider.requests[0].messages)
    assert "Andere Variante" not in str(provider.requests[0].messages)
    assert next(item.head_id for item in memory.list_branches(project.id) if item.id == branch.id) == head
    assert memory.list_branches(other.id)[0].project_id == other.id
    assert alternative.id != result.branch_id
    code = ("import json,sys; from uuid import UUID; from storyforge import Memory; "
            "r=Memory(sys.argv[1]).get_creative_run(UUID(sys.argv[2])); "
            "print(json.dumps({'manifest':r['manifest'],'draft':r['candidates'][0]}))")
    restored = json.loads(subprocess.check_output([sys.executable, "-c", code,
                         str(memory.path), str(result.id)], text=True))
    assert restored["manifest"] == result.manifest
    assert restored["draft"] == result.entwurf.model_dump(mode="json")


@pytest.mark.parametrize("change", [
    lambda p: p["matrix"].clear(),
    lambda p: p["matrix"].append({**p["matrix"][0], "beobachtung_id": str(uuid4())}),
    lambda p: p["interpretationen"][0].update(beobachtung_id=str(uuid4())),
    lambda p: p["hypothesen"][0].update(verwendete_karten_ids=["M99"]),
    lambda p: p["hypothesen"].append(p["hypothesen"][0]),
])
def test_ungueltige_referenzen_und_karten_werden_abgelehnt(tmp_path, change):
    memory, project, branch, library = setup(tmp_path)
    payload = answer()
    change(payload)
    with pytest.raises(InvalidModelResponse):
        Geheimnislabor(memory, FakeProvider([json.dumps(payload)]), library).develop(
            project.id, branch.id, "Rätsel", mode=Arbeitsweise.RUECKWAERTS)
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0


def test_autorbeobachtung_schutz_und_fehler(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    observation = Beobachtung(id=uuid4(), beschreibung="Ein Testgeräusch.")
    with pytest.raises(ValueError):
        Geheimnislabor(memory, FakeProvider([]), library).develop(
            project.id, branch.id, "Rätsel", mode=Arbeitsweise.VORWAERTS)
    with pytest.raises(KeyError):
        Geheimnislabor(memory, FakeProvider([]), library).select_cards("Rätsel", card_ids=("M99",))
    with pytest.raises(InvalidModelResponse):
        Geheimnislabor(memory, FakeProvider([json.dumps(answer())]), library).develop(
            project.id, branch.id, "Rätsel", mode=Arbeitsweise.RUECKWAERTS,
            observations=(observation,))
    for error in (ModelTimeout("spät"), ModelCancelled("Abbruch")):
        with pytest.raises(type(error)):
            Geheimnislabor(memory, FakeProvider([error]), library).develop(
                project.id, branch.id, "Rätsel", mode=Arbeitsweise.RUECKWAERTS)
    cancel = Event()
    cancel.set()
    with pytest.raises(ModelCancelled):
        Geheimnislabor(memory, FakeProvider([json.dumps(answer())]), library).develop(
            project.id, branch.id, "Rätsel", mode=Arbeitsweise.RUECKWAERTS, cancel=cancel)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id


def test_kartenauswahl_fallback_und_reflexion(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    lab = Geheimnislabor(memory, FakeProvider([]), library)
    choice = lab.select_cards("unbekannteswort", limit=4, card_ids=("M02",))
    assert len(choice.cards) == 4 and choice.cards[0].id == "M02"
    assert any("Fallback" in reason for reason in choice.reasons)
    reflection = {"strengths": ["Klarer Konflikt"], "risks": ["Offene Kausalität"],
                  "questions": ["Wer hört zuerst?"]}
    provider = FakeProvider([json.dumps(answer()), json.dumps(reflection)])
    result = Geheimnislabor(memory, provider, library).develop(
        project.id, branch.id, "unbekannteswort", mode=Arbeitsweise.RUECKWAERTS,
        card_ids=("M02",), reflect=True)
    assert len(provider.requests) == 2
    assert result.reflexion.strengths == reflection["strengths"]
    assert result.manifest["cards"][0]["id"] == "M02"


def test_fehlende_schutzpruefung_und_ungueltige_reflexion(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    idea = Idea(id=uuid4(), title="Geschützter Teststoff", premise="Eine synthetische Prämisse",
                protected_elements=["Der Ton bleibt hörbar"])
    revision = memory.approve(memory.propose(branch.id, branch.head_id,
                                              Snapshot(ideas=[idea]), "Schutz").id,
                              approved_by="Autor", explicit_approval=True)
    payload = answer()
    with pytest.raises(InvalidModelResponse):
        Geheimnislabor(memory, FakeProvider([json.dumps(payload)]), library).develop(
            project.id, branch.id, "Alternative", mode=Arbeitsweise.ALTERNATIVEN)
    payload["schutzpruefungen"] = [{"element": "Der Ton bleibt hörbar", "status": "ungeklärt",
                                    "begruendung": "Die Wirkung ist noch offen."}]
    with pytest.raises(InvalidModelResponse):
        Geheimnislabor(memory, FakeProvider([json.dumps(payload), "keine JSON-Reflexion"]), library).develop(
            project.id, branch.id, "Alternative", mode=Arbeitsweise.ALTERNATIVEN, reflect=True)
    assert memory.list_branches(project.id)[0].head_id == revision.id
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0


def test_revisionswechsel_waehrend_modellantwort_und_abbruch_danach(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    payload = json.dumps(answer())

    class ChangingProvider(FakeProvider):
        def generate(self, request, cancel=None):
            response = super().generate(request, cancel)
            memory.approve(memory.propose(branch.id, branch.head_id,
                                          Snapshot(), "Parallel").id,
                           approved_by="Autor", explicit_approval=True)
            return response

    with pytest.raises(ConflictError):
        Geheimnislabor(memory, ChangingProvider([payload]), library).develop(
            project.id, branch.id, "Rätsel", mode=Arbeitsweise.RUECKWAERTS)
    cancel = Event()

    class CancellingProvider(FakeProvider):
        def generate(self, request, event=None):
            response = super().generate(request, event)
            cancel.set()
            return response

    with pytest.raises(ModelCancelled):
        Geheimnislabor(memory, CancellingProvider([payload]), library).develop(
            project.id, branch.id, "Rätsel", mode=Arbeitsweise.RUECKWAERTS, cancel=cancel)
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0
