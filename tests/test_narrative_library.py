import json
from pathlib import Path

import pytest

from storyforge import (ContextLimitError, Dialogue, FakeProvider, Memory,
                        NarrativeLibrary)


FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "synthetic_cards"


def _copy_cards(tmp_path):
    for source in FIXTURES.glob("*.json"):
        (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_karten_aus_dateien_laden_und_version_aktualisieren(tmp_path):
    folder = _copy_cards(tmp_path)
    library = NarrativeLibrary.load(folder)
    assert library.get("M01").version == 1
    assert [card.id for card in library.related("M01")] == ["N01"]
    source = folder / "M01.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    data["version"] = 2
    data["name"] = "Aktualisierte synthetische Karte"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    updated = NarrativeLibrary.load(folder)
    assert updated.get("M01").version == 2
    assert updated.get("M01").name == "Aktualisierte synthetische Karte"
    assert library.get("M01").version == 1


@pytest.mark.parametrize("change", [
    {"version": 0}, {"version": "2"}, {"category": "A"}, {"principle": "  "},
    {"keywords": []}, {"unexpected": "nicht erlaubt"},
    {"related_ids": ["M01"]},
])
def test_ungueltige_karten_werden_abgelehnt(tmp_path, change):
    folder = _copy_cards(tmp_path)
    source = folder / "M01.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    data.update(change)
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="M01.json"):
        NarrativeLibrary.load(folder)


def test_doppelte_ids_und_unbekannte_querverweise(tmp_path):
    folder = _copy_cards(tmp_path)
    (folder / "kopie.json").write_text((folder / "M01.json").read_text(encoding="utf-8"),
                                       encoding="utf-8")
    with pytest.raises(ValueError, match="Doppelte Karten-ID"):
        NarrativeLibrary.load(folder)
    (folder / "kopie.json").unlink()
    source = folder / "M01.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    data["related_ids"] = ["N99"]
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="Unbekannter Querverweis"):
        NarrativeLibrary.load(folder)


def test_kaputtes_json_und_fehlendes_verzeichnis(tmp_path):
    with pytest.raises(ValueError, match="Kartenverzeichnis fehlt"):
        NarrativeLibrary.load(tmp_path / "fehlt")
    folder = _copy_cards(tmp_path)
    (folder / "M01.json").write_text("{kein JSON", encoding="utf-8")
    with pytest.raises(ValueError, match="M01.json"):
        NarrativeLibrary.load(folder)


def test_filter_und_reproduzierbare_begrenzte_auswahl(tmp_path):
    library = NarrativeLibrary.load(_copy_cards(tmp_path))
    assert [card.id for card in library.filter(categories={"M", "A"})] == ["A01", "M01"]
    assert [card.id for card in library.filter(keywords={"KLANG"})] == ["A01"]
    first = library.select("stoffidee", categories={"A", "M", "N"}, limit=2)
    second = library.select("stoffidee", categories={"N", "M", "A"}, limit=2)
    assert [card.id for card in first.cards] == ["A01", "M01"]
    assert first == second
    assert all("stoffidee" in reason for reason in first.reasons)
    focused = library.select("stoffidee", keywords={"perspektive"}, limit=1)
    assert [card.id for card in focused.cards] == ["M01"]
    assert focused.keywords == ("perspektive",)
    assert library.select("unbekannt").cards == ()
    with pytest.raises(ValueError):
        library.select("stoffidee", limit=0)


def test_nur_ausgewaehlte_karten_im_kontext_und_manifest(tmp_path):
    folder = tmp_path / "cards"
    folder.mkdir()
    _copy_cards(folder)
    changed = folder / "A01.json"
    data = json.loads(changed.read_text(encoding="utf-8"))
    data["version"] = 2
    changed.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    library = NarrativeLibrary.load(folder)
    selected = library.select("stoffidee", keywords={"klang"}, limit=1)
    memory = Memory(tmp_path / "projekt.sqlite3")
    project = memory.create_project("Synthetisches Werk")
    branch = memory.list_branches(project.id)[0]
    provider = FakeProvider(["Eine mögliche Lesart."])
    result = Dialogue(memory, provider).ask(project.id, branch.id, "Welche Klangidee?", cards=selected)
    context = provider.requests[0].messages[0]["content"]
    core = json.loads(context.split("Projektkontext:\n", 1)[1])
    assert [card["id"] for card in core["wissenskarten"]] == ["A01"]
    assert "Synthetischer Perspektivwechsel" not in context
    assert result.manifest["cards"] == [{"id": "A01", "version": 2}]
    assert result.manifest["card_selection"]["reasons"] == list(selected.reasons)
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
    assert memory.get_revision(branch.head_id).snapshot.ideas == []
    assert json.loads(memory.list_turns(project.id, branch.id)[1]["manifest"])["cards"] == result.manifest["cards"]


def test_karten_respektieren_kontextgrenze_ohne_entscheidungen_zu_kuerzen(tmp_path):
    library = NarrativeLibrary.load(FIXTURES)
    selection = library.select("stoffidee", limit=3)
    memory = Memory(tmp_path / "projekt.sqlite3")
    project = memory.create_project("Synthetisches Werk")
    branch = memory.list_branches(project.id)[0]
    provider = FakeProvider(["nicht verwendet"])
    with pytest.raises(ContextLimitError):
        Dialogue(memory, provider, max_context_chars=100).ask(
            project.id, branch.id, "Frage", cards=selection)
    assert provider.requests == []
    assert memory.list_branches(project.id)[0].head_id == branch.head_id
