# Erster praktischer Autoren-Test – SF-005

Diese Anleitung dient dem **späteren echten Test auf dem Autoren-PC**. Die bisherigen automatisierten und Browser-Tests verwendeten ausschließlich synthetische Daten und simulierte Modellantworten.

1. Windows-Test-ZIP vollständig entpacken. Python 3.10+ muss über `py` verfügbar sein. Lokal Ollama starten und ein installiertes Modell bereithalten. Ollama und das Modell sind nicht im ZIP enthalten.
2. `Start_Storyforge.bat` doppelklicken. Beim ersten Start werden Python-Abhängigkeiten installiert. Im Browser `http://127.0.0.1:8765` öffnen; in der Kopfzeile muss das lokale Modell auswählbar sein.
3. Unter **Einstellungen → Optionale Testwerkstatt** einen synthetischen Fall wählen, zunächst **T01**. Modell, Temperatur, Ausgabelimit und Wiederholungen einstellen und **Vergleich anlegen**. Diese Einstellungen gelten für A, B und C derselben Gruppe.
4. A, B und C mit derselben Wiederholungsnummer einzeln starten. Auf das Ende jedes Laufs warten. Bei Fehler oder Abbruch Status und Fehlermeldung notieren. Für einen neuen Versuch einen neuen Vergleich anlegen.
5. Erst nach den gewünschten Läufen **Verblindete Bewertung beginnen** wählen. Danach zeigt die Oberfläche für diese Gruppe keine Methodenwahl mehr; weitere Läufe erfordern einen neuen Vergleich. Ergebnisse stehen in zufälliger Reihenfolge. Jedes Kriterium mit 1–5 bewerten oder **Nicht zutreffend / überspringen** wählen. Freie Anmerkungen ergänzen. Eine einzelne selbst gestartete Methode ist nicht wirksam verblindet; für einen faireren A/B/C-Vergleich sollte eine andere Person die Läufe vorbereiten.
6. Nach dem Speichern aller Bewertungen **Verfahren nach Bewertung auflösen**. JSON und Markdown exportieren. Die Berichte enthalten die Modellkonfiguration sowie nach der Auflösung Kontext, Kartenversionen, Aufrufzahl und verfügbare Laufzeit- und Tokenwerte.

Die Pilotdaten liegen getrennt von Geschichtenprojekten in `local/storyforge-pilot.sqlite3` und `local/storyforge-pilot-core.sqlite3`. Beide Dateien lokal sichern und nicht ins öffentliche Repository legen. Zunächst nur die mitgelieferten synthetischen Fälle verwenden. Die Bewertung ist ein Autorenurteil; STORYFORGE berechnet keinen Kreativitätssieger.
