# ALPHA 2 – Kreativer Arbeitsfluss und Gesprächsoberfläche

Ausgangsstand: lokaler Commit `9646529`. Ollama-Komfort-Patch und stabilisierte Modellkommunikation bleiben erhalten. STORYFORGE soll sich wie eine intuitive kreative Autorenwerkstatt anfühlen.

## Verbindlicher Umfang

- Vollständigen gespeicherten Gesprächsverlauf chronologisch anzeigen, Autor und KI optisch unterscheiden, Eingabe unten platzieren, mehrzeilig schreiben, Enter zum Senden und Umschalt+Enter für Zeilenumbrüche. Nur automatisch scrollen, wenn der Autor dem Gespräch folgt. Verlauf nach Projektwechsel und Neustart wiederherstellen.
- Modellantworten lokal und sicher als Markdown darstellen: Überschriften, Fett/Kursiv, Listen, Tabellen, Absätze, Zitate und Codeblöcke. Kein ausführbares HTML und keine CDN-Abhängigkeit.
- Echtes Ollama-Streaming für freie V01-Antworten: Teiltext sichtbar, Abbruch möglich, unvollständige Antworten kennzeichnen. Strukturierte Verfahren erst nach vollständiger Validierung anzeigen und speichern. Keine erfundenen Fortschrittswerte.
- Kontextbezogene Aktionen für geeignete Ergebnisse: im Gespräch vertiefen, Geheimnis untersuchen, Varianten entwickeln, kritisch prüfen und als Idee bewahren. Ausgewähltes Material automatisch übergeben; Gesprächsmaterial durch Quellenreferenz oder explizit gewählten Text. Keine automatische Kanonänderung.
- Redaktionell lesbare Ergebnisse mit deutschen Bezeichnungen, standardmäßig ohne technische IDs und mit einklappbaren Zusatzinformationen. Handlungsbezogene Schaltflächen. Während der Generierung Status, danach optionale Laufzeit-, Token- und Geschwindigkeitswerte.
- Bestehendes Stromschlag-Audio-Design, Original-Logo, Classic Hell/Dunkel und matte Messingakzente beibehalten.

## Prüfung und Abschluss

Alle 129 bisherigen Tests müssen bestehen. Tests für Streaming, Abbruch, Gesprächspersistenz, sichere Markdown-Darstellung, Projektisolation und Wiederverwendung ergänzen. Beide Themes im Browser prüfen und Screenshots mit synthetischen Daten erstellen. Windows-Testdistribution aktualisieren. Auftrag und Ergebnis dokumentieren. Lokaler Commit; kein Push, Tag oder Release. Keine neuen kreativen Engines oder P1-Funktionen.
