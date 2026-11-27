# SF-004 – Erste lokale Autorenoberfläche

Stand: 27.11.2026. Ausgangsstand `109e35e`. Ausschließlich SF-004 umgesetzt; kein SF-005.

## Start unter Windows

1. Python 3.10 oder neuer installieren und bei der Installation `py` aktivieren. Für die erste Einrichtung ist Internetzugang zum Bezug der Python-Pakete erforderlich; der spätere Betrieb lädt keine Webressourcen nach.
2. Das Repository lokal ablegen und `Start_Storyforge.bat` doppelklicken. Der Launcher erstellt bei Bedarf `.venv`, installiert STORYFORGE und öffnet `http://127.0.0.1:8765` im Standardbrowser. Die Konsole während der Nutzung offen lassen; Schließen beendet den lokalen Server.
3. Für Modellfunktionen Ollama separat lokal starten und ein bereits installiertes Modell bereithalten (`ollama list`). STORYFORGE erkennt lokale Modelle und zeigt den Verbindungsstatus. Ohne Ollama sind Projektakte, Varianten und Export nutzbar; kreative Modellaufrufe melden den fehlenden Modellstatus.
4. Projektdatei: `local/storyforge.sqlite3`. Das Verzeichnis ist von Git ausgeschlossen. Theme und zuletzt gewähltes Modell werden in diesem Browser gespeichert.

Unter Linux/macOS: `python -m venv .venv`, `.venv/bin/python -m pip install -e ".[test]"`, dann `.venv/bin/python -m storyforge.web`. Der Server bindet ausschließlich an `127.0.0.1`. Der Port lässt sich mit `--port` ändern.

## Architektur und Arbeitsablauf

`storyforge.web.app.create_app(database, library, provider_factory)` stellt eine schmale FastAPI-Brücke zum bestehenden Python-Kern bereit. Die Oberfläche verwendet lokale HTML-, CSS-, JavaScript- und Bilddateien. Es gibt weder CDN noch Telemetrie oder Cloud-Anbindung. Lokale HTTP-Anfragen werden auf Loopback-Host und gleiche Herkunft begrenzt; eine Content Security Policy verhindert fremde Skripte und ausführbare Inhalte. Modell- und Nutzertexte werden mit `textContent` ausgegeben, nicht als HTML interpretiert.

Projekte und Varianten verwenden `Memory`; Gespräch, Stoffschmiede, Geheimnislabor, Mutation und Kritik rufen `Dialogue`, `Stoffschmiede`, `Geheimnislabor` beziehungsweise `Autorenredaktion` auf. Die 59 Wissenskarten werden intern geladen und vom Kern begrenzt ausgewählt. Hintergrundaufträge laufen in einem kleinen Thread-Pool. Die Oberfläche zeigt „Modell arbeitet …“, kann abbrechen und bindet jedes Ergebnis an die bei Auftragsbeginn gewählten Projekt- und Varianten-IDs. Bei einem Wechsel wird ein späteres Ergebnis nicht in der anderen Projektansicht angezeigt.

V04/V05 akzeptieren freie Beschreibung, bestätigte Idee, einen gespeicherten Creative Run oder einen einzelnen gespeicherten V02-Stoffkeim als Quelle. `Quelle.candidate_id` wählt einen einzelnen Keim; fremde oder veraltete Run-/Keim-IDs werden abgelehnt. Die Projektakte zeigt bestätigte Ideen, Entscheidungen, Revisionshistorie, alle gespeicherten Ergebnisse und offene Entwürfe. Ein V02-Stoffkeim kann als SF-001-Entwurf vorgemerkt werden. Der Entwurf lässt sich vor der Freigabe aufklappen. Erst die ausdrücklich benannte Freigabe über `Memory.approve` ändert den Revisionskopf. Für komplexe V03–V05-Ergebnisse wird keine verkürzte Übernahme angeboten. JSON und Markdown werden aus dem bestehenden `Memory`-Export bereitgestellt.

## Gestaltung und Browserprüfung

Die Classic-Oberflächen aus Spatial Lab waren die primäre Referenz. Ergänzend wurden Screenshots von Stromscore, Dreamcatcher und Tumult betrachtet. Spatial Labs `ClassicTheme.h` definiert die Panel-/Rahmen-/Typografierichtung; dessen kräftiges Orange wurde gemäß SF-004-Korrektur durch matte Messing-/Sandgoldtöne ersetzt. `logo-dunkel.png` und `logo-hell.png` sind unveränderte Originalressourcen aus `SpatialLab-vst/docs/`, lokal mitgeliefert. Beide Themes verwenden dieselben Ansichten und Dialoge. Die Auswahl wird über `localStorage` beim Neuladen wiederhergestellt.

Die Anwendung wurde mit Chromium auf Linux tatsächlich geöffnet. Projektwechsel zwischen zwei synthetischen Werken, Stoffschmiede, Projektakte, Theme-Wechsel und das vollständig strukturierte Geheimnislabor-Ergebnis wurden im Browser geprüft; keine JavaScript-Laufzeitfehler traten auf. Screenshots mit ausschließlich synthetischen Projektdaten liegen unter `docs/screenshots/`: Startansicht, Stoffschmiede, Projektakte und Geheimnislabor jeweils in Classic Dunkel und Classic Hell. Das Geheimnislabor-Ergebnis im Screenshot stammt aus einer **simulierten Browserantwort**, nicht aus einem realen Modelllauf. Der Browser prüfte den vollständigen Matrix-Renderweg; der Python-Integrationstest prüfte die Backend-Verbindung mit Fake-Provider. In der Abschlussprüfung wurden alle sieben Ansichten in beiden Themes, Theme-Persistenz nach Neuladen, Dialogfarben beider Themes, Projektwechsel, eine Breite von 600 Pixeln ohne horizontales Überlaufen und die Textdarstellung einer HTML-artigen Modellantwort ohne Bild-/Skriptausführung erneut in Chromium geprüft.

## Windows-Testdistribution

`downloads/Storyforge-SF004-Windows-Test.zip` ist ein einfacher ZIP-Ordner ohne Installer. Enthalten sind `Start_Storyforge.bat`, `WINDOWS_KURZANLEITUNG.txt`, `pyproject.toml`, der Python-Kern und die Browserdateien, beide lokalen Original-Logos und genau 59 produktive Wissenskarten. Weder `.venv`, Ollama, Sprachmodelle noch lokale Projektdaten sind enthalten. `scripts/build_sf004_zip.py` erzeugt das Archiv aus einer festen Dateiauswahl; automatisierte Tests prüfen den Inhalt und starten den entpackten Python-Kern auf der jeweiligen CI-Plattform. Nach dem Entpacken wurde die enthaltene Anwendung unter Linux mit vorhandener Test-Python-Umgebung gestartet, statische Ressourcen geladen und ein synthetisches Projekt angelegt. Dies ersetzt keinen echten Windows-Start. Voraussetzungen: Windows 10/11, Python 3.10+ mit `py` und Internet für die erste Paketinstallation; Ollama ist nur für Modellfunktionen optional.

## Akzeptanzprüfung

1. Windows-Launcher vorhanden; ein tatsächlicher Windows-Start konnte in der Linux-Entwicklungsumgebung nicht ausgeführt werden.
2. Projekte erstellen/öffnen und Varianten wählen: Backend-Integration sowie Browserbedienung geprüft.
3. V01–V05 sind an die bestehenden Python-Verfahren angeschlossen und mit Fake-Provider durchlaufen.
4. Strukturierte Ergebnisse werden vollständig als Textfelder, Listen und bei V03 als lesbare Hypothesenmatrix ausgegeben.
5. Gespeicherte Creative Runs und einzelne V02-Stoffkeime können V04/V05 als Quelle dienen.
6. SQLite-Daten bleiben nach erneutem Öffnen erhalten; bestehende Kerntests prüfen auch Prozessneustarts.
7. Verbindliche Übernahme benötigt einen Entwurf und `explicit_approval=True`; negative Freigabe wird HTTP 403.
8. Lokale Ollama-Modelle und Offline-Status werden angezeigt; Statusantworten wurden automatisiert simuliert.
9. Hintergrundaufträge blockieren die API nicht, sind abbrechbar und zeigen keine erfundenen Prozente.
10. Projekt-/Varianten-IDs werden vor Aufruf und bei Quellen geprüft; Ergebnisse werden bei Projektwechsel nur ihrem Ausgangskontext zugeordnet.
11. JSON-/Markdown-Export wurde über HTTP getestet.
12. Alle bisherigen 94 Tests bestehen.
13. Neue FastAPI-Integrations- und Bedienpfadtests wurden ergänzt, einschließlich Projekt-/Varianten-Neustart und einzelner Stoffkeimquelle.
14. Automatische Tests benötigen weder Ollama noch GPU.
15. Beide Themes wurden im Browser und nach Neuladen geprüft; sämtliche Ansichten und Dialoge verwenden gemeinsame Farbvariablen.
16. Originales Stromschlag-Audio-Logo und abgestimmte Classic-Gestaltung sind umgesetzt.

`.venv/bin/python -m pytest -q`: **102 bestanden**. Ein Starlette-Hinweis zur TestClient-/httpx-Integration ist nicht testrelevant. Ein echter Ollama-Modelllauf fand nicht statt; ein tatsächlicher Windows-Test ist offen. Der Browserlauf erfolgte unter Linux/Chromium mit synthetischen Daten; beim dargestellten Mystery-Ergebnis wurde die Modellantwort simuliert. Die Offline-/Online-Ollama-Statusprüfung und V01–V05-Backendläufe verwendeten Testdoubles. Die technische Funktionsfähigkeit belegt keine kreative Qualität.

## Dateien und Grenzen

Neu: `src/storyforge/web/` (FastAPI, Launcher-Modul, lokale Oberfläche und zwei Original-Logos), `Start_Storyforge.bat`, `tests/test_web.py`, `docs/tasks/SF-004_Auftrag.md`, dieser Bericht und synthetische Screenshots unter `docs/screenshots/`. Geändert: `pyproject.toml`, `src/storyforge/memory.py` (lesende Listen), `src/storyforge/autorenredaktion.py` (einzelner Keim als Quelle), `README.md`, `AGENTS.md`.

Offen: Ein tatsächlicher Windows-Start und ein echter lokaler Ollama-Lauf auf dem Autoren-PC. Modellqualität, semantische Bewahrung geschützter Inhalte und kreative Originalität sind nicht durch Fake-Provider-Tests nachgewiesen. Der lokale Browser speichert Theme und Modellwahl pro Browserprofil; beim Wechsel des Profils beginnt diese Einstellung neu. Kein Release und kein Push in diesem Entwicklungsauftrag.

## CI-Korrektur der Abschlussprüfung

Der erste veröffentlichte CI-Lauf scheiterte unter Linux, weil der Kartenpfad aus dem Installationsort des Python-Pakets statt aus dem Startordner abgeleitet wurde; der Windows-Job wurde durch den fehlgeschlagenen Matrixjob abgebrochen. Der Kartenpfad wird nun aus dem Arbeitsordner des Launchers beziehungsweise des Tests geladen. Das ZIP wurde neu gebaut. Zusätzlich wurde eine reguläre Paketinstallation in ein getrenntes Verzeichnis geprüft: 59 Karten, Startseite und Logo waren erreichbar. Der erneute GitHub-Actions-Lauf ist für die endgültige Windows-/Linux-Aussage maßgeblich.
