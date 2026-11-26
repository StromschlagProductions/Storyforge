# SF-003A – Narrative Library: technische Grundlage

Stand: 26.11.2026. Ausgangsstand `2168165`. Dieser Teilauftrag enthält keine Stoffgenerierung und keine redaktionellen Originalkarten.

## Datenvertrag

Jede Karte liegt als eigenes UTF-8-JSON-Objekt in einer Datei mit Endung `.json` und wird mit `KnowledgeCard` (Pydantic) validiert. Der Dateiname ist frei; die ID steht im Inhalt. Weitere Felder sind nicht zulässig.

| Feld | Pflicht | Werte und Regeln |
| --- | --- | --- |
| `id` | ja | Stabile Zeichenfolge gemäß `^[MNDA][0-9]{2,}$`, z. B. `M01` oder `A10`; erster Buchstabe muss `category` entsprechen. Eine ID darf im geladenen Verzeichnis nur einmal vorkommen. |
| `version` | ja | Ganze JSON-Zahl ab `1`; Zeichenfolgen und boolesche Werte sind ungültig. |
| `category` | ja | Genau `M`, `N`, `D` oder `A`. |
| `name` | ja | Nicht leerer deutscher Text. |
| `principle` | ja | Nicht leerer Text zum erzählerischen Prinzip. |
| `creative_instruction` | ja | Nicht leere kreative Arbeitsanweisung. |
| `applications` | ja | Liste mit mindestens einem nicht leeren Anwendungsgebiet. |
| `quality_questions` | ja | Liste mit mindestens einer nicht leeren Qualitäts- oder Prüffrage. |
| `weaknesses` | ja | Liste mit mindestens einer nicht leeren typischen Schwäche. |
| `audio_relevance` | ja | Nicht leerer Text zur Hörspielrelevanz. |
| `related_ids` | nein | Liste von Karten-IDs im selben geladenen Verzeichnis; Standardwert `[]`. Keine Selbstverweise oder doppelten Verweise. Jeder Verweis muss auflösbar sein. |
| `source` | ja | Nicht leere Herkunfts- oder Forschungsreferenz. Private Quellentexte gehören nicht in dieses öffentliche Repository. |
| `keywords` | ja | Liste mit mindestens einem nicht leeren Schlagwort; keine Dopplungen, auch nicht bei anderer Großschreibung. |
| `task_types` | ja | Liste mit mindestens einer nicht leeren Aufgabenart; keine Dopplungen, auch nicht bei anderer Großschreibung. |

Führende und nachgestellte Leerzeichen in Textfeldern werden entfernt; reine Leerzeichen gelten als leer. Die folgende Karte ist ein **synthetisches Formatbeispiel**, keine redaktionelle Forschungskarte. Sie ist für sich allein in einem Kartenverzeichnis gültig:

```json
{
  "id": "A42",
  "version": 1,
  "category": "A",
  "name": "Synthetischer Klangwechsel",
  "principle": "Ein erfundenes Testgeräusch verändert seine räumliche Wirkung.",
  "creative_instruction": "Beschreibe zwei hörbare Varianten desselben Testgeräuschs.",
  "applications": ["Akustische Skizze"],
  "quality_questions": ["Ist der Wechsel ohne Erklärung wahrnehmbar?"],
  "weaknesses": ["Der Effekt kann ohne erzählerische Folge bleiben."],
  "audio_relevance": "Räumliche Klanggestaltung kann einen Perspektivwechsel vermitteln.",
  "related_ids": [],
  "source": "Synthetisches Formatbeispiel SF-003A; keine Forschungsreferenz",
  "keywords": ["klang", "perspektive"],
  "task_types": ["stoffidee", "dialog"]
}
```

Eine Aktualisierung ersetzt die JSON-Datei mit derselben stabilen ID und einer neuen Version. Die Bibliothek prüft die positive Versionszahl, kann aber ohne vorherigen Bestand keine monotone Erhöhung erzwingen. Sie verwaltet keine parallelen historischen Kartenversionen. Das Kontextmanifest hält die tatsächlich gesendete Version fest. Redaktionell ausgearbeitete Originalkarten müssen separat geprüft und bereitgestellt werden.

## Schnittstellen und Auswahl

`NarrativeLibrary.load(path)` lädt alle `*.json` eines Verzeichnisses; ein fehlendes Verzeichnis oder eine ungültige Karte löst `ValueError` aus. `get(id)` holt eine Karte; eine unbekannte ID löst `KeyError` aus. `related(id)` löst Querverweise auf. `filter(categories=..., keywords=...)` prüft Kategorien exakt und Schlagwörter ohne Beachtung der Großschreibung; bei mehreren Schlagwörtern genügt ein Treffer. `select(task_type, categories=..., keywords=..., limit=3)` verlangt eine passende Aufgabenart (ohne Beachtung der Großschreibung), beschränkt optional Kategorien und Schlagwörter, sortiert nach Zahl passender Schlagwörter und dann stabil nach ID. `limit` muss positiv sein. Das Ergebnis enthält die Karten, Kriterien und eine Begründung pro Karte. Bei fehlendem Treffer sind Karten und Begründungen leer.

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

`.venv/bin/python -m pytest -q`: **44 bestanden**, darunter alle bisherigen 30 Tests. Neue Tests prüfen Dateiladen, Hinzufügen und Aktualisieren ohne Codeänderung, Pflichtfelder und kaputtes JSON, doppelte IDs, Querverweise, unbekannte IDs, Filter, leere und reproduzierbare Auswahl, tatsächliche Kontextübergabe, Manifestversion, Projektisolation, unveränderte Revisionsköpfe und Kontextgrenze mit bestätigter Autorenentscheidung. Alle Testdaten sind synthetisch. Der [GitHub-Actions-Lauf](https://github.com/StromschlagProductions/Storyforge/actions/runs/45890993385) bestand unter Linux und Windows.

## Prüfung der neun Akzeptanzkriterien

1. Hinzufügen und Aktualisieren unabhängig vom Programmcode: mit zusätzlichen und geänderten JSON-Dateien geprüft.
2. Ungültige Karten: Schema, Pflichtinhalte, Version und JSON-Syntax geprüft.
3. Doppelte IDs und ungültige Querverweise: beim Laden abgelehnt.
4. Auswahl: begrenzt, mit Kriterien und Gründen dokumentiert, bei gleicher Eingabe reproduzierbar.
5. Modellkontext: nur explizit ausgewählte Karten; leere Auswahl liefert keine Karteninhalte.
6. Manifest: gesendete Karten-IDs und Versionen einschließlich einer aktualisierten Version verglichen.
7. Revision und Kanon: durch Auswahl und freien Dialog unverändert; Projektisolation geprüft.
8. Regression: alle bisherigen 30 Tests erfolgreich.
9. Neue Funktionen: automatisierte Tests für Laden, Validieren, Filtern, Auswählen und Kontextintegration vorhanden.

## Offene Fragen

- Die 59 konzipierten Mechanismen wurden nicht übernommen. Ihre Texte, Schlagwörter, Aufgabenarten und Forschungsreferenzen brauchen redaktionelle Freigabe; private Berichte gehören nicht in dieses öffentliche Repository.
- Die Auswahl nutzt exakte Aufgabenarten und Schlagwörter ohne semantische Suche. Vor größeren Beständen sind Vokabular und Qualität der Zuordnung anhand kreativer Aufgaben zu prüfen.
- Eine Kartenversion ist im Manifest nachvollziehbar, aber der Inhalt älterer Versionen wird nicht archiviert. Falls reproduzierbare frühere Modellaufrufe nötig werden, ist eine bewusste Archivierungsregel zu entscheiden.
- SF-003B kann die Auswahl für die Stoffschmiede nutzen. Die redaktionellen Originalkarten und kreative Generierungsverfahren sind nicht Teil von SF-003A.
