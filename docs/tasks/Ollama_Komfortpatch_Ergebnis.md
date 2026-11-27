# Ollama-Komfort-Patch – Ergebnis und alpha.2-Vorbereitung

## Ablauf

Der Windows-Launcher startet weiterhin die lokale Python-Anwendung. Vor dem Browserstart fragt `OllamaService` ausschließlich `127.0.0.1:11434/api/tags` ab. Antwortet Ollama, verwendet STORYFORGE die vorhandene Instanz und übernimmt keinen Prozessbesitz. Sonst sucht es `ollama` im `PATH` und unter den üblichen Windows-Installationspfaden, startet `ollama serve` mit `CREATE_NO_WINDOW` und ohne umgeleitete Konsolenausgabe, wartet höchstens 20 Sekunden auf die Modellliste und zeigt bei Fehlern eine verständliche Meldung. Projektverwaltung und Export bleiben ohne Ollama nutzbar.

Der sichtbare Knopf **STORYFORGE beenden** sendet `POST /api/shutdown` an den lokalen Server. Laufende Hintergrundaufträge erhalten ein Abbruchsignal; Uvicorn fährt herunter. Im `finally` des Startpunkts wird ausschließlich der von STORYFORGE gehaltene `Popen`-Prozess beendet. Wenn eine andere Instanz im Startrennen den Port übernimmt, wird kein Prozessbesitz beansprucht. Der Server bindet weiterhin nur an `127.0.0.1`; die bestehenden Host-, Origin- und CSP-Regeln gelten auch für den Beenden-Endpunkt. Es gibt keine externe Datenübermittlung und keine Telemetrie.

Die kreativen Verfahren V01–V05, Pilot und Revisions-/Freigabelogik wurden nicht geändert. Die Modellliste wird beim Start und bei „Modelle erneut suchen“ abgefragt.

## Dateien

- `src/storyforge/web/ollama_service.py`: lokaler Status, Installationserkennung und Prozesslebensdauer.
- `src/storyforge/web/__main__.py`, `app.py`: Start, Beenden-Endpunkt und Modellstatus.
- `src/storyforge/web/static/index.html`, `app.js`: Beenden-Knopf und verständliche Ollama-Meldung.
- `tests/test_ollama_service.py`: Prozessbesitz, Fehler, Timeout, Windows-Startflags und lokale Route.
- `pyproject.toml`, `README.md`, `WINDOWS_KURZANLEITUNG.txt`, `scripts/build_sf004_zip.py`: Versions- und Distributionsunterlagen.
- `docs/releases/STORYFORGE_0.1.0-alpha.2.md`: vorbereitete Release Notes.
- `downloads/STORYFORGE-0.1.0-alpha.2-Windows.zip`: vorbereitete Testdistribution.

## Prüfungen

- `python -m pytest -q`: 117 bestanden unter Linux; Fake-Provider und Prozessdoubles, ohne Ollama/GPU.
- `node --check` für `app.js` und Python-Bytecodeprüfung erfolgreich.
- Lokaler Uvicorn-Prozess mit synthetischer temporärer Datenbank gestartet; fehlendes Ollama wurde gemeldet; `POST /api/shutdown` beendete den Prozess mit Exitcode 0.
- ZIP auf Integrität geprüft, entpackt und daraus den lokalen Server gestartet und beendet. Enthalten sind 59 Wissenskarten, sechs Pilotfälle, zwei Logos, Launcher und deutschsprachige Anleitungen. Das ZIP enthält keine lokale Projektdatenbank.
- Tatsächlicher Windows-Start, ein realer Ollama-Prozess und Modellläufe konnten in dieser Linux-Umgebung nicht geprüft werden. Kreative Qualität ist nicht nachgewiesen.

## Offene praktische Prüfungen

Auf dem Autoren-PC Launcher und Beenden-Knopf unter Windows mit bereits laufendem sowie selbst gestartetem Ollama prüfen. Dabei kontrollieren, dass nur ein selbst gestarteter Prozess beendet wird und `CREATE_NO_WINDOW` kein zusätzliches Konsolenfenster öffnet. Für alpha.2 sind Tag, GitHub-Release und Push noch nicht erfolgt.
