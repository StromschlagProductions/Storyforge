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

`.venv/bin/python -m pytest -q`: **60 bestanden**, einschließlich aller bisherigen 44 Tests. Neue Fake-Provider-Tests prüfen produktive Karten, Stoffkeime ohne Skript, unterschiedliche Kartenausgangspunkte, Kontextmanifest, unverbindliche Persistenz, Fallback einschließlich leerer Bibliothek, optionale Reflexion, ungültige Antworten und Karten-IDs, Timeout/Abbruch, Projektisolation, Autorenentscheidungen, veraltete Entwürfe und Migration. Es wurde **kein echtes Ollama-Modell** in diesen automatisierten Tests aufgerufen; auf der Prüfmaschine ist Ollama nicht installiert. Ein echter kreativer Qualitätstest wurde nicht durchgeführt. Die Promptprüfung bestätigt ausdrücklich kreative Freiheit: Karten sind Ausgangspunkte, ihre Felder, Prüffragen und Schwächen keine verpflichtenden Handlungselemente. Verschiedene Karten-IDs und Mechanismusbezeichnungen belegen technisch unterscheidbare Ausgangspunkte, nicht die erzählerische Qualität oder semantische Originalität der Ergebnisse.

Neu: `src/storyforge/stoffschmiede.py`, `tests/test_stoffschmiede.py`, diese Datei. Geändert: `src/storyforge/dialogue.py` (JSON-Schema ohne automatische Gesprächspersistenz), `src/storyforge/memory.py` (kreative Läufe), `src/storyforge/__init__.py`, `tests/test_memory.py`, `tests/test_dialogue.py`, `README.md`, `AGENTS.md`. Produktive Karten aus LIB-001 wurden nicht verändert.

## Abschlussprüfung der zwölf Akzeptanzkriterien

1. **Produktive Karten:** Alle 59 JSON-Karten werden vollständig geladen und validiert; M/N/D/A = 16/16/17/10, IDs und Querverweise gültig.
2. **Mehrere Stoffkeime:** Zwei bis fünf synthetische Keime werden mit Fake-Provider in einem Aufruf erzeugt und strukturell geprüft.
3. **Unterschiedliche Mechanismen:** Verschiedene ausgewählte Mechanismuskarten und eindeutige Mechanismusbezeichnungen werden erzwungen. Semantische Originalität bleibt redaktionell zu prüfen.
4. **Kartenauswahl:** Auswahl auf höchstens fünf Karten begrenzt, deterministisch und mit Auswahlgründen dokumentiert. Fehlende Schlagworttreffer führen zu gekennzeichnetem Fallback.
5. **Kontext und Manifest:** Übermittelte Karten-IDs/Versionen, Variante und Revision stimmen mit dem Manifest überein. Fremde Projekte und nicht gewählte Varianten sind ausgeschlossen.
6. **Keine erfundenen Karten:** Unbekannte, doppelte oder falsch zugeordnete Karten-IDs werden abgelehnt. Bei leerer Bibliothek sind nur `null` und leere ID-Listen zulässig.
7. **Optionale Reflexion:** Ohne `reflect` genau ein Modellaufruf; mit `reflect=True` genau ein zusätzlicher Aufruf. Ungültige Reflexion speichert keinen Lauf.
8. **Persistenz:** Ein separater Python-Prozess öffnet die SQLite-Datenbank erneut und liest alle Kandidaten sowie das Manifest unverändert.
9. **Isolation und Entscheidungen:** Projekt- und Variantenkontext bleiben getrennt; bestätigte Entscheidungen bleiben erhalten.
10. **Kontrollierte Übernahme:** Auswahl erzeugt nur einen Entwurf. Erst ausdrückliche Autorfreigabe übernimmt ihn.
11. **Fehler und Konflikte:** Ungültige Antwort, Timeout, Abbruch auch nach Modellantwort, falsche Ausgangsrevision und veralteter Entwurf ändern keinen Revisionskopf.
12. **Regression:** Alle **60** automatisierten Tests bestehen. Damit ist die technische Funktionsfähigkeit mit Fake-Provider belegt; die kreative Qualität ist nicht nachgewiesen.

## Direkt ausführbarer Ollama-Test unter Windows

Ollama lokal starten und mit `ollama list` den Namen eines **bereits installierten** Modells ablesen. In PowerShell im Repository:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe scripts\stoffschmiede_smoke.py --model "<installierter-modellname>"
```

Optional sind `--count 2` bis `--count 5`, `--reflect` und `--database <lokaler-pfad>`. Das Skript erstellt ausschließlich ein synthetisches Projekt, kontaktiert Ollama standardmäßig nur unter `127.0.0.1:11434`, gibt **sämtliche Felder jedes Stoffkeims** sowie ggf. die Reflexion lesbar aus und zeigt den unveränderten Revisionskopf. Die lokale SQLite-Datei unter `local/` ist ignoriert. Bei einem ungültigen JSON-Ergebnis meldet die Validierung einen Fehler; ein kanonischer Projektstand wird nicht verändert. `--help` wurde ausgeführt; ein echter Modelllauf war auf der Prüfmaschine ohne Ollama nicht möglich.

## Dateien und Sicherheitsprüfung

Neu in der Abschlussprüfung: `scripts/stoffschmiede_smoke.py`. Geändert: `src/storyforge/stoffschmiede.py`, `tests/test_stoffschmiede.py`, dieser Bericht. Die Tests prüfen zusätzlich Prozessneustart, tatsächliches Kartenmanifest, freie Promptformulierung, ungültige Mechanismuskartenzuordnung, Abbruch nach Antwort und vollständige Konsolenausgabe. Die Veröffentlichungsdateien enthalten nur Code, redaktionell bereitgestellte Karten, bereinigte Dokumentation und synthetische Testdaten; keine privaten Hörspielskripte, Projektdatenbanken oder Zugangsdaten.

## Offene Fragen

- Exakte Schlagwörter und je eine Anfangskarte pro Kategorie sind ein bewusst einfacher Auswahlmechanismus. Kreative Eignung der Auswahl und echte Mechanismusvielfalt müssen mit Autorinnen und Autoren geprüft werden.
- Bei einer fehlgeschlagenen optionalen Reflexion wird der gesamte unverbindliche Lauf nicht gespeichert; ein erneuter Aufruf ist nötig. Eine spätere Oberfläche kann eine getrennte Speicherauswahl anbieten.
- Die Übernahme eines Kandidaten reduziert ihn auf das vorhandene SF-001-Ideenformat. Ob zusätzliche Felder verbindlich werden sollen, ist eine spätere fachliche Entscheidung.
- SF-003C und SF-003D bleiben separate Aufträge. Kein Release in dieser Abschlussprüfung.
