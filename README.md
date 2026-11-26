# STORYFORGE

Deutschsprachige KI-gestützte Hörspiel-Autorenwerkstatt von Stromschlag Audio. Kreative Stoffentwicklung, Geheimnisse, Varianten und kritischer Dialog stehen im Mittelpunkt. Fade In bleibt eine optionale unterstützende Schnittstelle.

Einstieg: [Masterplan](docs/MASTERPLAN.md), [P0-Auftragsplan](docs/tasks/P0_Auftragsplan.md), [Technische Architektur](docs/research/08_Technische_Architektur.md), [Arbeitsregeln](AGENTS.md).

Status: SF-001, SF-002, die Narrative Library SF-003A und die Stoffschmiede SF-003B als lokaler Python-Kern implementiert; noch keine Oberfläche. Dieses öffentliche Repository enthält ausschließlich bereinigte Dokumentation, Code und synthetische Testdaten. Private kreative Inhalte bleiben lokal.

## Lokal starten

Python 3.10 oder neuer. Unter Windows:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e ".[test]"
.venv\Scripts\python -m pytest
```

Unter Linux/macOS `python -m venv .venv`, danach `.venv/bin/python` statt `.venv\Scripts\python` verwenden.

## Projektgedächtnis (SF-001)

Die Bibliothek hat noch keine Kommandozeile. Ein Projekt ohne Skript lässt sich so anlegen und nach einem Neustart wieder öffnen:

```python
from pathlib import Path
from storyforge import Memory

pfad = Path("local/meine-projekte.sqlite3")  # local/ wird nicht committet
speicher = Memory(pfad)
projekt = speicher.create_project("Neuer Stoff", universe_title="Optionales Universum")
projekt_id = projekt.id  # Diese ID für das erneute Öffnen aufbewahren.

spaeter = Memory(pfad)
print(spaeter.get_project(projekt_id))
```

Stoffideen und Entscheidungen liegen in `Snapshot`-Objekten. `propose` speichert einen Entwurf, ohne den Stand zu ändern. `approve(proposal_id, approved_by="...", explicit_approval=True)` übernimmt ihn nur bei ausdrücklicher Freigabe und aktueller Ausgangsrevision. `create_branch` eröffnet eine isolierte Variante; `restore` erstellt einen freizugebenden Wiederherstellungsentwurf. `export_file(project_id, pfad, format="json")` und `format="markdown"` schreiben atomare Dateien. Siehe [SF-001-Bericht](docs/tasks/SF-001_Ergebnis.md) für Datenverträge und Grenzen.

## Kreativer Dialog (SF-002)

`Dialogue` verbindet ein ausgewähltes Projekt und eine Variante mit einem `FakeProvider` oder dem lokalen `OllamaProvider`. Freie Antworten bleiben Gespräch; strukturierte Antworten werden als unverbindliche Entwürfe gespeichert. Nur ein ausdrücklicher Aufruf von `Memory.approve` verändert den Revisionskopf. Beispiel und optionaler Windows-Smoke-Test: [SF-002-Bericht](docs/tasks/SF-002_Ergebnis.md).

## Narrative Library (SF-003A)

`NarrativeLibrary.load(verzeichnis)` liest versionierte Wissenskarten aus einzelnen JSON-Dateien. `select(aufgabenart, categories={...}, keywords={...}, limit=...)` liefert eine begründete, begrenzte Auswahl. Nur bei `Dialogue.ask(..., cards=auswahl)` gelangen deren Inhalte in den Modellkontext. Die vier Dateien unter `examples/synthetic_cards/` sind ausschließlich synthetische Testbeispiele. Datenvertrag und Nutzung: [SF-003A-Bericht](docs/tasks/SF-003A_Ergebnis.md).

## Stoffschmiede (SF-003B)

`Stoffschmiede(memory, provider, NarrativeLibrary.load("library/cards"))` entwickelt zwei bis fünf unverbindliche Stoffkeime. Die redaktionell bereitgestellten Karten bleiben unter `library/cards/` getrennt von synthetischen Beispielen. Ergebnisvertrag, Freigabeweg und optionaler Windows-Ollama-Test: [SF-003B-Bericht](docs/tasks/SF-003B_Ergebnis.md).
