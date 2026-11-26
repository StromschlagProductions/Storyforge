# SF-003B – Kreative Stoffschmiede V02

Stand: 26.11.2026. Ausgangsstand `2b16e39` (LIB-001). Kein Geheimnis- oder Mutationslabor implementiert.

## Vorprüfung der Narrative Library

`NarrativeLibrary.load("library/cards")` lädt alle **59** produktiven Karten mit Pydantic-Schemavalidierung, eindeutigen IDs und gültigen Querverweisen: **16 M, 16 N, 17 D, 10 A**. Ein Integrationstest prüft diese Verteilung und Auswahlbeispiele für `stoffidee`, `geheimnis` und `dramaturgie`. Die produktiven Karten bleiben unter `library/cards/`; die vier synthetischen Beispiele bleiben unter `examples/synthetic_cards/`. Die Karten sind redaktionelle Anregungen, kein Nachweis kreativer Qualität.

## Architektur und Schnittstellen

- `Stoffschmiede(memory, provider, library)` verwendet den bestehenden Provider-Vertrag und die Projektkontext-Erstellung von `Dialogue`. `develop(project_id, branch_id, task, count=3, card_limit=4, reflect=False, cancel=None)` benötigt kein Skript. Ein Aufruf generiert zwei bis fünf Kandidaten; `reflect=True` fügt genau einen separaten kritischen Aufruf hinzu.
- `select_cards(task, limit=4)` zieht exakte Aufgabenbegriffe aus den Kartenschlagwörtern vor und versucht zunächst je eine Karte aus M, N, A und D. Ohne exakten Treffer wählt es explizit gekennzeichnete Kategorie-Fallbacks. Weitere Plätze werden deterministisch aufgefüllt. Es werden zwei bis fünf Karten angefragt; bei einer kleineren Bibliothek sind weniger oder keine Karten möglich. Ist die Bibliothek leer, werden Stoffkeime ohne Karten-IDs angefragt und validiert. Keine Karte oder ID wird erfunden.
- Die ausgewählten Karten werden den Kandidaten als unterschiedliche Ausgangspunkte zugeordnet. Der JSON-Ergebnisvertrag verlangt genau die angeforderte Zahl, verschiedene benannte Mechanismen, passende `mechanism_card_id` und `used_card_ids` ausschließlich aus der tatsächlichen Auswahl. Die technische Prüfung kann semantische Originalität nicht belegen.
- Validierte Ergebnisse stehen getrennt von Gespräch und Revision in `creative_runs` (SQLite-Migration 2 → 3). Gespeichert werden Aufgabenstellung, Projekt-/Varianten-/Ausgangsrevision, Modellkennung, Kontextmanifest mit Karten-IDs und Versionen, Kandidaten, optionale Reflexion sowie verfügbare Laufzeit- und Tokenwerte. Fehlerhafte Generierung oder Reflexion wird nicht gespeichert; es erfolgt nie eine automatische Kanonänderung.
- `stage_candidate(run_id, candidate_id)` ist ein bewusster Auswahlschritt: er kopiert Titel, Prämisse und Mechanismus eines gespeicherten Kandidaten in einen SF-001-Entwurf auf dessen Ausgangsrevision. Erst `Memory.approve(..., explicit_approval=True)` kann diesen übernehmen. Veraltete Ausgangsrevisionen werden abgelehnt. Die ausführlicheren Felder bleiben im kreativen Ergebnis erhalten.

## Ergebnisvertrag

Jeder `Stoffkeim` hat eine stabile Ergebnis-ID sowie `title`, `premise`, `narrative_promise`, `mechanism`, `mechanism_card_id` (Karten-ID oder `null`), `central_mystery` (Text oder `null`), `personal_conflict`, `development`, `audio_potential`, `fictional_assumptions`, `research_questions`, `weaknesses` und `used_card_ids`. Freitextfelder außer dem optionalen Geheimnis sind nicht leer; Listen müssen vorhanden sein und dürfen bei nicht zutreffenden Punkten leer sein. Die Modellantwort enthält `base_revision_id` und eine Kandidatenliste. `Reflexion` enthält nicht leere Listen `strengths`, `risks` und `questions`; sie verändert keinen Stoffkeim.

Beispiel ohne Modellinstallation mit einem synthetischen Projekt: `FakeProvider` erhält eine JSON-Antwort nach diesem Vertrag. Für einen realen Modelltest siehe unten. Die kreative Qualitätsbewertung benötigt eine gesonderte redaktionelle Sichtung.

## Tests und Dateien

`python -m pytest -q`: **57 bestanden**, einschließlich aller bisherigen 44 Tests. Neue Fake-Provider-Tests prüfen produktive Karten, Stoffkeime ohne Skript, unterschiedliche Kartenausgangspunkte, Kontextmanifest, unverbindliche Persistenz, Fallback einschließlich leerer Bibliothek, optionale Reflexion, ungültige Antworten und Karten-IDs, Timeout/Abbruch, Projektisolation, Autorenentscheidungen, veraltete Entwürfe und Migration. Es wurde **kein echtes Ollama-Modell** in diesen automatisierten Tests aufgerufen; auf der Prüfmaschine ist Ollama nicht installiert. Ein echter kreativer Qualitätstest wurde nicht durchgeführt.

Neu: `src/storyforge/stoffschmiede.py`, `tests/test_stoffschmiede.py`, diese Datei. Geändert: `src/storyforge/dialogue.py` (JSON-Schema ohne automatische Gesprächspersistenz), `src/storyforge/memory.py` (kreative Läufe), `src/storyforge/__init__.py`, `tests/test_memory.py`, `tests/test_dialogue.py`, `README.md`, `AGENTS.md`. Produktive Karten aus LIB-001 wurden nicht verändert.

## Optionaler kreativer Ollama-Test unter Windows

In PowerShell im Repository eine lokale Ollama-Installation starten und einen verfügbaren Modellnamen aus `ollama list` wählen. Ohne lokal verfügbares Modell erfordert `ollama pull <modellname>` einen Download. Anschließend:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e ".[test]"
$env:STORYFORGE_MODEL = "<installierter-modellname>"
@'
import os
from storyforge import Memory, NarrativeLibrary, OllamaProvider, Stoffschmiede

memory = Memory("local/stoffschmiede-smoke.sqlite3")
project = memory.create_project("Synthetischer Hörspieltest")
branch = memory.list_branches(project.id)[0]
library = NarrativeLibrary.load("library/cards")
forge = Stoffschmiede(memory, OllamaProvider(os.environ["STORYFORGE_MODEL"]), library)
run = forge.develop(project.id, branch.id,
                    "Entwickle drei Hörspielansätze um ein rätselhaftes Geräusch.",
                    count=3, reflect=False)
for seed in run.candidates:
    print(seed.title, "–", seed.mechanism, "–", seed.mechanism_card_id)
print("Karten:", run.manifest["cards"])
print("Revisionskopf unverändert:", memory.list_branches(project.id)[0].head_id == branch.head_id)
'@ | .venv\Scripts\python -
```

Der Smoke-Test nutzt nur synthetische lokale Projektdaten. Je nach Modell kann die strenge Strukturvalidierung eine Antwort ablehnen; das ist ein sichtbarer Modellbefund, kein Kanonwechsel. Für eine qualitative Bewertung Kandidaten redaktionell mit gewöhnlichem Chat und vergleichbarem Aufwand vergleichen. Der Test wurde hier nicht ausgeführt.

## Offene Fragen

- Exakte Schlagwörter und je eine Anfangskarte pro Kategorie sind ein bewusst einfacher Auswahlmechanismus. Kreative Eignung der Auswahl und echte Mechanismusvielfalt müssen mit Autorinnen und Autoren geprüft werden.
- Bei einer fehlgeschlagenen optionalen Reflexion wird der gesamte unverbindliche Lauf nicht gespeichert; ein erneuter Aufruf ist nötig. Eine spätere Oberfläche kann eine getrennte Speicherauswahl anbieten.
- Die Übernahme eines Kandidaten reduziert ihn auf das vorhandene SF-001-Ideenformat. Ob zusätzliche Felder verbindlich werden sollen, ist eine spätere fachliche Entscheidung.
- SF-003C und SF-003D bleiben separate Aufträge. Kein Push oder Release in SF-003B.
