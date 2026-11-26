# SF-003A – Narrative Library: technische Grundlage

Stand: 26.11.2026. Ausgangsstand `2168165`. Dieser Teilauftrag enthält keine Stoffgenerierung und keine redaktionellen Originalkarten.

## Datenvertrag

Jede Karte liegt als eigene UTF-8-JSON-Datei vor und wird mit `KnowledgeCard` (Pydantic) validiert. Pflichtfelder: `id` (`M01`, `N01`, `D01`, `A01` usw.), positive `version`, `category` (`M`, `N`, `D`, `A`), `name`, `principle`, `creative_instruction`, `applications`, `quality_questions`, `weaknesses`, `audio_relevance`, `source`, `keywords` und `task_types`. `related_ids` ist eine Liste anderer Karten-IDs. Pflichttexte und die fachlichen Listen dürfen nicht leer sein. Unbekannte Felder, falsche ID/Kategorie, Selbstverweise, doppelte IDs und unbekannte Querverweise werden abgelehnt.

Die Kartenversion ist eine positive ganze Zahl. Eine Aktualisierung ersetzt die JSON-Datei mit derselben stabilen ID und höherer Version; diese kleine Bibliothek verwaltet keine parallelen historischen Kartenversionen. Das Kontextmanifest hält die tatsächlich gesendete Version fest. Redaktionell ausgearbeitete Originalkarten müssen separat geprüft und bereitgestellt werden.

## Schnittstellen und Auswahl

`NarrativeLibrary.load(path)` lädt alle `*.json` eines Verzeichnisses; `get(id)` holt eine Karte, `filter(categories=..., keywords=...)` filtert nach Kategorie und Schlagwort, `related(id)` löst Querverweise auf. `select(task_type, categories=..., keywords=..., limit=3)` verlangt eine passende Aufgabenart, beschränkt optional Kategorien und Schlagwörter, sortiert nach Zahl passender Schlagwörter und dann stabil nach ID. Das Ergebnis enthält die Karten, Kriterien und eine Begründung pro Karte. Bei fehlendem Treffer ist die Auswahl leer.

```python
from storyforge import NarrativeLibrary, Dialogue

library = NarrativeLibrary.load("examples/synthetic_cards")
selection = library.select("stoffidee", categories={"M", "A"}, keywords={"klang"}, limit=2)
result = Dialogue(memory, provider).ask(project_id, branch_id, "Welche akustische Idee?", cards=selection)
print(result.manifest["cards"])  # z. B. [{"id": "A01", "version": 1}]
```

`cards` ist optional. Ohne übergebene Auswahl sendet der Dialog keine Wissenskarten. Mit Auswahl enthält der Systemkontext ausschließlich deren vollständige Datensätze; das Manifest enthält IDs, Versionen, Kriterien und Begründungen. Die bisherige Zeichengrenze umfasst die Karten. Übersteigt der bestätigte Projektstand zusammen mit der Auswahl die Grenze, bricht die Anfrage vor dem Modellaufruf ab. Weder Auswahl noch Dialog verändern Revisionen oder umgehen die Autorfreigabe.

## Dateien und Tests

Neu: `src/storyforge/narrative_library.py`, vier ausdrücklich synthetische JSON-Karten in `examples/synthetic_cards/`, `tests/test_narrative_library.py`, diese Datei. Geändert: `src/storyforge/dialogue.py`, `src/storyforge/__init__.py`, `README.md`, `AGENTS.md`.

`.venv/bin/python -m pytest -q`: **43 bestanden**, darunter alle bisherigen 30 Tests. Neue Tests prüfen Dateiladen und Aktualisieren, Pflichtfelder und kaputtes JSON, doppelte IDs, Querverweise, Filter und reproduzierbare Auswahl, tatsächliche Kontextübergabe, Manifestversion und Kontextgrenze. Alle Testdaten sind synthetisch. CI wird erst nach einem gesondert freigegebenen Push laufen.

## Offene Fragen

- Die 59 konzipierten Mechanismen wurden nicht übernommen. Ihre Texte, Schlagwörter, Aufgabenarten und Forschungsreferenzen brauchen redaktionelle Freigabe; private Berichte gehören nicht in dieses öffentliche Repository.
- Die Auswahl nutzt exakte Aufgabenarten und Schlagwörter ohne semantische Suche. Vor größeren Beständen sind Vokabular und Qualität der Zuordnung anhand kreativer Aufgaben zu prüfen.
- Eine Kartenversion ist im Manifest nachvollziehbar, aber der Inhalt älterer Versionen wird nicht archiviert. Falls reproduzierbare frühere Modellaufrufe nötig werden, ist eine bewusste Archivierungsregel zu entscheiden.
- SF-003B kann die Auswahl für die Stoffschmiede nutzen. Die redaktionellen Originalkarten und kreative Generierungsverfahren sind nicht Teil von SF-003A.
