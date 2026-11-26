# SF-002 – Modelladapter und kreativer Dialog

Stand: 26.11.2026. Ausgangsstand: `819bd3e`. SF-003 wurde nicht begonnen.

## Architekturentscheidungen

- `ModelProvider.generate(ModelRequest, cancel)` ist der kleine gemeinsame Vertrag. `OllamaProvider` spricht standardmäßig nur mit `localhost`/Loopback über `POST /api/chat`; Modellname, Adresse, Optionen und Timeout sind konfigurierbar. `FakeProvider` spielt Antworten und Fehler deterministisch ab. Einheitliche Modellfehler unterscheiden ungültige Antwort, Timeout und Abbruch.
- Ollama wird mit `stream: false` aufgerufen; für strukturierte Antworten wird das JSON-Schema im Feld `format` übergeben. Die Rückgabe normalisiert Modellkennung sowie optionale `total_duration` (Nanosekunden), `prompt_eval_count` und `eval_count`. Dokumentationsgrundlage: [offizielle Ollama-API](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion) und [Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs), geprüft am 26.11.2026.
- `Dialogue` stellt Projekt, Werk, optionales Universum, aktive Variante, Ausgangsrevision mit Hash, sämtliche bestätigten Ideen und Entscheidungen sowie die letzten Gesprächspaare zusammen. Das Kontextmanifest speichert die tatsächlich übermittelten IDs. Bei Platzmangel werden nur die ältesten Gesprächspaare entfernt; passt der bestätigte Stand nicht hinein, endet die Anfrage vor dem Modellaufruf mit Fehler.
- Gesprächsbeiträge liegen in einer eigenen Tabelle (`conversation_turns`, Migration von Schema 1 auf 2). Sie verändern keine Revision. Ein strukturierter Vorschlag enthält die Ausgangsrevision und den vollständigen vorgeschlagenen Ideenstand. Autorenentscheidungen werden ausschließlich aus der aktuellen Revision übernommen. Pydantic und fachliche Prüfungen weisen ungültige Formate, doppelte IDs und entfernte geschützte Elemente ab. `Memory.propose` speichert den Entwurf; `Memory.approve` bleibt der einzige Freigabeschritt.
- Keine automatische externe Datenübermittlung, Telemetrie, Oberfläche oder kostenpflichtige Anbieter. Ein nicht lokaler Ollama-Server erfordert `allow_remote=True` als bewusste Konfiguration.

## Dateien

Neu: `src/storyforge/providers.py`, `src/storyforge/dialogue.py`, `tests/test_providers.py`, `tests/test_dialogue.py`, diese Datei. Geändert: `src/storyforge/memory.py` (Schema 2 und Gesprächsspeicher), `src/storyforge/__init__.py`, `tests/test_memory.py` (Schemaerwartung), `README.md`, `AGENTS.md`. Keine privaten Stoffe oder Datenbanken aufgenommen.

## Automatisierte Tests

`.venv/bin/python -m pytest -q`: **30 bestanden**. Die bisherigen neun SF-001-Tests bleiben erfolgreich. Die Tests nutzen Fake-Antworten und einen lokalen HTTP-Testserver; sie benötigen weder Ollama noch GPU, API-Schlüssel oder Internetzugriff auf ein Modell. Die Abschlussprüfung ergänzte einen vollständigen Prozessneustart des Dialogs, den 1:1-Abgleich von Manifest und gesendetem Kontext, Abbruch nach der Modellantwort, Konkurrenz während des Modellaufrufs, Ablehnung eines fremden Variantenschlüssels, unverändertes DB-Schema beim Modellwechsel und die Prüfung der Modellfähigkeiten. **Ein echtes Ollama-Modell wurde nicht ausgeführt:** Auf der Prüfmaschine ist kein `ollama`-Programm installiert. Simulierte HTTP-Antworten sind keine realen Modelltests. Der Linux- und Windows-CI-Lauf für den veröffentlichten Stand wird nach dem Push geprüft.

## Abschlussprüfung der zehn Akzeptanzkriterien

1. Fake-Provider mit vollständigem Projektgespräch: erfüllt; zwei Gesprächsrunden mit gespeichertem Verlauf und erneutem Laden.
2. Ollama frei und strukturiert: HTTP-Vertrag für beide Modi am lokalen Testserver geprüft; realer Modelllauf offen.
3. Modellwechsel ohne Datenbankänderung: erfüllt; anderer Fake-Modellname bei identischem SQLite-Schema.
4. Kontextmanifest: erfüllt; Projekt-, Werk-, Universums-, Varianten-, Revisions-, Ideen-, Entscheidungs- und Verlauf-IDs mit der tatsächlich gesendeten Nachricht verglichen.
5. Isolation: erfüllt; fremdes Projekt und nicht gewählte Variante fehlen im Modellkontext; ein fremder Variantenschlüssel wird vor dem Provideraufruf abgelehnt.
6. Unverbindliche KI-Vorschläge: erfüllt; ohne `Memory.approve` bleibt der Revisionskopf unverändert. Freier Dialog erzeugt keinen Vorschlag.
7. Ungültig, abgebrochen, veraltet: erfüllt; keine verbindliche Änderung bei fehlerhafter oder unvollständiger Antwort, Offline-Fall, Timeout und Abbruch. Eine Änderung während des Modellaufrufs macht den Vorschlag veraltet.
8. Kreativer Dialog ohne Modelländerung: erfüllt; Gesprächsbeiträge werden getrennt von Revisionen gespeichert.
9. SF-001-Regression: erfüllt; alle neun bisherigen Tests bestehen.
10. Automatisierte Tests: erfüllt; 30 pytest-Tests, einschließlich lokaler Ollama-HTTP-Simulation. Windows-CI-Ergebnis folgt nach Veröffentlichung.

Die Kontextgrenze zählt Zeichen der gesendeten Nachrichteninhalte, nicht modellabhängige Token. Sämtliche bestätigten Entscheidungen bleiben im Systemkontext; falls dieser zu groß ist, erfolgt kein Modellaufruf. Der Standard-Ollama-Adapter akzeptiert nur Loopback-Adressen; eine nicht lokale Adresse verlangt ausdrücklich `allow_remote=True`. Es gibt keine Telemetrie.

## Optionaler manueller Ollama-Smoke-Test unter Windows

1. Ollama lokal installieren und starten. `ollama list` ausführen; einen dort installierten Modellnamen für `$env:STORYFORGE_MODEL` wählen. Falls noch kein Modell vorhanden ist, ein gewünschtes Modell mit `ollama pull <modellname>` lokal laden. Diese Schritte laden möglicherweise Modelldaten aus dem Internet; der Test selbst spricht nur den lokalen Server an.
2. Im Repository in PowerShell ausführen:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e ".[test]"
$env:STORYFORGE_MODEL = "<installierter-modellname>"
@'
import os
from pathlib import Path
from storyforge import Dialogue, Memory, OllamaProvider

memory = Memory(Path("local/ollama-smoke.sqlite3"))
project = memory.create_project("Synthetischer Smoke-Test")
branch = memory.list_branches(project.id)[0]
dialog = Dialogue(memory, OllamaProvider(os.environ["STORYFORGE_MODEL"]))
result = dialog.ask(project.id, branch.id, "Nenne eine ungewöhnliche akustische Erzählmöglichkeit.")
print(result.answer)
print("Modell:", result.model, "Revision:", result.manifest["revision_id"])
print("Revisionskopf unverändert:", memory.list_branches(project.id)[0].head_id == branch.head_id)
'@ | .venv\Scripts\python -
```

Der Test erzeugt nur synthetische lokale Daten in `local/` (gitignored) und löst keine Autorfreigabe aus. Für einen strukturierten Versuch `dialog.ask(..., structured=True)` verwenden und die erzeugte `proposal_id` prüfen; die Qualität der Modellantwort ist modellabhängig. Keine privaten Stoffe für einen Smoke-Test verwenden.

## Offene Fragen und Empfehlung

- Ollama-Modellqualität, tatsächliche Windows-Laufzeit und Tokenlimits lassen sich erst mit einem ausgewählten lokalen Modell manuell beurteilen. Die automatisierten HTTP-Vertragstests belegen den Adapter, keinen realen Modelllauf.
- Abbruch während eines laufenden HTTP-Aufrufs schließt die Verbindung und beendet den Dialog sofort; ein bereits gestarteter Serveraufruf kann noch kurz nachlaufen. Dabei erfolgt keine Kanonänderung.
- Für SF-003 reicht der Provider-Vertrag mit freien Nachrichten und frei wählbarem JSON-Schema als technische Basis. Der aktuelle `Dialogue`-Pfad validiert strukturierte Änderungen bewusst nur als Ideen-Snapshot. Geheimnishypothesen, Kritik und mehrere Kandidaten benötigen in SF-003 eigene geprüfte Ergebnisverträge und Kontextauswahl; sie wurden hier nicht vorweggenommen. Modellantworten redaktionell prüfen; eine Autorfreigabe bleibt explizit.
