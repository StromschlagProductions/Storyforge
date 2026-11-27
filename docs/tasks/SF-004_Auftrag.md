# STORYFORGE – SF-004: Erste Autorenoberfläche

Ausgangsstand: `109e35e` auf `origin/main`. SF-001 bis SF-003D sowie LIB-001 sind technisch abgeschlossen; 94 automatisierte Tests bestehen. Ausschließlich SF-004 ist zur Implementierung freigegeben.

## 1. Ziel

Eine tatsächlich bedienbare, deutschsprachige lokale Autorenwerkstatt für Windows. Kreative Zusammenarbeit steht im Mittelpunkt, nicht Datenbankverwaltung.

## 2. Architektur

- Lokale Browseranwendung mit schlankem Python-Backend, vorzugsweise FastAPI und einfacher HTML/CSS/JavaScript-Oberfläche.
- Nur Loopback-Bindung. Keine Cloud-Dienste, kein externes CDN, keine Telemetrie.
- Bestehenden Python-Kern und SQLite-Speicher weiterverwenden. Keine zweite Geschäftslogik implementieren.

## 3. Verbindliches GUI-Design

STORYFORGE gehört optisch zur Stromschlag-Audio-Produktfamilie. Primäre Designreferenz: Spatial Lab Classic. Ergänzende Referenzen: Stromscore, Dreamcatcher und Tumult:

- <https://github.com/StromschlagProductions/SpatialLab-vst>
- <https://github.com/StromschlagProductions/Stromscore-vst>
- <https://github.com/StromschlagProductions/Dreamcatcher-vst>
- <https://github.com/StromschlagProductions/Tumult-vst>

Insbesondere `docs/oberflaeche-dunkel.png`, `docs/oberflaeche-hell.png`, `docs/logo-dunkel.png` und `docs/logo-hell.png` prüfen. Vorhandene Farbdefinitionen im Plugin-Quellcode berücksichtigen. Die Designkorrektur ersetzt die ursprünglich vorgeschlagene Atelier-Optik und das kräftige Orange:

- Originales Stromschlag-Audio-Logo oben links, nicht neu zeichnen; passende lokale Logo-Variante je Theme.
- Prägnanter STORYFORGE-Schriftzug; einheitliche Typografie, Rahmen und Bedienelemente.
- Classic Hell und Classic Dunkel, während des Betriebs umschaltbar und dauerhaft gespeichert; sämtliche Ansichten und Dialoge unterstützen beide.
- Dezente, matte Messing-/Sandgoldakzente statt kräftigem Orange. Akzent sparsam für aktive Elemente, Auswahl und wichtige Aktionen.
- Orientierende Palette: dunkler Hintergrund `#17191C`, dunkle Bedienflächen `#24262A`, primärer Akzent `#B99A70`, heller Akzent `#E7D3B5`, heller Hintergrund `#DEDEDB`, helle Bedienflächen `#F1F0EC`. Für Lesbarkeit und Kontrast anpassen.
- Ruhige, professionelle Autorenwerkstatt für längere Texte; keine Verläufe, Glanzeffekte, übermäßigen Verzierungen oder VST-Drehregler.
- Bildressourcen lokal mitliefern; keine Online-Abhängigkeit. Screenshots beider Themes erstellen.

## 4. Arbeitsbereiche

Gemeinsamer Arbeitsbereich mit Projektauswahl, aktiver Variante, Modellstatus und Ansichten für Gespräch V01, Stoffschmiede V02, Geheimnislabor V03, Varianten V04, Lektorat V05, Projektakte und Einstellungen. Alle fünf kreativen Verfahren sind tatsächlich mit dem vorhandenen Backend verbunden, keine Attrappen. Freie deutschsprachige Eingaben stehen im Mittelpunkt; erweiterte Einstellungen nur bei Bedarf. Die 59 Wissenskarten arbeiten im Hintergrund und müssen nicht manuell konfiguriert werden.

## 5. Kreativer Arbeitsablauf

- Neue Projekte ohne Skript erstellen; bestehende öffnen und Varianten auswählen.
- Gespeicherte Stoffkeime und geeignete kreative Ergebnisse direkt als Ausgangsmaterial weiterer Verfahren verwenden. Veraltete oder unzulässige Quellen verständlich melden.
- Kreative Ergebnisse vollständig lesbar darstellen, einschließlich Geheimnismatrix, Schutzprüfungen, Kritikbefunden und Unsicherheiten.
- Ergebnisse bleiben unverbindlich. Übernahme nur über vorhandene Entwurfs- und Autorfreigabefunktionen. Keine verlustbehaftete Übernahme komplexer Ergebnisse erzwingen.
- Projektakte mit bestätigten Ideen, Autorenentscheidungen, Revisionen, gespeicherten Ergebnissen und JSON-/Markdown-Export.

## 6. Ollama und Bedienung

Installierte lokale Ollama-Modelle erkennen und auswählbar machen; Verbindungsstatus anzeigen; Offline-Fehler verständlich behandeln. Längere Aufrufe blockieren die Oberfläche nicht; sichtbarer Bearbeitungsstatus und Abbruch ohne erfundene Fortschrittsprozente. Bei Projektwechsel keine falsche Zuordnung laufender Anfragen/Ergebnisse. Modellantworten und importierte Texte als nicht vertrauenswürdig sicher darstellen; kein ausführbares HTML übernehmen.

## 7. Windows-Start

Ein einfacher Launcher wie `Start_Storyforge.bat` startet die lokale Anwendung und öffnet den Standardbrowser. Ersteinrichtung verständlich dokumentieren. Für normalen Betrieb keine langen Python-Befehle.

## 8. Akzeptanzkriterien

1. Anwendung lokal unter Windows startbar.
2. Projekte erstellen, öffnen und Varianten auswählen.
3. Alle fünf kreativen Verfahren über die Oberfläche nutzbar.
4. Ergebnisse vollständig und verständlich dargestellt.
5. Ergebnisse als Ausgangsmaterial weiterverwendbar.
6. Projektgedächtnis nach Neustart erhalten.
7. Autorfreigabe erforderlich für verbindliche Änderungen.
8. Modellwahl und Ollama-Verbindungsstatus funktionieren.
9. Modellaufrufe blockieren die Bedienung nicht; Abbruch und Fehler werden sicher behandelt.
10. Projektisolation bleibt gewährleistet.
11. JSON-/Markdown-Export funktioniert.
12. Alle bisherigen 94 Tests bleiben erfolgreich.
13. Neue Schnittstellen und zentrale Bedienabläufe besitzen automatisierte Tests.
14. Automatisierte Tests funktionieren ohne Ollama und GPU.
15. Beide Themes funktionieren in sämtlichen Ansichten und Dialogen; Theme-Auswahl bleibt nach Neustart erhalten.
16. Originales Stromschlag-Audio-Logo und vereinbarte Designsprache sind umgesetzt.

## 9. Nicht Bestandteil

Fade-In-Integration, DAW-Anbindung, externe KI-Anbieter, vollständige Saga-Verwaltung, neue kreative Engines, automatische Internetrecherche, weitere Forschungsfunktionen und SF-005.

## 10. Abschluss

Oberfläche nach Möglichkeit tatsächlich im Browser prüfen. Screenshots der wichtigsten Ansichten in beiden Themes erstellen, ausschließlich mit synthetischen Projektdaten. Startanleitung, Architektur, Testergebnisse, offene Fragen und bekannte Einschränkungen in `docs/tasks/SF-004_Ergebnis.md` dokumentieren. Diesen vollständigen Entwicklungsauftrag unter `docs/tasks/SF-004_Auftrag.md` hinterlegen. Commit-Dateien auf vertrauliche Inhalte prüfen. Unmögliche echte Ollama- oder Windows-Tests ausdrücklich dokumentieren; keine ungeprüfte kreative Qualität behaupten. Lokalen Commit erstellen. Kein Push, kein Release und keine Implementierung von SF-005.
