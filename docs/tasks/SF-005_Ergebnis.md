# SF-005 – Ergebnis: Vorbereitung des kreativen Qualitätspiloten

## Verfahren

Die Testfälle `pilot/cases/T01.json` bis `T06.json` sind synthetisch und einzeln versioniert. T01–T05 verlangen je drei Stoffansätze, T06 eine gezielte Mutation mit zwei geschützten Elementen. Für einen Vergleich wird ein Modell mit festen Parametern (`temperature`, `num_predict`) und einer wählbaren Wiederholungszahl 1–5 gespeichert. A, B und C können einzeln gestartet werden. Pro Lauf wird exakt ein Modellaufruf ohne optionale Reflexion geplant. A und B benutzen pro Fall denselben strukturierten Antwortvertrag wie C; B erhält eine begrenzte Auswahl produktiver Wissenskarten, C nutzt V02 (T01–T05) beziehungsweise V04 (T06). Die Vorgaben der vorhandenen Verfahren können den tatsächlichen Prompt und die Ausgabelänge beeinflussen; Tokenwerte und Zeichenlängen stehen deshalb im Bericht. Ein identisches generiertes Tokenvolumen ist nicht garantiert.

Die Kartenauswahl erfolgt über die bestehenden Selektoren. Das Manifest enthält den Kernkontext und die **tatsächlich übermittelten Modellnachrichten einschließlich JSON-Schema**, Karten-IDs und Versionen. Modellname, Parameter, Aufrufzahl, optionale Reflexionsaufrufe (hier 0), Wandzeit, verfügbare Modelllaufzeit und Tokenzahlen werden je Lauf gespeichert. Fehler und Abbrüche bleiben mit Status und Fehlermeldung nachvollziehbar. Kein externer Dienst und keine Telemetrie; der Standardprovider spricht nur lokales Ollama an.

## Bedienung

Windows: `Start_Storyforge.bat` starten, unter **Einstellungen** die **Optionale Testwerkstatt** öffnen. Ein installiertes lokales Ollama-Modell wählen, Testfall, Wiederholungen, Temperatur und Ausgabelimit einstellen und **Vergleich anlegen**. A, B und C mit gewünschter Wiederholungsnummer einzeln starten. Die Anzeige kann während eines Modelllaufs bedient werden; **Abbrechen** signalisiert den Abbruch. Die Vorbereitung zeigt die Methodenwahl und noch keine Ergebnisse. **Verblindete Bewertung beginnen** blendet die Methodenwahl aus und zeigt Ergebnisse in zufälliger Reihenfolge mit zufälligen Kennungen. Je Kriterium sind 1–5 oder „Nicht zutreffend / überspringen“ möglich. Nach dem Ende aller gestarteten Läufe und der Bewertung aller fertigen Ergebnisse kann die Zuordnung aufgelöst werden. JSON- und Markdown-Export sind vorher verblindet und danach mit Methoden, Manifesten und Metriken möglich. Ein einzelner selbst gestarteter Lauf ist inhaltlich nicht wirksam verblindet.

Das Startskript installiert bei der Ersteinrichtung Python-Abhängigkeiten; Ollama und Modelle werden nicht mitgeliefert. `scripts/build_sf004_zip.py` nimmt die sechs Fälle und `SF-005_PILOT_KURZANLEITUNG.md` zusätzlich zur bestehenden Windows-Testdistribution auf. Der normale Projektbereich und die fünf Autorenverfahren bleiben unverändert.

## Daten und Schnittstellen

- `PilotLab(database, provider_factory, cases=..., cards=...)`: separater Pilotspeicher. Der Provider-Factory-Vertrag lautet `(model: str, parameters: dict) -> ModelProvider`.
- `PilotConfig`: `case_id`, `model`, `temperature` (0–2), `num_predict` (128–4096), `repetitions` (1–5).
- `create_group`, `execute(group_id, arm, repetition, cancel)`, `blind_runs`, `rate`, `report(reveal=False)`, `markdown(reveal=False)` bilden den Pilotablauf.
- `PilotRating`: sieben optionale Kriterien mit Werten 1–5 und freie Anmerkungen.
- HTTP: `/api/pilot/cases`, `/api/pilot/groups`, `/api/pilot/groups/{id}/runs`, `/blind`, `/report`, `/export/{json|markdown}` sowie `/api/pilot/ratings/{blind_id}`. Die Methodenauflösung wird bei fehlenden oder noch laufenden Ergebnissen und solange ein fertiges Ergebnis unbewertet ist verweigert.
- Die Tabellen `groups`, `runs`, `ratings` liegen in `local/storyforge-pilot.sqlite3`; ein getrennter Pilot-Kern liegt in `local/storyforge-pilot-core.sqlite3`. Beide Dateien sind von der normalen Projektdatei getrennt und durch `.gitignore` vom Commit ausgeschlossen. Ein Vergleich speichert den vollständigen Testfall als Snapshot mitsamt Version, sodass spätere Änderungen an der Testbibliothek alte Berichte nicht verfälschen. Modell, Aufgabe und Parameter sind im Gruppenbericht enthalten. Laufdaten umfassen Status, vollständige strukturierte Kandidaten, Kontextmanifest, Metriken und Fehler. Bewertungen sind an die zufällige Ergebniskennung gebunden.

Die Auswertung ist bewusst beim Autor: kein Mittelwert, kein Siegeralgorithmus, keine Behauptung objektiver Kreativität. Ein A/B/C-Vergleich ist nur für dieselbe Gruppe und Modellkonfiguration sinnvoll. Die zufällige Reihenfolge der gestarteten Ergebnisse verschleiert die Methodenkennung in der Bewertungsansicht; wer die Läufe selbst startet, kann deren Reihenfolge erinnern. Für eine streng verblindete Studie sollte eine zweite Person die Läufe vorbereiten. Die API ist lokal ohne Mehrbenutzerrollen; die Verblindung ist ein Bedienablauf, kein Schutz gegen absichtliches Nachsehen in der lokalen Datenbank.

## Tests und Einschränkungen

Automatisierte Tests verwenden ausschließlich `FakeProvider`. Sie prüfen alle sechs Fallverträge, A/B/C-Kontext und Kartenmanifest, identische Schemas und Modellparameter, Ergebnisanzahl, Einzelprüfung geschützter Elemente, zufällige und nach Neustart stabile Reihenfolge, Verblindung und Auflösung, Export, vollständigen Prozessneustart, Testfall-Snapshot bei einer Bibliotheksänderung, Trennung vom Produktivspeicher, Modellfehler, Timeout, Abbruch und lokale HTTP-Schnittstellen. `python -m pytest -q`: **109 bestanden** (102 bisherige und 7 Pilot-Tests), eine Deprecation-Warnung aus der TestClient-Abhängigkeit. Die Windows-ZIP wurde neu gebaut und **entpackt** geprüft: 59 Karten, sechs Fälle, beide Logos, Kurzanleitung und lokaler HTTP-Start aus dem entpackten Quellbaum. Das war kein Windows-Start.

Änderungen dieser Abschlussprüfung: `src/storyforge/pilot.py`, `src/storyforge/web/static/{index.html,pilot.js}`, `tests/test_pilot.py`, `pyproject.toml`, `scripts/build_sf004_zip.py`, `README.md`, `WINDOWS_KURZANLEITUNG.txt`, `docs/tasks/SF-005_Ergebnis.md`, die Windows-ZIP. Neu: `SF-005_PILOT_KURZANLEITUNG.md`, `docs/releases/STORYFORGE_0.1.0-alpha.1.md` und zwei Screenshots unter `docs/screenshots/`.

**Browserprüfung unter Linux:** Die lokale Oberfläche wurde mit synthetischem Projekt und einem lokalen HTTP-Stub für Ollamas Protokoll geöffnet. A, B und C wurden einzeln bedient; ein zunächst fehlerhafter Stub belegte die sichtbare Fehlerbehandlung, nach Korrektur lieferte C ein synthetisches Ergebnis. Projektanlage, Variantenwahl, regulärer V02-Lauf, Navigation zu V03–V05 und Projektakte sowie Classic Hell/Dunkel und Theme-Persistenz nach Neuladen wurden beobachtet. Nach der Trennung von Vorbereitung und Bewertung wurde die verblindete Ansicht nochmals im Browser geprüft: Methodenwahl verborgen, Ergebnis mit zufälliger Kennung sichtbar. Screenshots: `docs/screenshots/SF-005_testwerkstatt-dunkel.jpg` und `docs/screenshots/SF-005_testwerkstatt-hell.jpg`. Sie zeigen ausschließlich synthetische Daten.

Ein echter Ollama-Lauf, ein Windows-Start und eine Bewertung kreativer Qualität wurden hier **nicht** durchgeführt. Der Browser-Stub ist **kein echtes Ollama-Modell**; FakeProvider-Tests und HTTP-Stub-Antworten belegen keinen kreativen Mehrwert. Die Grenzen des Vergleichs bleiben die nicht garantierte gleiche Tokenzahl und die Möglichkeit, dass ein Autor bei selbst gestarteten Läufen die Methodenreihenfolge kennt. F09 ist im bereinigten Repository nicht vorhanden; der konkrete SF-005-Auftrag bildet die verfügbare Spezifikation.

## Abschlussprüfung der zehn Akzeptanzkriterien

| Nr. | Befund |
| --- | --- |
| 1 | Sechs synthetische JSON-Fälle T01–T06 mit stabiler ID und Version 1 vorhanden; T06 enthält zwei geschützte Elemente. |
| 2 | A, B und C pro Gruppe einzeln ausführbar; Browser-Stubs und FakeProvider prüfen den Ablauf. |
| 3 | Modell, Parameter, tatsächliche Nachrichten und JSON-Schema, Kartenversionen, Aufrufzahl, Laufzeit und verfügbare Tokenwerte im aufgelösten Bericht. |
| 4 | Vorbereitung und Bewertung sind in der Oberfläche getrennt; vor der Bewertung erscheinen keine Methoden in Ergebnissen oder verblindeten Exporten. Die praktische Blindheit braucht bei selbst gestarteten Läufen eine zweite Person. |
| 5 | Gruppen, Ergebnisse und Bewertungen aus getrenntem SQLite-Speicher nach vollständigem Prozessneustart geladen. |
| 6 | JSON und Markdown enthalten vollständige Kandidaten; aufgelöst zusätzlich Manifest und Metriken. |
| 7 | Pilotgruppen und Pilot-Kern in separaten Datenbanken; reguläre Projektakte und Revisionsköpfe unverändert. |
| 8 | Abbruch, Timeout, ungültige Antwort und Offline-Fehler ändern keinen verbindlichen Geschichtenstand; Status und Fehler bleiben gespeichert. |
| 9 | Alle 102 bestehenden Tests bleiben erfolgreich. |
| 10 | Neue Pilotfunktionen und wichtige Randfälle besitzen FakeProvider-Tests. |

## P0-Entwicklungsstand

SF-001 (Projektgedächtnis, Revisionen, Freigabe), SF-002 (Provider und Dialog), SF-003A/LIB-001 (59 Wissenskarten), SF-003B–D (V02–V05), SF-004 (lokale Autorenoberfläche) und die technische Vorbereitung SF-005 sind implementiert. Der P0-Kern erlaubt einen vertikalen kreativen Ablauf vom skriptlosen Projekt über Modellgespräch und Verfahren bis zur expliziten Autorfreigabe und zum Export. **Ein empirisches P0-Nutzenurteil liegt noch nicht vor.** Offen sind ein echter Windows-Start, reale lokale Ollama-Läufe auf dem Autoren-PC, die anonymisierte kreative Autorenbewertung A/B/C und die Entscheidung, welche Verfahren tatsächlich Mehrwert liefern. Die vorbereitete Bezeichnung `STORYFORGE 0.1.0-alpha.1` ist noch kein Release.

## Offene Fragen

- Auf dem Autoren-PC: Ist das gewählte lokale Modell für alle drei Verfahren und JSON-Schemas zuverlässig genug?
- Soll die spätere reale Bewertung durch eine zweite Person vorbereitet werden, um Erinnerung an die Startreihenfolge auszuschließen?
- Welche qualitative Auswertung der Autorenanmerkungen ist nach dem realen Pilot angemessen, ohne eine automatische Kreativitätsnote zu behaupten?
