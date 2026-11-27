# SF-003C – Geheimnislabor V03

Stand: 27.11.2026. Ausgangsstand `3053faf`. Ausschließlich V03 implementiert; SF-003D, Oberfläche und automatische Recherche bleiben außerhalb dieses Auftrags.

## Architektur und Schnittstelle

`Geheimnislabor(memory, provider, NarrativeLibrary.load("library/cards"))` verwendet `Dialogue` für den isolierten Projekt-/Variantenkontext und die bestehende `creative_runs`-Tabelle für unverbindliche Ergebnisse. Es gibt keine neue Engine und keine Datenbankmigration. `develop(project_id, branch_id, task, *, mode, observations=(), given_truth=None, card_ids=(), card_limit=4, reflect=False, cancel=None)` akzeptiert eine freie deutschsprachige Aufgabe ohne Skript. `mode` ist `Arbeitsweise.RUECKWAERTS`, `.VORWAERTS`, `.ALTERNATIVEN` oder `.PRUEFUNG`. Rückwärtsentwicklung und Alternativen verlangen mindestens zwei Hypothesen, die Prüfung erlaubt eine einzelne. Vorwärtsentwicklung verlangt `given_truth` als ausdrückliche Autorvorgabe; diese gilt nur im Entwurf und wird nicht zum Kanon. `get_result(run_id)` lädt das strukturierte Ergebnis erneut.

Eine Bearbeitung nutzt genau einen Modellaufruf. `reflect=True` ergänzt genau einen Aufruf für `Reflexion` mit Stärken, Risiken und Fragen; die Reflexion verändert den Entwurf nicht. Ungültige Modellantworten, fehlgeschlagene Reflexion, Timeout, Abbruch und zwischenzeitlicher Revisionswechsel speichern keinen Creative Run. Das Modell löst niemals `Memory.approve` aus.

## Datenvertrag

`Beobachtung` hat `id: UUID` und `beschreibung: nicht leerer Text`. Vom Autor übergebene Beobachtungen müssen mit unveränderten IDs und Texten in der Modellantwort erscheinen. `Interpretation` hat `beobachtung_id` und `deutung`; sie ist ausdrücklich eine Deutung, kein beobachteter oder bestätigter Fakt. `Hypothese` hat `id`, `bezeichnung`, optionalen `verborgener_mechanismus`, Listen für `notwendige_annahmen`, `widersprueche`, `offene_fragen`, `hinweise`, `falsche_faehrten`, `emotionale_folgen`, `recherchebedarf` und `verwendete_karten_ids` sowie optionale Texte für `vorbereitung`, `enthuellung` und `hoerspielpotenzial`. Optionale Felder und leere Listen erlauben bewusst unvollständige Hypothesen. Eine Hypothese ist nie bestätigte fiktionale Wahrheit.

`MatrixEintrag` verbindet genau eine existierende Beobachtung mit genau einer existierenden Hypothese. `zustand` ist **erklärt**, **zusätzliche Annahme erforderlich**, **widerspricht** oder **ungeklärt**; `begruendung` darf nicht leer sein. Die Matrix benötigt genau einen Eintrag für **jedes** Beobachtung-Hypothese-Paar. Doppelte oder unbekannte Referenzen werden abgelehnt. Es gibt keine numerische Rangliste. `Geheimnismodell.bewusst_mehrdeutig` markiert gewollte Offenheit.

`Schutzpruefung` dokumentiert für jedes aus der aktuellen Revision stammende geschützte Stoffelement den Status **bewahrt**, **verletzt** oder **ungeklärt** und eine Begründung. Fehlende oder doppelte Prüfungen werden abgelehnt. Erkennbare Verletzungen werden im Entwurf sichtbar gespeichert; ihre semantische Erkennung durch das Modell ist nicht deterministisch beweisbar. Bestätigte Autorenentscheidungen bleiben im von `Dialogue` bereitgestellten Projektkontext, werden nicht verändert und nicht automatisch überschrieben.

## Kartenauswahl und Kontextmanifest

`select_cards(task, limit=4, card_ids=())` wählt höchstens fünf Karten. Angegebene IDs haben Vorrang; unbekannte und doppelte IDs werden abgelehnt. Danach folgt je eine passende M-, N-, A- und D-Karte, zuerst nach exaktem Aufgabenwort, sonst mit ausdrücklich dokumentiertem Fallback. D-Karten werden über ihre produktive Aufgabenart `dramaturgie` als Ergänzung gewählt. Nur diese Karten gehen in den Modellkontext. Das `manifest` dokumentiert Karten-IDs und Versionen, Auswahlgründe, Projekt, Variante, Revision, Verfahren, Arbeitsweise, geschützte Elemente und IDs vorgegebener Beobachtungen. Die vom Autor vorgegebene Wahrheit wird lokal im Manifest gespeichert, damit der Entwurf vollständig wiederherstellbar ist; sie ist kein Kanonstatus.

Der Prompt fordert grundverschiedene Erklärungsmechanismen, sinnvolle Umdeutungen, sparsame Zusatzannahmen, emotionale Folgen, hörbare Informationsvermittlung und die Trennung wissenschaftlicher Spekulation von gesichertem Wissen. Karten sind Anregungen ohne verpflichtende Dramaturgieschablone. Automatische Tests prüfen die Struktur, nicht kreative Originalität.

## Abschlussprüfung der 14 Akzeptanzkriterien

1. **Vier Arbeitsweisen:** Rückwärts, vorwärts, Alternativen und Prüfung sind über `Arbeitsweise` verfügbar und mit Fake-Provider getestet.
2. **Ohne Skript:** Alle vier Modi laufen auf einem frisch angelegten synthetischen Projekt.
3. **Konkurrierende Hypothesen:** Rückwärts und Alternativen verlangen mindestens zwei; die Prüfung darf bei einer bleiben.
4. **Matrix:** Jede Beobachtung-Hypothese-Kombination braucht genau eine begründete Zuordnung. Fehlende, doppelte und fremde Referenzen werden abgelehnt.
5. **Widerspruch und Offenheit:** `widerspricht` und `ungeklärt` bleiben als eigene Zustände erhalten; auch unvollständige Hypothesen sind gültig.
6. **Mehrdeutigkeit:** `bewusst_mehrdeutig` und optionale Mechanismus-/Enthüllungsfelder erlauben bewusst ungelöste Entwürfe.
7. **Geschützte Elemente:** Jedes geschützte Element braucht eine eigene begründete Prüfung. Verletzungen und Unklarheiten werden sichtbar, nicht eigenmächtig korrigiert. Die Wahrheit der Modellbehauptung braucht redaktionelle Prüfung.
8. **Karten und Manifest:** IDs, Versionen, Auswahlgründe und Fallback werden dokumentiert; ein Test vergleicht die übermittelten Karten direkt mit dem Manifest.
9. **Persistenz:** Ein separater Python-Prozess lädt den gespeicherten Creative Run nach erneutem Öffnen der SQLite-Datenbank.
10. **Isolation:** Modellkontext und gespeicherter Lauf enthalten nur das gewählte Projekt und die gewählte Variante.
11. **Autorenkontrolle:** Kein V03-Aufruf erzeugt eine Kanonrevision oder Autorfreigabe; vorgegebene Wahrheit bleibt als Autorangabe getrennt von Hypothesen.
12. **Fehlerpfade:** Ungültige Antworten, Referenzen, Karten, Schutzprüfungen und Reflexion sowie Timeout, Abbruch und Revisionswechsel werden ohne Creative Run oder automatische Kanonänderung behandelt.
13. **Regression:** Die bisherigen 60 Tests bestehen weiterhin.
14. **Neue Tests:** Insgesamt bestehen **76** automatisierte Tests.

Die Promptprüfung bestätigt Anregungen zu grundverschiedenen Mechanismen, emotionalen Folgen, sparsamen Zusatzannahmen und kontrollierter Mehrdeutigkeit. Karten sind ausdrücklich freie Anregungen ohne Dramaturgieschablone. Dies belegt die *Anweisung*, nicht ihre kreative Befolgung durch ein reales Modell.

## Autorfreigabe und Grenzen

`develop` und `get_result` verändern keinen Revisionskopf. `creative_runs` bewahrt das vollständige strukturierte Geheimnismodell. Der kleine SF-001-`Idea`-Vertrag kann eine Hypothesenmatrix nicht vollständig als Kanon aufnehmen. Deshalb gibt es in V03 keine automatische oder verkürzte Übernahme. Eine spätere ausdrückliche Kanonänderung muss als gesonderter SF-001-Entwurf mit aktueller Ausgangsrevision und `Memory.approve(..., explicit_approval=True)` erfolgen. Ein erkannter Schutzverstoß verlangt vor einer solchen Übernahme die Entscheidung des Autors.

## Tests und Dateien

`.venv/bin/python -m pytest -q`: **76 bestanden**, darunter alle bisherigen 60 Tests. Neue Fake-Provider-Tests decken vier Arbeitsweisen ohne Skript, vollständige Matrix, Mehrdeutigkeit, Manifest/Karten, Fallback, gezielte Auswahl, optionale Reflexion, Prozessneustart, Projekt-/Variantenisolation, Schutzprüfung, unbekannte Referenzen und Karten, Timeout, Abbruch sowie Revisionswechsel ab. Ein echter Ollama-Lauf fand mangels installiertem Modell und Autoren-PC nicht statt. Die Tests belegen technische Funktionsfähigkeit, **keine nachgewiesene Originalität oder dramaturgische Qualität**.

Neu: `src/storyforge/geheimnislabor.py`, `tests/test_geheimnislabor.py`, dieser Bericht. Geändert: `src/storyforge/__init__.py`, `README.md`, `AGENTS.md`. Alle Tests verwenden synthetische Inhalte. Keine private Projektdatenbank, kein unveröffentlichter Hörspielstoff und kein Zugangsschlüssel wurden für den Commit vorgesehen.

## Offene Fragen

- Wie Hypothesenmatrix und bestätigte fiktionale Wahrheit künftig vollständig in den Kanonvertrag übergehen, benötigt eine fachliche Entscheidung.
- Semantisch falsche Schutzbehauptungen und tatsächliche Mechanismusvielfalt brauchen redaktionelle Prüfung an echten Modellläufen. Der lokale Ollama-Test bleibt wie vereinbart zurückgestellt.
- Eine spätere Oberfläche kann Widersprüche, offene Beziehungen und Schutzverletzungen sichtbar zur Autorentscheidung anbieten; dies ist nicht Teil von SF-003C.
