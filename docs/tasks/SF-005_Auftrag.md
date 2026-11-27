# STORYFORGE – SF-005: Kreativer Qualitätspilot

Ausgangsstand: `69e402c` auf `origin/main`. SF-001 bis SF-004 und LIB-001 sind technisch abgeschlossen; 102 automatisierte Tests bestehen. Implementiert wird ausschließlich die Vorbereitung des kreativen Qualitätspiloten. Der reale Ollama-Test findet später auf dem Autoren-PC statt.

## Ziel

Ein reproduzierbares Vergleichsverfahren zur Untersuchung des kreativen Mehrwerts von STORYFORGE gegenüber gewöhnlicher KI-Zusammenarbeit.

## Vergleichsverfahren

- **A:** Dasselbe Sprachmodell ohne Wissenskarten und spezielle kreative Verfahren.
- **B:** Dasselbe Sprachmodell mit ausgewählten Wissenskarten, aber ohne vollständigen kreativen Verfahrensablauf.
- **C:** Dasselbe Sprachmodell mit den vorhandenen STORYFORGE-Verfahren.

Vergleichbare Aufgabenstellungen, Kandidatenzahlen, Modellparameter und Ausgabelängen verwenden. Unterschiede im Kontext, in der Zahl der Modellaufrufe und im Rechenaufwand dokumentieren. Optionale Reflexionsaufrufe gesondert kennzeichnen. Kein unfairer Vergleich durch wesentlich höhere Generierungsbudgets. Der Vergleich unterschiedlicher Sprachmodelle wird separat behandelt.

## Testbibliothek

Sechs synthetische, versionierte Testfälle ohne private Hörspielinhalte:

- T01: Polarforschung, biologischer Widerspruch, Schuld, Mehrdeutigkeit.
- T02: Archäologischer Wissenschaftsthriller mit ungewöhnlichem Artefakt.
- T03: Psychologischer Horror ohne übernatürliche Erklärung, Serienmörder oder geheimes Menschenexperiment.
- T04: Akustisches Geheimnis mit späterer Umdeutung eines Geräusches.
- T05: Mehrere unabhängige Beobachtungen mit gemeinsamer verborgener Ursache.
- T06: Gezielte Veränderung einer schwachen Auflösung unter Schutz ausgewählter Stoffelemente.

## Bewertung

Ergebnisse anonymisieren, zufällig anordnen und erst nach der Bewertung die verwendete Methode auflösen. Der Autor bewertet Faszination, Originalität, Geheimnisqualität sofern relevant, innere Logik, emotionale Bedeutung, Hörspielpotenzial und Weiterentwicklungswunsch; freie Anmerkungen sind möglich. Nicht zutreffende Kriterien können übersprungen werden. Keine automatische Kreativitätsnote und keine automatische Siegerbehauptung.

## Bedienung

Eine kompakte optionale Testwerkstatt in die vorhandene Oberfläche integrieren, vorzugsweise unter Einstellungen. Die reguläre Autorenwerkstatt nicht komplizierter machen. Testprojekte und Testergebnisse von produktiven Geschichtenprojekten trennen. Modellname, Testfall, Vergleichsverfahren und Wiederholungen auswählbar machen; einzelne Tests ermöglichen. Ergebnisse und Bewertungen lokal speichern und als JSON sowie lesbaren Markdown-Bericht exportieren.

## Technische Anforderungen

Vorhandene Provider, kreative Verfahren und Hintergrundaufträge wiederverwenden. Modellkennung, Kartenversionen, Aufgabenstellung, Modellparameter, Laufzeit, verfügbare Tokeninformationen, Fehler und Abbrüche protokollieren. Keine externe Datenübermittlung. Automatisierte Tests ausschließlich mit Fake-Provider.

## Akzeptanzkriterien

1. Sechs synthetische Testfälle verfügbar.
2. Vergleichsverfahren A, B und C unabhängig ausführbar.
3. Verwendetes Modell und tatsächliche Kontextunterschiede nachvollziehbar.
4. Anonymisierte Bewertung ohne vorherige Offenlegung der Methode.
5. Bewertungen und Ergebnisse nach Neustart verfügbar.
6. JSON- und Markdown-Testberichte exportierbar.
7. Testdaten bleiben von normalen Geschichtenprojekten isoliert.
8. Abbruch und Modellfehler sicher behandelt.
9. Alle bisherigen 102 Tests bleiben erfolgreich.
10. Neue Funktionen besitzen automatisierte Tests.

## Nicht Bestandteil

Neue kreative Engines, externe Modellanbieter, Fade In, Saga-Erweiterungen oder größere Änderungen der Autorenoberfläche.

## Abschluss

Testverfahren, Bedienung, Ergebnisformate, Testergebnisse und Einschränkungen in `docs/tasks/SF-005_Ergebnis.md` dokumentieren. Diesen vollständigen Auftrag unter `docs/tasks/SF-005_Auftrag.md` hinterlegen. Simulierte Ergebnisse niemals als reale Kreativitätstests ausgeben. Lokalen Commit erstellen. Kein Push, kein Release und keine weiteren Entwicklungsaufträge.
