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

`.venv/bin/python -m pytest -q`: **24 bestanden**. Die bisherigen neun SF-001-Tests bleiben erfolgreich. Die neuen Tests nutzen Fake-Antworten und einen lokalen HTTP-Testserver; sie benötigen weder Ollama noch GPU, API-Schlüssel oder Internetzugriff auf ein Modell. Geprüft werden Dialog und Neustart, Kontextisolation, Manifest, Modellwechsel, Entwurf ohne Freigabe, Abbruch, Timeout, Offline-Fall, ungültige und veraltete Vorschläge, Schutz bestehender Elemente, Ollama-Payload und optionale Metriken. **Ein echtes Ollama-Modell wurde in diesem Auftrag nicht ausgeführt.** Der CI-Workflow führt dieselbe Suite nach einem späteren Push unter Linux und Windows aus; es erfolgt hier kein Push.

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
- Für SF-003 die geplanten kreativen Verfahren auf `Dialogue` und unverbindliche Entwürfe aufsetzen und erst dann geeignete Wissenskarten bereitstellen. Modellantworten redaktionell prüfen; eine Autorfreigabe bleibt explizit.
