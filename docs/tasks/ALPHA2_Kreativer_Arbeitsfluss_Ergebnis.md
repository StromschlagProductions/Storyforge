# ALPHA 2 – Kreativer Arbeitsfluss: Ergebnis

## Architektur und Bedienung

V01 verwendet jetzt `OllamaProvider.generate_stream` mit der lokalen Ollama-Chat-API (`stream: true`). Die NDJSON-Teile werden im bestehenden Hintergrundjob gesammelt und während der Generierung über dessen Status an die Browseransicht gegeben. Das Gespräch wird erst nach einem gültigen `done`-Abschluss atomar als Autor-/KI-Paar gespeichert. Abbruch, Timeout, ein unvollständiger Stream und ungültige Teile speichern keine Teilantwort; die Oberfläche markiert bereits sichtbaren Teiltext als **unvollständig und nicht gespeichert**. Die strukturierten Verfahren V02–V05 bleiben beim vollständigen, validierten Antwortweg.

Der Gesprächsendpunkt liefert alle gespeicherten Beiträge chronologisch. Die Oberfläche trennt Autor- und KI-Beiträge, setzt die mehrzeilige Eingabe unter den scrollbaren Verlauf und unterstützt Enter zum Senden sowie Umschalt+Enter für einen Zeilenumbruch. Beim Nachladen bleibt die Scrollposition erhalten, wenn der Autor ältere Beiträge liest. Projekt- und Variantenwechsel laden den jeweils eigenen Verlauf. Die unverbindliche Antwort bleibt vom bestätigten Geschichtenstand getrennt.

Ein kleiner lokaler Markdown-Renderer erzeugt ausschließlich erlaubte DOM-Knoten über `textContent` und `createTextNode`. Er unterstützt Überschriften, Hervorhebungen, Listen, Tabellen, Zitate, Absätze und Codeblöcke. Modell-HTML wird als Text gezeigt; weder `innerHTML` noch externe Skripte werden verwendet. Die bestehenden CSP- und Loopback-Regeln bleiben aktiv.

Gesprächsbeiträge und gespeicherte kreative Ergebnisse bieten kontextbezogene Anschlussaktionen. Gesprächsquellen werden über ihre ID projekt- und variantenbezogen sowie gegen die aktuelle Revision geprüft; für V04/V05 wird zusätzlich der exakt ausgewählte Text abgeglichen. Gespeicherte Creative Runs werden ebenfalls gegen Projekt, Variante, Revision und gegebenenfalls Kandidat geprüft. Ein geeigneter Stoffkeim kann über den bestehenden Entwurfsweg vorgemerkt werden. Für einen KI-Gesprächsbeitrag gibt es einen neuen **unverbindlichen** SF-001-Entwurf; nur `Memory.approve(..., explicit_approval=True)` ändert den Kanon. Das Modell löst keine Freigabe aus.

Ergebnisse zeigen deutsche Feldnamen, verbergen technische IDs im Normalfall und klappen ausführliche Zusatzfelder ein. Die fünf Verfahrensknöpfe benennen ihre jeweilige Aktion. V01 zeigt nach Abschluss verfügbare Antwortdauer, Ausgabetoken und Generierungsgeschwindigkeit in einem optionalen Bereich. Original-Logo, Classic Hell/Dunkel und matte Akzentfarben bleiben erhalten.

## Tests und Browserprüfung

`python -m pytest -q`: **138 bestanden** unter Linux. Neue Tests prüfen HTTP-Streaming mit mehreren Teilen, Abbruch und fehlenden Abschluss, sichtbare Teilantwort im Job ohne vorzeitige Persistenz, vollständigen Verlauf nach Neustart, Quellenisolation, veränderte und veraltete Gesprächsquellen, Wiederverwendung eines einzelnen Stoffkeims sowie Markdown-DOM ohne ausführbares Modell-HTML. Die bisherigen 129 Tests bleiben erfolgreich. Kein Ollama, keine GPU und kein privates Projekt sind für die Tests nötig.

Chromium unter Linux wurde mit ausschließlich synthetischer SQLite-Datenbank geprüft: Markdown mit Tabelle/Zitat/Codeblock, nicht ausgeführtes HTML, Anschlussaktion, Projektwechsel, Projektakte, Ansicht bei 750 px und Theme-Persistenz nach Neuladen. Ein zweiter Browserlauf mit Fake-Streaming zeigte Teiltext während der Generierung und die Markierung nach Abbruch; es wurde kein Gespräch gespeichert. Screenshots: `docs/screenshots/ALPHA2_gespraech-dunkel.png` und `docs/screenshots/ALPHA2_gespraech-hell.png`.

Ein realer Windows-Start und ein echter Ollama-/Gemma-Streaminglauf wurden in dieser Linux-Umgebung nicht ausgeführt. Die kreative Qualität wurde nicht bewertet.

Das aktualisierte alpha.2-ZIP wurde auf Prüfsumme und Inhalt geprüft, entpackt, daraus unter Linux lokal gestartet und über den Beenden-Endpunkt mit Exitcode 0 heruntergefahren. Es enthält 59 Wissenskarten, sechs Pilotfälle, beide Logos sowie die neuen lokalen Browserdateien.

## Dateien und offene Punkte

Geändert: `src/storyforge/providers.py`, `dialogue.py`, `memory.py`, `web/app.py`, `web/static/index.html`, `style.css`; neu: `web/static/markdown.js`, `workflow.js`, gezielte Tests, dieser Bericht, Auftrag und zwei synthetische Screenshots. Die Windows-Testdistribution und Prüfsumme wurden aktualisiert. Es wurden keine privaten Hörspielinhalte, Projektdatenbanken oder Zugangsdaten in Commit-Dateien aufgenommen.

Die Markdown-Untermenge ist bewusst klein; komplexe verschachtelte Markdown-Syntax wird als Text oder einfacher Absatz dargestellt. Teilantworten eines abgebrochenen Laufs sind nur bis zum Neuladen im Browser sichtbar. Ein realer Windows-/Ollama-Test sollte insbesondere das Streaming und das Verhalten bei langen Antworten prüfen. Kein Push, Tag oder Release.
