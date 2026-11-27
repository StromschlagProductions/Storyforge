# STORYFORGE

Deutschsprachige KI-gestützte Hörspiel-Autorenwerkstatt von Stromschlag Audio. Kreative Stoffentwicklung, Geheimnisse, Varianten und kritischer Dialog stehen im Mittelpunkt. Fade In bleibt eine optionale unterstützende Schnittstelle.

Einstieg: [Masterplan](docs/MASTERPLAN.md), [P0-Auftragsplan](docs/tasks/P0_Auftragsplan.md), [Technische Architektur](docs/research/08_Technische_Architektur.md), [Arbeitsregeln](AGENTS.md).

Status: SF-001 bis SF-005 sind technisch implementiert; der Komfort-Patch zur lokalen Ollama-Verwaltung ist enthalten. [0.1.0-alpha.2](docs/releases/STORYFORGE_0.1.0-alpha.2.md) ist zur Veröffentlichung vorbereitet. Dieses öffentliche Repository enthält ausschließlich bereinigte Dokumentation, Code und synthetische Testdaten. Private kreative Inhalte bleiben lokal.

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

## Geheimnislabor (SF-003C)

`Geheimnislabor(memory, provider, library)` entwickelt und prüft unverbindliche Mystery-Hypothesen in vier Arbeitsweisen. Beobachtungen, Interpretationen, Hypothesen und ihre begründete Matrix bleiben getrennt; bestätigte Wahrheit stammt ausschließlich vom Autor. Datenvertrag, Grenzen und Tests: [SF-003C-Bericht](docs/tasks/SF-003C_Ergebnis.md).

## Narrative Mutation und Kritik (SF-003D)

`Autorenredaktion` entwickelt gezielte Varianten und begründete Kritik aus bestätigten Ideen, gespeicherten kreativen Ergebnissen oder freien Stoffbeschreibungen. Ergebnisse bleiben unverbindliche Creative Runs. Schnittstellen und Datenverträge: [SF-003D-Bericht](docs/tasks/SF-003D_Ergebnis.md).

## Autorenoberfläche (SF-004)

Unter Windows `Start_Storyforge.bat` doppelklicken. Für einen einfachen Test steht das vollständige [Windows-ZIP](downloads/STORYFORGE-0.1.0-alpha.2-Windows.zip) mit [Kurzanleitung](WINDOWS_KURZANLEITUNG.txt) bereit. Die Anwendung öffnet sich lokal im Browser, prüft Ollama, startet es bei Bedarf im Hintergrund und zeigt installierte Modelle. Mit „STORYFORGE beenden“ werden der lokale Server und nur ein selbst gestarteter Ollama-Prozess beendet. Ohne Ollama bleiben Projekte und Exporte nutzbar. Zwei Classic-Themes, Projektakte, alle Verfahren V01–V05 und Export sind verbunden. Einrichtung und Einschränkungen: [SF-004-Ergebnis](docs/tasks/SF-004_Ergebnis.md).

Unter **Einstellungen** liegt die optionale [SF-005-Testwerkstatt](docs/tasks/SF-005_Ergebnis.md) mit sechs synthetischen Fällen und verblindeter Bewertung. Für den ersten echten Autoren-Test gibt es eine [Kurzanleitung](SF-005_PILOT_KURZANLEITUNG.md). Der [P0-Stand](docs/tasks/SF-005_Ergebnis.md#p0-entwicklungsstand) trennt technische Umsetzung von offenen Praxisprüfungen. Reale kreative Qualität wurde bislang nicht untersucht.

Prozessbesitz, Fehlermeldungen und die vorbereitete Windows-Distribution für alpha.2 sind im [Bericht zum Ollama-Komfort-Patch](docs/tasks/Ollama_Komfortpatch_Ergebnis.md) dokumentiert. Ein GitHub-Release für alpha.2 ist noch nicht erstellt.

Für langsame lokale Modelle und strukturierte Antworten beschreibt [ALPHA-2 Modellkommunikation](docs/tasks/ALPHA2_Modellkommunikation_Ergebnis.md) die Timeout- und Ollama-Limits sowie eine datensparsame lokale Fehlerdiagnose. Der konkrete Gemma-Fehler auf dem Autoren-PC muss mit diesen Diagnosen erneut beobachtet werden.

Die [Gesprächsansicht und kreativen Anschlussaktionen](docs/tasks/ALPHA2_Kreativer_Arbeitsfluss_Ergebnis.md) zeigen den vollständigen Verlauf, freie V01-Antworten während des Ollama-Streamings und sicheres lokales Markdown. Geeignete Beiträge und gespeicherte Ergebnisse können direkt in weitere Verfahren übernommen oder als unverbindlicher Ideenentwurf vorgemerkt werden. Der [Auftrag](docs/tasks/ALPHA2_Kreativer_Arbeitsfluss_Auftrag.md) und zwei synthetische Screenshots sind im Repository hinterlegt.
