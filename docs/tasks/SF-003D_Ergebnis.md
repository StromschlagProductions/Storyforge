# SF-003D – Narrative Mutation V04 und kritische Autorenredaktion V05

Stand: 27.11.2026. Ausgangsstand `9352bf8`. Ausschließlich SF-003D implementiert.

## Architektur und Schnittstellen

`Autorenredaktion(memory, provider, library)` nutzt den vorhandenen `Dialogue`, die versionierten Wissenskarten und `creative_runs`. Keine Datenbankmigration, neue Engine oder automatische Kanonänderung. `mutate(project_id, branch_id, task, source, *, operation, erhalten=(), veraenderbar=(), gezielt_aendern=(), moeglichkeiten=(), card_ids=(), card_limit=4, cancel=None)` und `critique(project_id, branch_id, task, source, *, bereiche=alle, card_ids=(), card_limit=4, cancel=None)` benötigen je **einen** Modellaufruf. `get_result(run_id)` stellt gespeicherte Ergebnisse wieder her.

`Quelle` bezeichnet genau eine bestätigte Idee der aktiven Revision (`art="idee", id=...`), einen gespeicherten Creative Run (`art="creative_run", id=...`) oder freien Text (`art="frei", beschreibung=...`). Bei Creative Runs werden Projekt, Variante und Ausgangsrevision mit dem aktuellen Stand verglichen. Fremde und veraltete Quellen werden abgelehnt. Für freie Texte ist keine Skriptdatei erforderlich.

## V04: Datenvertrag und Schutz

`Operation` bietet Substitution, Inversion, kausale Umkehr, Perspektivwechsel, Skalierung, Reduktion, Rekombination, Regeltransformation, akustische Transformation und freie Mutation. `Mutationsantwort` enthält mindestens eine `Alternative`. Jede Alternative verlangt Bezeichnung, Kurzbeschreibung, Operation, veränderte und bewahrte Elemente, neue Möglichkeiten, kausale und dramaturgische Folgen, Auswirkungen auf Figuren und Geheimnisse, Hörspielpotenzial, Risiken, ungeklärte Auswirkungen, einzeln begründete Schutzprüfungen sowie verwendete Karten-IDs. Leere Listen sind zulässig, wenn ein Aspekt nicht bestimmbar ist; Ungewissheit soll ausdrücklich in `ungeklaerte_auswirkungen` stehen. Dies ist keine Kausalitätssimulation.

Die Schutzmenge ist die Vereinigung aus `erhalten` und allen `protected_elements` der bestätigten Ideen in der aktiven Revision. Widersprüche zu `veraenderbar` oder `gezielt_aendern` werden vor dem Modellaufruf abgelehnt. Jede Alternative muss jedes geschützte Element genau einmal mit `bewahrt`, `verletzt` oder `ungeklärt` und Begründung prüfen. Verletzungen bleiben sichtbar. Eine Modellbehauptung `bewahrt` beweist semantische Erhaltung nicht; eine redaktionelle Prüfung bleibt nötig. Bestätigte Autorenentscheidungen stehen im Projektkontext und werden nicht verändert.

## V05: Datenvertrag

`Analysebereich` umfasst Originalität/Klischees, Kausalität/Logik, Figurenmotivation, Geheimnis/Auflösung, Dramaturgie, Emotion, Akustik und wissenschaftliche/historische Plausibilität. Eine oder mehrere Bereiche sind wählbar. Jeder `Befund` verlangt Bereich, Art (`widerspruch`, `interpretation`, `geschmack`, `recherchebedarf`), konkretes Problem, Materialbezug, Begründung, qualitative Bedeutung, Verbesserung, mögliche Nachteile und verbleibende Unsicherheit. `Kritikantwort` enthält außerdem Stärken, beizubehaltende Eigenschaften, offene Fragen und verwendete Karten-IDs. Eine leere Befundliste ist zulässig: Kritik muss keine Probleme erfinden. Es gibt keine Kreativitätsnote oder verpflichtende Dramaturgieschablone. Der Prompt untersagt unbelegte wissenschaftliche und historische Tatsachenbehauptungen; automatische Faktenrecherche findet nicht statt.

## Karten, Kontext und Autorfreigabe

`card_ids` erlaubt eine gezielte Auswahl. Weitere Karten werden nach exakten Aufgabenwörtern und danach mit dokumentiertem Fallback aus M, N, D und A gewählt; insgesamt höchstens fünf. Nur übermittelte IDs dürfen im Ergebnis genannt werden. Das Kontextmanifest speichert Projekt, Variante, Revision, Karten-IDs/-Versionen, Auswahlgründe, Verfahren und Quelle. Wissenskarten sind Anregungen. Die Ergebnisse bleiben unabhängig von Gesprächsverlauf und Revisionskopf in `creative_runs`. Eine komplexe Alternative oder Kritik wird nicht verlustbehaftet in das SF-001-`Idea`-Format gepresst. Verbindliche Änderungen benötigen einen gesonderten SF-001-Entwurf und ausdrückliche Autorfreigabe.

## Tests und Dateien

`.venv/bin/python -m pytest -q`: **94 bestanden**, einschließlich aller bisherigen 76. Neue Fake-Provider-Tests decken zehn Operationen, freie und bestätigte Quellen, gespeicherte Quellen, ausgewählte Kritikbereiche, Stärken ohne erzwungene Befunde, Karten-/Manifestabgleich, Schutzkonflikte, fehlende Schutzprüfungen, ungültige Karten und Bereiche, Timeout/Abbruch, Quellenisolation, veraltete Revisionen und Prozessneustart ab. Ein echter Ollama-Lauf bleibt bis zur Verfügbarkeit des Autoren-PCs zurückgestellt. Die Tests belegen **technische Funktionsfähigkeit**, nicht kreative Originalität oder Qualität.

Neu: `src/storyforge/autorenredaktion.py`, `tests/test_autorenredaktion.py`, dieser Bericht. Geändert: `src/storyforge/__init__.py`, `README.md`, `AGENTS.md`. Alle Teststoffe sind synthetisch. Keine privaten Hörspielskripte, Projektdatenbanken oder Zugangsdaten gehören zum Commit.

## Offene Fragen

- Semantische Bewahrung geschützter Elemente, Kausalität und wissenschaftliche Plausibilität können ohne redaktionelle Prüfung oder echte Recherche nicht bewiesen werden.
- Eine spätere fachliche Entscheidung ist nötig, wenn komplexe Mutationsalternativen vollständig in den Kanon übernommen werden sollen. SF-004 und weitere Verfahren wurden nicht implementiert.

## Abschlussprüfung der 15 Akzeptanzkriterien

1. **Beide Verfahren:** V04 und V05 sind unabhängig mit je einem Modellaufruf nutzbar.
2. **Operationen:** Alle zehn `Operation`-Werte werden durchlaufen und die Modellantwort muss die gewählte Operation bestätigen.
3. **Quellen:** Freier Text, bestätigte Idee und gespeicherter Creative Run sind geprüft.
4. **Schutz:** Jede Alternative prüft alle geschützten Elemente einzeln; fehlende oder doppelte Angaben werden abgelehnt.
5. **Folgen:** Änderungen sowie kausale, dramaturgische, Figuren-, Geheimnis- und Hörspielfolgen haben eigene Ergebnisfelder.
6. **Bereiche:** Einzelne und kombinierte `Analysebereich`-Werte werden geprüft; fremde Bereiche werden abgelehnt.
7. **Befunde:** Konkreter Materialbezug, Begründung und Verbesserung sind Pflichtfelder.
8. **Stärken und Unsicherheit:** Stärken, zu Bewahrendes, Nachteile und Unsicherheit bleiben sichtbar; eine leere Befundliste ist zulässig.
9. **Kartenkontext:** Übermittelte Karten-IDs und Versionen entsprechen dem Manifest; unbekannte Ergebnis-IDs werden abgelehnt.
10. **Persistenz:** Ein separater Python-Prozess liest Manifest und Ergebnis aus SQLite erneut.
11. **Isolation:** Creative Runs müssen Projekt, Variante und aktuelle Ausgangsrevision treffen; fremde und veraltete Quellen werden abgelehnt.
12. **Kanon:** Kein Verfahren ruft `approve` auf oder ändert den Revisionskopf.
13. **Fehler:** Ungültiges JSON, Schutzwiderspruch, falsche Karten/Bereiche, Timeout, Abbruch auch nach Antwort und paralleler Revisionswechsel werden ohne gespeicherten Lauf behandelt.
14. **Regression:** Die bisherigen 76 Tests bestehen weiter.
15. **Neue Tests:** Insgesamt bestehen **94** automatisierte Tests.

Eine Schutzprüfung mit Status `verletzt` bleibt sichtbar. Eindeutige interne Widersprüche, etwa dass dasselbe Element zugleich als verletzt und bewahrt bezeichnet wird, werden abgelehnt. Dies erkennt nur wörtlich identische Elemente; semantische Bewahrung verlangt weiterhin Autorenprüfung. Die Promptinspektion fand keine festen Beats oder Pflichtdramaturgie. V04 verlangt gezielte Varianten statt vollständiger Neugenerierung; V05 erlaubt ausdrücklich eine Kritik ohne negative Befunde. Gemeinsame Hinweise wiederholen sich nur einmal je Modellaufruf. Die Prüfung belegt Form und technische Schutzregeln, nicht tatsächliche kreative Qualität.

## Öffentliche Schnittstellen V01–V05 für SF-004

| Verfahren | Einstieg | Ergebnis und Speicherung | Verbindlichkeit |
| --- | --- | --- | --- |
| V01 Gespräch | `Dialogue(memory, provider).ask(project_id, branch_id, task, structured=False, cards=None, persist=True)` | `DialogueResult`; Gespräch in `conversation_turns` bei `persist=True` | Freier Text ändert keinen Kanon. `structured=True` erzeugt nur einen SF-001-Entwurf. |
| V02 Stoffschmiede | `Stoffschmiede(memory, provider, library).develop(project_id, branch_id, task, count=3, reflect=False)` | `StoffschmiedeErgebnis`; `creative_runs` | `stage_candidate(run_id, candidate_id)` erzeugt nur einen freizugebenden Entwurf. |
| V03 Geheimnislabor | `Geheimnislabor(memory, provider, library).develop(project_id, branch_id, task, mode=Arbeitsweise.RUECKWAERTS, ...)` | `GeheimnisErgebnis`; `get_result(run_id)` | Hypothesen bleiben kreative Entwürfe. |
| V04 Mutation | `Autorenredaktion(memory, provider, library).mutate(project_id, branch_id, task, Quelle(...), operation=Operation.INVERSION, ...)` | `Verfahrensergebnis` mit `Mutationsantwort`; `get_result(run_id)` | Alternativen bleiben kreative Entwürfe. |
| V05 Kritik | `Autorenredaktion(memory, provider, library).critique(project_id, branch_id, task, Quelle(...), bereiche=(Analysebereich.KAUSALITAET,))` | `Verfahrensergebnis` mit `Kritikantwort`; `get_result(run_id)` | Befunde bleiben kreative Entwürfe. |

Alle Einstiege benötigen ein ausgewähltes Projekt und eine Variante. Die Provider-Schnittstelle erlaubt `FakeProvider` für Tests und lokalen `OllamaProvider`; ein echter Ollama-Test bleibt zurückgestellt. SF-004 ist hier nur durch die Dokumentation vorbereitet, nicht implementiert.
