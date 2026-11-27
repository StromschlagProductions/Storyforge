import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest

from storyforge import (Analysebereich, Autorenredaktion, ConflictError, FakeProvider, Idea,
                        InvalidModelResponse, Memory, ModelCancelled, ModelTimeout,
                        NarrativeLibrary, Operation, Quelle, Snapshot)

CARDS = Path(__file__).resolve().parents[1] / "library" / "cards"


def setup(tmp_path):
    memory = Memory(tmp_path / "redaktion.sqlite3")
    project = memory.create_project("Synthetisches Testwerk")
    branch = memory.list_branches(project.id)[0]
    library = NarrativeLibrary.load(CARDS)
    return memory, project, branch, library


def mutation(operation, protected=()):
    return json.dumps({"alternativen": [{"bezeichnung": "Variante A", "kurzbeschreibung": "Ein Ton ändert seine Quelle.",
        "operation": operation.value, "veraenderte_elemente": ["Quelle des Tons"],
        "bewahrte_elemente": list(protected), "neue_moeglichkeiten": ["Eine andere Deutung"],
        "kausale_konsequenzen": ["Ursache noch ungeklärt"],
        "dramaturgische_konsequenzen": ["Spätere Enthüllung"],
        "figuren_und_geheimnisse": ["Die Figur zweifelt"],
        "hoerspielpotenzial": ["Räumlicher Klang"], "risiken": ["Verwirrung"],
        "ungeklaerte_auswirkungen": ["Zeitfolge ungeklärt"],
        "schutzpruefungen": [{"element": e, "status": "bewahrt", "begruendung": "Im Entwurf genannt"}
                               for e in protected], "verwendete_karten_ids": []}]}, ensure_ascii=False)


def critique(bereich=Analysebereich.KAUSALITAET):
    return json.dumps({"befunde": [{"bereich": bereich.value, "art": "interpretation",
        "problem": "Die Ursache ist offen", "materialbezug": "Der synthetische Ton",
        "begruendung": "Ein Übergang fehlt", "bedeutung": "Kann irritieren",
        "verbesserung": "Eine Spur ergänzen", "nachteile": "Weniger Rätsel",
        "unsicherheit": "Eine bewusste Lücke ist möglich"}],
        "staerken": ["Klangidee"], "beibehalten": ["Offener Beginn"],
        "offene_fragen": ["Wer hört zuerst?"], "verwendete_karten_ids": []}, ensure_ascii=False)


@pytest.mark.parametrize("operation", list(Operation))
def test_alle_operationen_freie_quelle_und_kartenkontext(tmp_path, operation):
    memory, project, branch, library = setup(tmp_path)
    provider = FakeProvider([mutation(operation)])
    editor = Autorenredaktion(memory, provider, library)
    result = editor.mutate(project.id, branch.id, "Mutationsauftrag", Quelle(art="frei", beschreibung="Ein Ton."),
                           operation=operation, card_ids=("M02",))
    assert len(provider.requests) == 1
    assert result.result.alternativen[0].operation == operation
    context = json.loads(provider.requests[0].messages[0]["content"].split("Projektkontext:\n", 1)[1])
    assert [(c["id"], c["version"]) for c in context["wissenskarten"]] == [
        (c["id"], c["version"]) for c in result.manifest["cards"]]
    assert result.manifest["cards"][0]["id"] == "M02"
    assert editor.get_result(result.id) == result
    assert memory.list_branches(project.id)[0].head_id == branch.head_id


def test_kritikbereiche_staerken_und_leere_befunde(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    editor = Autorenredaktion(memory, FakeProvider([critique()]), library)
    result = editor.critique(project.id, branch.id, "Prüfe Logik", Quelle(art="frei", beschreibung="Ein Ton."),
                            bereiche=(Analysebereich.KAUSALITAET,))
    assert result.result.befunde[0].verbesserung == "Eine Spur ergänzen"
    assert result.result.staerken and result.result.beibehalten
    empty = json.dumps({"befunde": [], "staerken": ["Synthetische Stärke"],
                        "beibehalten": ["Ton"], "offene_fragen": [], "verwendete_karten_ids": []})
    result2 = Autorenredaktion(memory, FakeProvider([empty]), library).critique(
        project.id, branch.id, "Freie Kritik", Quelle(art="frei", beschreibung="Ein Ton."))
    assert result2.result.befunde == []
    with pytest.raises(ValueError):
        editor.critique(project.id, branch.id, "Kritik", Quelle(art="frei", beschreibung="X"), bereiche=())


def test_geschuetzte_idee_entscheidungen_und_prozessneustart(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    idea = Idea(id=uuid4(), title="Ton", premise="Ein Ton", protected_elements=["Der Ton bleibt hörbar"])
    revision = memory.approve(memory.propose(branch.id, branch.head_id, Snapshot(ideas=[idea]), "Idee").id,
                              approved_by="Autor", explicit_approval=True)
    editor = Autorenredaktion(memory, FakeProvider([mutation(Operation.INVERSION, (*idea.protected_elements, "Die Figur bleibt"))]), library)
    result = editor.mutate(project.id, branch.id, "Inversion", Quelle(art="idee", id=idea.id),
                           operation=Operation.INVERSION, erhalten=("Die Figur bleibt",))
    assert len(result.result.alternativen[0].schutzpruefungen) == 2
    assert result.manifest["protected_elements"] == ["Der Ton bleibt hörbar", "Die Figur bleibt"] or set(result.manifest["protected_elements"]) == {"Der Ton bleibt hörbar", "Die Figur bleibt"}
    assert memory.list_branches(project.id)[0].head_id == revision.id
    code = ("import json,sys; from uuid import UUID; from storyforge import Memory; "
            "r=Memory(sys.argv[1]).get_creative_run(UUID(sys.argv[2])); "
            "print(json.dumps({'manifest':r['manifest'],'result':r['candidates'][0]}))")
    restored = json.loads(subprocess.check_output([sys.executable, "-c", code,
                         str(memory.path), str(result.id)], text=True))
    assert restored["manifest"] == result.manifest
    assert restored["result"] == result.result.model_dump(mode="json")


def test_gespeicherter_run_isolation_und_revision(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    other = memory.create_project("Fremdes Werk")
    other_branch = memory.list_branches(other.id)[0]
    alternative = memory.create_branch(project.id, "Alternative", branch.head_id)
    origin = Autorenredaktion(memory, FakeProvider([critique()]), library).critique(
        project.id, branch.id, "Analyse", Quelle(art="frei", beschreibung="Synthetischer Ton"))
    source = Quelle(art="creative_run", id=origin.id)
    result = Autorenredaktion(memory, FakeProvider([mutation(Operation.REDUKTION)]), library).mutate(
        project.id, branch.id, "Reduziere", source, operation=Operation.REDUKTION)
    assert result.manifest["source"]["id"] == str(origin.id)
    with pytest.raises(KeyError):
        Autorenredaktion(memory, FakeProvider([]), library).mutate(
            other.id, other_branch.id, "Reduziere", source, operation=Operation.REDUKTION)
    with pytest.raises(KeyError):
        Autorenredaktion(memory, FakeProvider([]), library).mutate(
            project.id, alternative.id, "Reduziere", source, operation=Operation.REDUKTION)
    memory.approve(memory.propose(branch.id, branch.head_id, Snapshot(), "Parallel").id,
                   approved_by="Autor", explicit_approval=True)
    with pytest.raises(ConflictError):
        Autorenredaktion(memory, FakeProvider([]), library).mutate(
            project.id, branch.id, "Reduziere", source, operation=Operation.REDUKTION)


def test_fehler_verletzte_schutzpruefung_abbruch(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    source = Quelle(art="frei", beschreibung="Synthetischer Ton")
    for bad in ("kein JSON", mutation(Operation.INVERSION),
                json.dumps({**json.loads(mutation(Operation.INVERSION, ("Ton bleibt",))),
                            "alternativen": [{**json.loads(mutation(Operation.INVERSION, ("Ton bleibt",)))["alternativen"][0],
                                              "verwendete_karten_ids": ["M99"]}]})):
        with pytest.raises(InvalidModelResponse):
            Autorenredaktion(memory, FakeProvider([bad]), library).mutate(
                project.id, branch.id, "Mutieren", source, operation=Operation.INVERSION,
                erhalten=("Ton bleibt",))
    for error in (ModelTimeout("spät"), ModelCancelled("Abbruch")):
        with pytest.raises(type(error)):
            Autorenredaktion(memory, FakeProvider([error]), library).critique(
                project.id, branch.id, "Kritik", source)
    cancel = Event()
    cancel.set()
    with pytest.raises(ModelCancelled):
        Autorenredaktion(memory, FakeProvider([critique()]), library).critique(
            project.id, branch.id, "Kritik", source, cancel=cancel)
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0
    assert memory.list_branches(project.id)[0].head_id == branch.head_id


def test_nicht_angeforderter_kritikbereich_und_schutzkonflikt(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    source = Quelle(art="frei", beschreibung="Ton")
    with pytest.raises(InvalidModelResponse):
        Autorenredaktion(memory, FakeProvider([critique(Analysebereich.AKUSTIK)]), library).critique(
            project.id, branch.id, "Logik", source, bereiche=(Analysebereich.KAUSALITAET,))
    with pytest.raises(ValueError):
        Autorenredaktion(memory, FakeProvider([]), library).mutate(
            project.id, branch.id, "Wandel", source, operation=Operation.FREI,
            erhalten=("Ton",), gezielt_aendern=("Ton",))


def test_kombinierte_kritik_und_promptfreiheit(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    payload = json.loads(critique())
    payload["befunde"].append({**payload["befunde"][0], "bereich": Analysebereich.AKUSTIK.value,
                              "art": "widerspruch", "problem": "Quelle und Hörperspektive kollidieren"})
    provider = FakeProvider([json.dumps(payload, ensure_ascii=False)])
    result = Autorenredaktion(memory, provider, library).critique(
        project.id, branch.id, "Prüfe Logik und Klang", Quelle(art="frei", beschreibung="Ein Testton."),
        bereiche=(Analysebereich.KAUSALITAET, Analysebereich.AKUSTIK), card_limit=2)
    assert {b.bereich for b in result.result.befunde} == {Analysebereich.KAUSALITAET, Analysebereich.AKUSTIK}
    assert {b.art for b in result.result.befunde} == {"interpretation", "widerspruch"}
    assert all(b.begruendung and b.materialbezug and b.verbesserung and b.nachteile and b.unsicherheit
               for b in result.result.befunde)
    assert len(provider.requests) == 1
    prompt = provider.requests[0].messages[-1]["content"]
    assert "Erzwinge keine Probleme" in prompt and "keine Pflichtregeln" in prompt
    assert "keine Kreativitätsnote" in prompt
    context = json.loads(provider.requests[0].messages[0]["content"].split("Projektkontext:\n", 1)[1])
    assert [(c["id"], c["version"]) for c in context["wissenskarten"]] == [
        (c["id"], c["version"]) for c in result.manifest["cards"]]
    assert len(result.manifest["cards"]) <= 2


def test_schutzverletzung_bleibt_sichtbar_und_widerspruch_wird_abgelehnt(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    source = Quelle(art="frei", beschreibung="Ein synthetischer Klang.")
    payload = json.loads(mutation(Operation.INVERSION, ("Ton bleibt", "Figur bleibt")))
    payload["alternativen"][0]["schutzpruefungen"][0]["status"] = "verletzt"
    payload["alternativen"][0]["bewahrte_elemente"].remove("Ton bleibt")
    payload["alternativen"][0]["veraenderte_elemente"].append("Ton bleibt")
    editor = Autorenredaktion(memory, FakeProvider([json.dumps(payload)]), library)
    result = editor.mutate(project.id, branch.id, "Inversion", source, operation=Operation.INVERSION,
                           erhalten=("Ton bleibt", "Figur bleibt"))
    assert result.result.alternativen[0].schutzpruefungen[0].status == "verletzt"
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    payload["alternativen"][0]["bewahrte_elemente"].append("Ton bleibt")
    with pytest.raises(InvalidModelResponse):
        Autorenredaktion(memory, FakeProvider([json.dumps(payload)]), library).mutate(
            project.id, branch.id, "Inversion", source, operation=Operation.INVERSION,
            erhalten=("Ton bleibt", "Figur bleibt"))


def test_abbruch_nach_antwort_und_revisionswechsel(tmp_path):
    memory, project, branch, library = setup(tmp_path)
    source = Quelle(art="frei", beschreibung="Ein Testton.")
    cancel = Event()

    class CancellingProvider(FakeProvider):
        def generate(self, request, event=None):
            response = super().generate(request, event)
            cancel.set()
            return response

    with pytest.raises(ModelCancelled):
        Autorenredaktion(memory, CancellingProvider([critique()]), library).critique(
            project.id, branch.id, "Kritik", source, cancel=cancel)

    class ChangingProvider(FakeProvider):
        def generate(self, request, event=None):
            response = super().generate(request, event)
            memory.approve(memory.propose(branch.id, branch.head_id, Snapshot(), "Parallel").id,
                           approved_by="Autor", explicit_approval=True)
            return response

    with pytest.raises(ConflictError):
        Autorenredaktion(memory, ChangingProvider([mutation(Operation.FREI)]), library).mutate(
            project.id, branch.id, "Wandel", source, operation=Operation.FREI)
    with sqlite3.connect(memory.path) as db:
        assert db.execute("SELECT COUNT(*) FROM creative_runs").fetchone()[0] == 0
