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

`.venv/bin/python -m pytest -q`: **91 bestanden**, einschließlich aller bisherigen 76. Neue Fake-Provider-Tests decken zehn Operationen, freie und bestätigte Quellen, gespeicherte Quellen, ausgewählte Kritikbereiche, Stärken ohne erzwungene Befunde, Karten-/Manifestabgleich, Schutzkonflikte, fehlende Schutzprüfungen, ungültige Karten und Bereiche, Timeout/Abbruch, Quellenisolation, veraltete Revisionen und Prozessneustart ab. Ein echter Ollama-Lauf bleibt bis zur Verfügbarkeit des Autoren-PCs zurückgestellt. Die Tests belegen **technische Funktionsfähigkeit**, nicht kreative Originalität oder Qualität.

Neu: `src/storyforge/autorenredaktion.py`, `tests/test_autorenredaktion.py`, dieser Bericht. Geändert: `src/storyforge/__init__.py`, `README.md`, `AGENTS.md`. Alle Teststoffe sind synthetisch. Keine privaten Hörspielskripte, Projektdatenbanken oder Zugangsdaten gehören zum Commit.

## Offene Fragen

- Semantische Bewahrung geschützter Elemente, Kausalität und wissenschaftliche Plausibilität können ohne redaktionelle Prüfung oder echte Recherche nicht bewiesen werden.
- Eine spätere fachliche Entscheidung ist nötig, wenn komplexe Mutationsalternativen vollständig in den Kanon übernommen werden sollen. SF-004 und weitere Verfahren wurden nicht implementiert.
