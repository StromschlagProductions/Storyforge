# Vorbereitete Release Notes – STORYFORGE 0.1.0-alpha.2

**Status:** Release und Tag sind vorbereitet, aber noch nicht veröffentlicht.

Diese Alpha-Version ergänzt die bestehende lokale Autorenwerkstatt um eine automatische Ollama-Verwaltung. Beim Start prüft STORYFORGE den lokalen Ollama-Dienst, startet ihn bei Bedarf ohne zusätzliches Konsolenfenster, wartet auf Betriebsbereitschaft und zeigt die installierten Modelle. Eine fehlende Installation wird verständlich gemeldet; Projektverwaltung und Export bleiben nutzbar. Der neue Knopf „STORYFORGE beenden“ stoppt den lokalen Server und einen von STORYFORGE gestarteten Ollama-Prozess. Eine vorher laufende Ollama-Instanz bleibt bestehen.

Die fünf kreativen Verfahren, Projektgedächtnis, Autorenfreigabe, Wissenskarten, Classic Hell/Dunkel und die optionale Testwerkstatt bleiben erhalten. Das Windows-ZIP enthält Launcher, Programmdateien, 59 Wissenskarten, sechs Pilotfälle, beide Logos und deutschsprachige Anleitungen. Python 3.10+ muss separat installiert werden; für Modellläufe ebenso Ollama und ein lokales Modell. Die erste Installation der Python-Abhängigkeiten benötigt Internetzugang.

116 automatisierte Tests bestehen unter Linux mit Fake-Providern und Prozessdoubles. Ein tatsächlicher Windows-Start und echte Ollama-Modellläufe sind weiterhin offen. Kreativer Mehrwert ist noch nicht nachgewiesen. Der Server bindet ausschließlich an `127.0.0.1`; es gibt keine Telemetrie.
