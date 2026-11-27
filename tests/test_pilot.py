"""SF-005: synthetische Fake-Läufe, Verblindung und getrennte Persistenz."""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from threading import Event
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from storyforge import FakeProvider, ModelCancelled, ModelTimeout
from storyforge.pilot import PilotConfig, PilotLab, PilotRating
from storyforge.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "pilot" / "cases"
CARDS = ROOT / "library" / "cards"


def config(case="T01"):
    return PilotConfig(case_id=case, model="fake-lokal", temperature=0.7,
                       num_predict=1024, repetitions=1)


def stoff_answer(head, ids):
    return json.dumps({"base_revision_id": str(head), "candidates": [{
        "title": f"Synthetischer Ansatz {index}", "premise": "Eine künstliche Testprämisse.",
        "narrative_promise": "Eine offene Frage", "mechanism": f"Testmechanismus {index}",
        "mechanism_card_id": ids[index-1] if ids else None,
        "central_mystery": None, "personal_conflict": "Schuld", "development": "Eine neue Spur",
        "audio_potential": "Räumlicher Klang", "fictional_assumptions": [],
        "research_questions": [], "weaknesses": [],
        "used_card_ids": [ids[index-1]] if ids else []
    } for index in range(1, 4)]}, ensure_ascii=False)


def mutation_answer(protected):
    return json.dumps({"alternativen": [{
        "bezeichnung": "Künstliche Alternative", "kurzbeschreibung": "Eine neue Ursache.",
        "operation": "frei", "veraenderte_elemente": ["Erklärung"],
        "bewahrte_elemente": protected, "neue_moeglichkeiten": ["Anderer Schluss"],
        "kausale_konsequenzen": ["Noch zu prüfen"],
        "dramaturgische_konsequenzen": ["Spätere Enthüllung"],
        "figuren_und_geheimnisse": ["Eine Figur zweifelt"],
        "hoerspielpotenzial": ["Signal"], "risiken": ["Unklarheit"],
        "ungeklaerte_auswirkungen": ["Zeitfolge"],
        "schutzpruefungen": [{"element": item, "status": "bewahrt", "begruendung": "Im Testtext enthalten"}
                              for item in protected], "verwendete_karten_ids": []
    }]}, ensure_ascii=False)


def lab(tmp_path, answers):
    providers = []

    def factory(model, params):
        assert model == "fake-lokal"
        assert params == {"temperature": 0.7, "num_predict": 1024}
        provider = FakeProvider([answers.pop(0)], model=model)
        providers.append(provider)
        return provider

    return PilotLab(tmp_path / "pilot.sqlite3", factory, cases=CASES, cards=CARDS), providers


def test_sechs_synthetische_faelle_und_vertraege(tmp_path):
    pilot, _ = lab(tmp_path, [])
    assert sorted(pilot.cases) == [f"T0{i}" for i in range(1, 7)]
    assert all(case.version == 1 for case in pilot.cases.values())
    assert len(pilot.library.filter()) == 59
    with pytest.raises(ValueError, match="Unbekannter"):
        pilot.create_group(config("T99"))


def test_a_b_c_kontext_verblindung_export_und_neustart(tmp_path):
    pilot, providers = lab(tmp_path, [])
    group = pilot.create_group(config())
    data = pilot._group(group)
    head = pilot.core.list_branches(UUID(data["project_id"]))[0].head_id
    from storyforge import Stoffschmiede
    task = pilot.cases["T01"].task
    ids = [c.id for c in Stoffschmiede(pilot.core, FakeProvider([]), pilot.library).select_cards(task).cards]
    answers = [stoff_answer(head, []), stoff_answer(head, []), stoff_answer(head, ids)]
    pilot.provider_factory = lambda model, params: providers.append(FakeProvider([answers.pop(0)], model=model)) or providers[-1]
    for arm in "ABC":
        pilot.execute(group, arm, 1)
    assert len(providers) == 3 and all(len(p.requests) == 1 for p in providers)
    runs = pilot.blind_runs(group)
    assert len(runs) == 3 and all("arm" not in row for row in runs)
    assert all(len(row["candidates"]) == 3 for row in runs)
    with pytest.raises(ValueError, match="bewertet"):
        pilot.report(group, reveal=True)
    for row in runs:
        pilot.rate(row["blind_id"], PilotRating(fascination=4, notes="Synthetischer Test"))
    report = pilot.report(group, reveal=True)
    assert {r["arm"] for r in report["runs"]} == {"A", "B", "C"}
    for run in report["runs"]:
        assert run["metrics"]["calls"] == 1
        assert run["metrics"]["optional_reflection_calls"] == 0
        request = run["manifest"]["transmitted_requests"][0]
        cards = run["manifest"]["creative_context"].get("cards", [])
        transmitted = json.loads(request["messages"][0]["content"].split("Projektkontext:\n",1)[1])
        assert [(c["id"], c["version"]) for c in transmitted.get("wissenskarten", [])] == [
            (c["id"], c["version"]) for c in cards]
        assert request["format_schema"] is not None
    assert next(r for r in report["runs"] if r["arm"] == "A")["manifest"]["creative_context"].get("cards", []) == []
    assert pilot.core.list_branches(UUID(data["project_id"]))[0].head_id == head
    assert "Synthetischer Test" in pilot.markdown(group, reveal=True)
    code = ("import json,sys; from storyforge.pilot import PilotLab; "
            "from storyforge import FakeProvider; "
            "p=PilotLab(sys.argv[1],lambda m,o:FakeProvider([]),cases=sys.argv[2],cards=sys.argv[3]); "
            "print(json.dumps(p.report(sys.argv[4],reveal=True)))")
    restored = json.loads(subprocess.check_output([sys.executable,"-c",code,
        str(pilot.path),str(CASES),str(CARDS),group],text=True))
    assert restored == report
    assert pilot.core.list_projects()  # Nur die Pilot-Core-Datenbank enthält diese Projekte.
    assert not (tmp_path / "storyforge.sqlite3").exists()


def test_t06_schutz_und_fehler(tmp_path):
    pilot, _ = lab(tmp_path, [])
    group = pilot.create_group(config("T06"))
    protected = pilot.cases["T06"].protected
    pilot.provider_factory = lambda model, params: FakeProvider([mutation_answer(protected)], model=model)
    for arm in "ABC":
        pilot.execute(group, arm, 1)
    assert all(run["status"] == "fertig" for run in pilot.blind_runs(group))
    other = pilot.create_group(config("T06"))
    pilot.provider_factory = lambda model, params: FakeProvider([mutation_answer(protected[:1])],model=model)
    with pytest.raises(Exception, match="Schutzprüfung"):
        pilot.execute(other, "A", 1)
    assert pilot.blind_runs(other)[0]["status"] == "fehler"
    assert pilot.blind_runs(other)[0]["error"] == "Lauf fehlgeschlagen"
    assert "Schutzprüfung" in pilot.report(other, reveal=True)["runs"][0]["error"]
    for error in (ModelTimeout("Zeitüberschreitung"), ModelCancelled("Abbruch")):
        trial = pilot.create_group(config("T06"))
        pilot.provider_factory = lambda model, params: FakeProvider([error],model=model)
        with pytest.raises(type(error)):
            pilot.execute(trial, "B", 1)
        assert pilot.blind_runs(trial)[0]["status"] in {"fehler", "abgebrochen"}
    trial = pilot.create_group(config("T06"))
    cancel = Event(); cancel.set()
    with pytest.raises(ModelCancelled):
        pilot.execute(trial, "C", 1, cancel)
    assert pilot.blind_runs(trial)[0]["status"] == "abgebrochen"


def test_http_testwerkstatt_ohne_ollama(tmp_path):
    app = create_app(tmp_path / "storyforge.sqlite3", CARDS,
                     pilot_provider_factory=lambda model,params: FakeProvider(["kein JSON"],model=model),
                     pilot_cases=CASES)
    client = TestClient(app)
    assert len(client.get('/api/pilot/cases').json()) == 6
    group = client.post('/api/pilot/groups',json=config().model_dump()).json()['id']
    assert client.get('/api/pilot/groups/' + group + '/blind').json() == []
    assert client.get('/api/pilot/groups/' + group + '/export/json').status_code == 200
    assert client.get('/api/pilot/groups/' + group + '/export/markdown').status_code == 200
    started = client.post('/api/pilot/groups/' + group + '/runs?arm=A&repetition=1')
    assert started.status_code == 200
    job_id = started.json()['id']
    for _ in range(100):
        state = client.get('/api/jobs/' + job_id).json()
        if state['status'] not in {'läuft', 'abbruch angefordert'}:
            break
        time.sleep(0.01)
    assert state['status'] == 'fehler'
    assert client.get('/api/pilot/groups/' + group + '/blind').json()[0]['status'] == 'fehler'
    page = client.get('/').text
    assert 'pilot.js' in page and 'pilot-workshop' in page
    script = client.get('/static/pilot.js').text
    assert 'textContent' in script and '.innerHTML' not in script


def test_testfall_snapshot_bleibt_trotz_dateiaktualisierung(tmp_path):
    folder = tmp_path / "cases"
    shutil.copytree(CASES, folder)
    database = tmp_path / "pilot.sqlite3"
    pilot = PilotLab(database, lambda model,params: FakeProvider([]), cases=folder, cards=CARDS)
    group = pilot.create_group(config())
    original = pilot.report(group)["case"]
    updated = json.loads((folder / "T01.json").read_text(encoding="utf-8"))
    updated["version"] = 2
    updated["task"] = "Ein anderer synthetischer Auftrag."
    (folder / "T01.json").write_text(json.dumps(updated), encoding="utf-8")
    reopened = PilotLab(database, lambda model,params: FakeProvider([]), cases=folder, cards=CARDS)
    assert reopened.report(group)["case"] == original
    assert reopened.cases["T01"].version == 2
