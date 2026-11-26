# STORYFORGE – P0 Codex-Auftragsplan
Jeweils nur einen freigegebenen Auftrag ausführen. Tests und kurze deutschsprachige Ergebnisdokumentation; keine Umfangserweiterung ohne Autorentscheidung. Aktuell SF-001.

## SF-001 – Projektgrundlage und lokales Projektgedächtnis
Python, SQLite, Migration, Pydantic, minimale Projekte, Werke, optionale Universen, Revisionen, Ideen und Entscheidungen. Referenz F08 und P0 im Masterplan. Akzeptanz: Projekt ohne Skript erstellen, speichern und nach Neustart öffnen; Varianten isoliert; Autorenentscheidungen dauerhaft; atomare explizite Autorfreigabe; veraltete Revision ablehnen; JSON/Markdown-Export; automatisierte pytest-Tests inklusive Neustart. Nicht-Ziele: LLM, GUI, Fade In, Saga-Graph, Dramaturgie. Repo prüfen, nichts überschreiben. Nur synthetische Testdaten. Ergebnis: Architekturentscheidungen, Dateien, Tests, offene Punkte, Empfehlungen SF-002. Lokaler Commit, kein Push/Release.

## SF-002 – Modelladapter und kreativer Dialog
Voraussetzung SF-001. Ollama und Fake-Provider, austauschbarer Vertrag für externe Anbieter; externe Anbindung erst nach Anbieterwahl. Kontextmanifest, Abbruch/Timeout, strukturierte Entwürfe, keine automatischen Kanonänderungen. Tests für gültige/ungültige Antworten, Offline-Fall und Providerfehler. Keine komplexen Agenten.

## SF-003 – Erste kreative Verfahren
Voraussetzung SF-002. V02 Stoffkeime, V03 Geheimnislabor, V04 gezielte Varianten, V05 Kritik. Redaktionell geprüfte versionierte Auswahl M/N/D/A-Karten aus F02–F07 vor Umsetzung bereitstellen. Technische Fake-Provider-Tests für unterschiedliche Stoffmechanismen, Hypothesen und geschützte Elemente; reale kreative Qualität separat. Keine vollständige automatische Narrative Engine.

## SF-004 – Minimale Autorenoberfläche
Voraussetzung SF-003. Lokale Browseroberfläche als Vorschlag: Projektwahl, Gespräch, Ideen/Varianten, Freigabe, Modellwahl, Export. Keine permanenten Warnungen oder Formularpflicht. Windows-Test, Neustart, Abbruch, Vergleich und Ablehnung. Externe Übermittlung nur bewusst.

## SF-005 – Qualitätspilot
Vergleichsprotokoll F09 vor Umsetzung in bereinigter Fassung bereitstellen. Verfügbare Modelle, anonymisierte Autorbewertung, Laufzeit/Kosten. A/B/C getrennt vom Modellvergleich. Keine automatische Siegerbehauptung. Ohne Mehrwert Verfahren reduzieren. Optional Textimport, Fade In gesondert. P1 erst nach P0-Nutzenentscheidung.
