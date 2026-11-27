# ALPHA 2 – Stabilisierung der Modellkommunikation

## Befund und Ursache der bisherigen Meldung

Der Adapter in `providers.py` fing vor der V02-Stoffkeimvalidierung mehrere unterschiedliche Fehler mit derselben Meldung „Ungültige Ollama-Antwort“ ab. Dazu gehörten ungültiges HTTP-JSON, fehlende Antwortfelder, leerer `message.content`, ein fehlender `done`-Abschluss und fehlerhafte Laufzeitwerte. Die vom Autor beobachtete Meldung beweist daher nur, dass der Adapter eine Antwort zurückgewiesen hat. **Welche Ursache der konkrete Windows-/Gemma-Lauf hatte, ist ohne dessen Rohantwort oder neue Metadaten nicht nachträglich bestimmbar.** Es wurden keine privaten Stoffe oder Modellantworten übernommen.

Nun werden HTTP-Status, ungültiges HTTP-JSON, fehlendes `message`, leerer Inhalt, reine `message.thinking`-Ausgabe, fehlender Abschluss und `done_reason=length` getrennt gemeldet. Die Meldungen enthalten keine Modelltexte. V02 benennt bei einem Pydantic-Schemafehler den Feldpfad und Fehlertyp, ohne den Feldwert auszugeben. Kontextrevision, Wissenskarten-IDs, Kandidatenzahl und Autorenfreigabe werden weiterhin geprüft.

## Konfiguration und Grenzen

- `STORYFORGE_MODEL_TIMEOUT_SECONDS`: Standard **300**, zulässig 1–3600 Sekunden. Gilt für die bestehenden Verfahren und den Pilot. Direkte `ModelRequest`-Aufrufe behalten ihren expliziten Timeout. Abbruch bleibt jederzeit möglich.
- `STORYFORGE_OLLAMA_NUM_CTX` und `STORYFORGE_OLLAMA_NUM_PREDICT`: optionale ganzzahlige Ollama-Parameter, jeweils 128–65536. Nicht gesetzt bedeutet: Ollama-/Modellvorgabe. Explizit übergebene Provider-Optionen haben Vorrang. Für einen ersten lokalen Gemma-V02-Versuch sind beispielsweise `num_ctx=8192` und `num_predict=4096` denkbar; die Eignung für das konkrete Modell und den verfügbaren VRAM ist nicht geprüft.
- Die bestehende STORYFORGE-Kontextgrenze beträgt **30.000 Zeichen**. Sie bewahrt verbindliche Autorenentscheidungen und ist kein Tokenlimit. Ollamas `num_ctx` ist davon unabhängig; ein zu kleines Token-Kontextfenster kann intern kürzen. Die HTTP-Antwort bleibt auf **4.000.000 Byte** begrenzt. `done_reason=length` wird als abgeschnittene Ausgabe abgelehnt.
- Gemma und Ollama können strukturierte Ausgaben über `format: <JSON-Schema>` liefern. Der Adapter übergibt das bestehende Pydantic-Schema unverändert. Ob das tatsächlich installierte Gemma-Modell alle Felder und das Schema bei drei Stoffkeimen erfüllt, bleibt praktisch zu testen. Ein vollständiger Markdown-Codeblock mit `json`-Kennung wird einmal deterministisch entfernt; es gibt keinen zusätzlichen Reparaturaufruf. Unvollständige oder inhaltlich ungültige JSON-Antworten werden nicht übernommen.

Unter Windows können die Werte vor `Start_Storyforge.bat` in einer Eingabeaufforderung gesetzt werden:

```bat
set STORYFORGE_MODEL_TIMEOUT_SECONDS=480
set STORYFORGE_OLLAMA_NUM_CTX=8192
set STORYFORGE_OLLAMA_NUM_PREDICT=4096
set STORYFORGE_MODEL_DIAGNOSTICS=1
Start_Storyforge.bat
```

Mit `STORYFORGE_MODEL_DIAGNOSTICS=1` schreibt STORYFORGE **nur lokal** `local/ollama-diagnostics.jsonl`. Erfasst werden Zeitstempel, Fehlerkategorie, HTTP-Status, Antwortgröße, Antwortdauer, verfügbare Prompt-/Ausgabetoken und Generierungsgeschwindigkeit (`eval_count / eval_duration`). Es werden **keine Prompts, Modellantworten, Thinking-Texte, Modellnamen, Projekt-IDs oder Zugangsdaten** protokolliert. Der Log-Eintrag `transport_ok` besagt nur, dass der Ollama-Adapter die Antwort angenommen hat; er bestätigt noch kein V02-Schema. Die Datei liegt im ignorierten `local/`-Ordner und gehört nicht in das öffentliche Repository. Kreative Läufe speichern verfügbare Laufzeit-, Token- und Geschwindigkeitswerte in ihren Metriken.

## Tests und Änderungen

`python -m pytest -q`: **129 bestanden** unter Linux. Synthetische HTTP-Tests unterscheiden die Fehlerklassen und prüfen ein Gemma-artiges Antwortformat, Modellparameter, Generierungsgeschwindigkeit und den Ausschluss privater Texte aus der Diagnose. Ein Fake-Provider-Test prüft die einmalige Codeblock-Bereinigung, 480-Sekunden-Timeout, persistierte V02-Metriken und unveränderten Revisionskopf. Weitere Tests prüfen Feldpfad- und JSON-Diagnose sowie die bestehenden 117 Funktionen. Ein echtes Gemma-Modell wurde in dieser Umgebung nicht ausgeführt; HTTP-Stubs belegen keine reale Modellkompatibilität oder kreative Qualität.

Geändert: `providers.py`, `dialogue.py`, die Konstruktoren von `stoffschmiede.py`, `geheimnislabor.py` und `autorenredaktion.py`, die Tests `test_providers.py` und `test_stoffschmiede.py`, README, Windows-Kurzanleitung und vorbereitete alpha.2-Release-Notizen. Das Windows-ZIP wird mit aktualisierten Programmdateien und Prüfsumme neu gebaut. Kein Push, Tag oder Release.
