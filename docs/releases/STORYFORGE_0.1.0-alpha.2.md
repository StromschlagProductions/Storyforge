# Vorbereitete Release Notes – STORYFORGE 0.1.0-alpha.2

**Status:** Release und Tag sind vorbereitet, aber noch nicht veröffentlicht.

Diese Alpha-Version ergänzt die bestehende lokale Autorenwerkstatt um eine automatische Ollama-Verwaltung. Beim Start prüft STORYFORGE den lokalen Ollama-Dienst, startet ihn bei Bedarf ohne zusätzliches Konsolenfenster, wartet auf Betriebsbereitschaft und zeigt die installierten Modelle. Eine fehlende Installation wird verständlich gemeldet; Projektverwaltung und Export bleiben nutzbar. Der neue Knopf „STORYFORGE beenden“ stoppt den lokalen Server und einen von STORYFORGE gestarteten Ollama-Prozess. Eine vorher laufende Ollama-Instanz bleibt bestehen.

Die Modellkommunikation unterscheidet jetzt HTTP-, JSON-, leere, reine Thinking- und unvollständige Antworten sowie Ausgabelimits. Stoffkeim-Schemafehler benennen das betroffene Feld. Der Standard-Timeout beträgt 300 Sekunden und ist konfigurierbar. Optionale lokale Metadaten-Diagnosen enthalten keine Prompt- oder Antworttexte. Ein vollständiger JSON-Codeblock kann ohne weiteren Modellaufruf entfernt werden; alle inhaltlichen Validierungs- und Freigaberegeln gelten weiter.

Die Gesprächsansicht zeigt den vollständigen gespeicherten Verlauf, echtes Ollama-Streaming für freie Antworten und sicheres lokales Markdown. Anschlussaktionen übernehmen ausgewählte Beiträge oder kreative Ergebnisse als Ausgangsmaterial. Abgebrochene Teilantworten werden nicht gespeichert; die Übernahme als Idee bleibt ein freizugebender Entwurf.

Die fünf kreativen Verfahren, Projektgedächtnis, Autorenfreigabe, Wissenskarten, Classic Hell/Dunkel und die optionale Testwerkstatt bleiben erhalten. Das Windows-ZIP enthält Launcher, Programmdateien, 59 Wissenskarten, sechs Pilotfälle, beide Logos und deutschsprachige Anleitungen. Python 3.10+ muss separat installiert werden; für Modellläufe ebenso Ollama und ein lokales Modell. Die erste Installation der Python-Abhängigkeiten benötigt Internetzugang.

138 automatisierte Tests bestehen unter Linux mit Fake-Providern, HTTP-Stubs und Prozessdoubles. Die Gesprächsansicht wurde unter Chromium in Classic Hell und Dunkel mit synthetischen Daten geprüft. Der vom Autor berichtete Windows-Start mit Gemma umfasst V01; die konkrete Ursache des V02-Fehlers konnte ohne die fehlgeschlagene Ollama-Antwort noch nicht reproduziert werden. Ein eigener realer Gemma-Streaminglauf und kreative Qualitätsprüfung stehen aus. Der Server bindet ausschließlich an `127.0.0.1`; es gibt keine Telemetrie.
