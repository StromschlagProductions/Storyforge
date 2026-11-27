# Vorbereitete Release Notes – STORYFORGE 0.1.0-alpha.1

**Status:** Versionsbezeichnung vorbereitet. Noch kein GitHub Release erstellt.

STORYFORGE ist eine lokale deutschsprachige Hörspiel-Autorenwerkstatt. Projekte können ohne Skript beginnen. Projektgedächtnis, Varianten, Revisionen und Autorenentscheidungen liegen lokal in SQLite. Änderungen am verbindlichen Geschichtenstand benötigen eine ausdrückliche Freigabe.

Die Autorenoberfläche bietet Gespräch (V01), Stoffschmiede (V02), Geheimnislabor (V03), narrative Mutation (V04) und kritisches Lektorat (V05). Die 59 versionierten Wissenskarten können im Modellkontext als Anregungen dienen. Die Verfahren nutzen lokale Ollama-Modelle; ein Modell wird nicht mitgeliefert. Classic Hell und Classic Dunkel verwenden lokale Bildressourcen. Projekte lassen sich als JSON und Markdown exportieren.

SF-005 ergänzt eine **optionale** Testwerkstatt mit sechs synthetischen Fällen, A/B/C-Vergleich, verblindeter Autorenbewertung, getrenntem Pilotspeicher und JSON-/Markdown-Berichten. Die Windows-Testdistribution enthält Programmdateien, Wissenskarten, Pilotfälle und Kurzanleitungen.

## Voraussetzungen und bekannte Grenzen

- Windows-Zielplattform: Python 3.10+; für kreative Modellläufe lokal gestartetes Ollama mit installiertem Modell. Die Erstinstallation der Python-Abhängigkeiten benötigt Internetzugang.
- Keine Cloud-Dienste, kein externes CDN und keine Telemetrie; der lokale Server bindet an `127.0.0.1`.
- Der reale Windows-Start, echte Ollama-Modellläufe und die kreative Autorenbewertung stehen aus. Technische Fake- und HTTP-Stub-Tests sind kein Nachweis kreativer Qualität.
- Die Methoden können sich trotz gleicher Modellparameter und Ausgabetoken-Grenze im tatsächlichen Promptumfang und in der generierten Tokenzahl unterscheiden. Der Pilot protokolliert diese Unterschiede. Wer die Läufe selbst vorbereitet, kann Methoden aus der Startreihenfolge erinnern.
- F09 ist im öffentlichen bereinigten Repository nicht enthalten. Ein P0-Nutzenurteil setzt die spätere praktische Autorenbewertung voraus.

## Release-Entscheidung

Die Version ist als Alpha-Teststand vorbereitet. Ein GitHub Release oder Tag wird mit diesem Abschluss nicht erstellt.
