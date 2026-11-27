# SF-005 – Ergebnis: Vorbereitung des kreativen Qualitätspiloten

## Verfahren

Die Testfälle `pilot/cases/T01.json` bis `T06.json` sind synthetisch und einzeln versioniert. T01–T05 verlangen je drei Stoffansätze, T06 eine gezielte Mutation mit zwei geschützten Elementen. Für einen Vergleich wird ein Modell mit festen Parametern (`temperature`, `num_predict`) und einer wählbaren Wiederholungszahl 1–5 gespeichert. A, B und C können einzeln gestartet werden. Pro Lauf wird exakt ein Modellaufruf ohne optionale Reflexion geplant. A und B benutzen pro Fall denselben strukturierten Antwortvertrag wie C; B erhält eine begrenzte Auswahl produktiver Wissenskarten, C nutzt V02 (T01–T05) beziehungsweise V04 (T06). Die Vorgaben der vorhandenen Verfahren können den tatsächlichen Prompt und die Ausgabelänge beeinflussen; Tokenwerte und Zeichenlängen stehen deshalb im Bericht. Ein identisches generiertes Tokenvolumen ist nicht garantiert.

Die Kartenauswahl erfolgt über die bestehenden Selektoren. Das Manifest enthält den Kernkontext und die **tatsächlich übermittelten Modellnachrichten einschließlich JSON-Schema**, Karten-IDs und Versionen. Modellname, Parameter, Aufrufzahl, optionale Reflexionsaufrufe (hier 0), Wandzeit, verfügbare Modelllaufzeit und Tokenzahlen werden je Lauf gespeichert. Fehler und Abbrüche bleiben mit Status und Fehlermeldung nachvollziehbar. Kein externer Dienst und keine Telemetrie; der Standardprovider spricht nur lokales Ollama an.

## Bedienung

Windows: `Start_Storyforge.bat` starten, unter **Einstellungen** die **Optionale Testwerkstatt** öffnen. Ein installiertes lokales Ollama-Modell wählen, Testfall, Wiederholungen, Temperatur und Ausgabelimit einstellen und **Vergleich anlegen**. A, B und C mit gewünschter Wiederholungsnummer einzeln starten. Die Anzeige kann während eines Modelllaufs bedient werden; **Abbrechen** signalisiert den Abbruch. Ergebnisse erscheinen mit zufälligen Kennungen und ohne Methodenname. Je Kriterium sind 1–5 oder „Nicht zutreffend / überspringen“ möglich. Nach der Bewertung aller fertigen Ergebnisse kann die Zuordnung aufgelöst werden. JSON- und Markdown-Export sind vorher verblindet und danach mit Methoden, Manifesten und Metriken möglich.

Das Startskript installiert bei der Ersteinrichtung Python-Abhängigkeiten; Ollama und Modelle werden nicht mitgeliefert. `scripts/build_sf004_zip.py` nimmt die sechs Fälle zusätzlich zur bestehenden Windows-Testdistribution auf. Der normale Projektbereich und die fünf Autorenverfahren bleiben unverändert.

## Daten und Schnittstellen

- `PilotLab(database, provider_factory, cases=..., cards=...)`: separater Pilotspeicher. Der Provider-Factory-Vertrag lautet `(model: str, parameters: dict) -> ModelProvider`.
- `PilotConfig`: `case_id`, `model`, `temperature` (0–2), `num_predict` (128–4096), `repetitions` (1–5).
- `create_group`, `execute(group_id, arm, repetition, cancel)`, `blind_runs`, `rate`, `report(reveal=False)`, `markdown(reveal=False)` bilden den Pilotablauf.
- `PilotRating`: sieben optionale Kriterien mit Werten 1–5 und freie Anmerkungen.
- HTTP: `/api/pilot/cases`, `/api/pilot/groups`, `/api/pilot/groups/{id}/runs`, `/blind`, `/report`, `/export/{json|markdown}` sowie `/api/pilot/ratings/{blind_id}`. Die Methodenauflösung wird verweigert, solange ein fertiges Ergebnis unbewertet ist.
- Die Tabellen `groups`, `runs`, `ratings` liegen in `local/storyforge-pilot.sqlite3`; ein getrennter Pilot-Kern liegt in `local/storyforge-pilot-core.sqlite3`. Beide Dateien sind von der normalen Projektdatei getrennt und durch `.gitignore` vom Commit ausgeschlossen. Ein Vergleich speichert den vollständigen Testfall als Snapshot mitsamt Version, sodass spätere Änderungen an der Testbibliothek alte Berichte nicht verfälschen. Modell, Aufgabe und Parameter sind im Gruppenbericht enthalten. Laufdaten umfassen Status, vollständige strukturierte Kandidaten, Kontextmanifest, Metriken und Fehler. Bewertungen sind an die zufällige Ergebniskennung gebunden.

Die Auswertung ist bewusst beim Autor: kein Mittelwert, kein Siegeralgorithmus, keine Behauptung objektiver Kreativität. Ein A/B/C-Vergleich ist nur für dieselbe Gruppe und Modellkonfiguration sinnvoll. Die zufällige Reihenfolge der gestarteten Ergebnisse verschleiert die Methodenkennung in der Bewertungsansicht; wer die Läufe selbst startet, kann deren Reihenfolge erinnern. Für eine streng verblindete Studie sollte eine zweite Person die Läufe vorbereiten oder eine getrennte Sitzung zur Bewertung genutzt werden.

## Tests und Einschränkungen

Automatisierte Tests verwenden ausschließlich `FakeProvider`. Sie prüfen alle sechs Fallverträge, A/B/C-Kontext und Kartenmanifest, Ergebnisanzahl, Einzelprüfung geschützter Elemente, Verblindung und Auflösung, Export, vollständigen Prozessneustart, Testfall-Snapshot bei einer Bibliotheksänderung, Trennung vom Produktivspeicher, Modellfehler, Timeout, Abbruch und lokale HTTP-Schnittstellen. `python -m pytest -q`: **107 bestanden** (102 bestehende und 5 neue Tests), eine Deprecation-Warnung aus der TestClient-Abhängigkeit. Die Windows-ZIP wurde mit sechs Fällen neu gebaut und ihr Inhalt geprüft.

Geänderte Dateien: `AGENTS.md`, `README.md`, `WINDOWS_KURZANLEITUNG.txt`, `scripts/build_sf004_zip.py`, `downloads/Storyforge-SF004-Windows-Test.zip`, `src/storyforge/web/app.py`, `src/storyforge/web/static/{index.html,style.css}`. Neu: `pilot/cases/T01.json` bis `T06.json`, `src/storyforge/pilot.py`, `src/storyforge/web/static/pilot.js`, `tests/test_pilot.py`, `docs/tasks/SF-005_{Auftrag,Ergebnis}.md`.

Ein echter Ollama-Lauf, ein Windows-Test, eine manuelle Browserprüfung und eine Bewertung kreativer Qualität wurden hier **nicht** durchgeführt. Der HTTP-TestClient prüfte die lokale Testwerkstatt ohne Browser. Die technische Funktionsfähigkeit eines Fake-Laufs belegt keinen kreativen Mehrwert. Die Grenzen des Vergleichs bleiben die nicht garantierte gleiche Tokenzahl und die Möglichkeit, dass ein Autor bei selbst gestarteten Läufen die Methodenreihenfolge kennt. F09 ist im bereinigten Repository nicht vorhanden; der konkrete SF-005-Auftrag bildet die verfügbare Spezifikation.

## Offene Fragen

- Auf dem Autoren-PC: Ist das gewählte lokale Modell für alle drei Verfahren und JSON-Schemas zuverlässig genug?
- Soll die spätere reale Bewertung durch eine zweite Person vorbereitet werden, um Erinnerung an die Startreihenfolge auszuschließen?
- Welche qualitative Auswertung der Autorenanmerkungen ist nach dem realen Pilot angemessen, ohne eine automatische Kreativitätsnote zu behaupten?
