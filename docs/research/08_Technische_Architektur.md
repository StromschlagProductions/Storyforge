# STORYFORGE – Forschungsbericht 08: Technische Architektur
26.11.2026 | Technischer Konzeptstand, öffentliche Fassung. Kreative Stoffentwicklung hat Vorrang vor Fade In. Acht funktionale Bausteine C01–C08.

## Architekturvorschlag
Python, SQLite, Pydantic, modularer Monolith, lokale Browseroberfläche (FastAPI mit einfacher HTML/JS-Oberfläche; endgültige GUI nach Usability-Test). Keine Microservices, Graphdatenbank, autonomen Agenten oder Modelltrainings in P0. Datenhaltung lokal, externe Übermittlung nur nach bewusster Freigabe. API-Schlüssel nicht in Projektdateien oder Logs. Lokaler Server ausschließlich Loopback, keine automatische externe Freigabe. Abhängigkeiten versionieren; Windows als Zielplattform.

## P0 – vertikaler kreativer Arbeitsablauf
1. Neues Projekt ohne Manuskript erstellen oder bestehende Notizen importieren.
2. Freier Dialog mit Ziel, aktuellem Projektstand und ausgewählten Wissenskarten.
3. Ideen/Hypothesen erzeugen; Autor kann Kernbestandteile markieren, Varianten abzweigen und Kritik anfordern.
4. KI liefert lesbaren Text; strukturierte Vorschläge separat validieren und als Entwurf speichern.
5. Autor übernimmt ausgewählte Änderungen; neue Revision atomar erzeugen. Ablehnung verändert keinen Kanon.
6. Projekt schließen und erneut öffnen; Entscheidungen und Varianten vollständig erhalten; portable Markdown/JSON-Ausgabe.

## Komponenten und Schnittstellen
C01: Quellenimport zunächst Text/Markdown; Fade In lesend nach Bedarf, versions- und vorlagenbewusst. C02: Repository für Projekte, Werke, optionale Universen, Quellen, Revisionen, Ideen, Feedback, Gesprächsverlauf. C03: P0 narrative Notizen und typisierte Hypothesen/Beobachtungen; P1 zeitabhängiges Wissen, Ereignisse, Evidenzbeziehungen und Kanon. C04: ModelAdapter.generate(request), normalisierte Antwort, Modellkennung, Token-/Laufzeitmetadaten sofern verfügbar, Fehler, Abbruch, Fähigkeiten; Kontextauswahl separat. C05: versionierte Verfahren, Mechanismenkarten und CreativeRun. C06: Schema-, Referenz- und Revisionsvalidierung; qualitative Kritik als begründete Befunde. C07: optionale dramaturgische und akustische Profile. C08: Gespräch, Projektakte, Varianten und Freigabe; keine Formularpflicht.

## Minimales Datenmodell
Project(id,title,universe_id optional); Work(id,project_id,title); Source(id,work_id optional,content_hash,content,kind); Revision(id,project_id,parent_id,created_at,author,description,snapshot); Idea(id,revision_id,title,premise,mechanism,protected_elements,status); Observation(id,revision_id,text,source_anchor optional); Hypothesis(id,revision_id,explanation,assumptions,observation_links,status); Decision(id,revision_id,target,action,rationale); Run(id,revision_id,model,procedure_version,context_manifest,status,output,metrics); Card(id,version,principle,application,risks,checks,related_ids,source_refs). UUIDs intern, Hashes für Inhalte; Zeitstempel UTC. Snapshots zunächst vollständig statt komplexer Event-Sourcing-Architektur. SQLite-Transaktionen, Foreign Keys, Migrationen, Backups. Keine automatische Zusammenführung von Varianten. Werk- und Universumszuordnung explizit. Quellenanker bei fehlendem Skript optional. P0 keine vollständige Wahrheitssimulation. Für SF-001 nur den im Auftragsplan abgegrenzten Teil umsetzen.

## Kontext und Verfahren
Kontextpaket: aktuelle Aufgabe, bestätigte Fakten und Autorentscheidungen, relevante Quellen, aktuelle Variante, wenige passende Karten, optional jüngster Dialog. Kontextmanifest dokumentiert tatsächlich übergebene IDs und Versionen. Explizite Grenzen; fehlende Quellen anzeigen, keine heimliche Kürzung bestätigter Kernvorgaben. Externe Aufrufe zeigen Modell und freigegebenen Datenumfang. Skripte sind Daten, keine ausführbaren Anweisungen. Kein automatischer Webzugriff in P0.

Verfahren V01 freies Gespräch; V02 divergente Stoffkeime mit strukturell unterschiedlichen Mechanismen; V03 Geheimnislabor: Beobachtungen, konkurrierende Erklärungen, Gegenbeispiele, Zusatzannahmen und emotionale Folgen; V04 gezielte Varianten mit geschützten Eigenschaften; V05 Kritik mit konkreten Befunden und Reparaturoptionen. Erst einfache sequenzielle Aufrufe, keine Pflicht zu Multi-Agenten. Wissenskarten M/N/D/A als versionierte redaktionell geprüfte Datensätze; kleine Auswahl nach Aufgabe, keine gesamten Bücher. Keine starren Beats oder Kreativitätsnoten.

## Fehler und Sicherheit
Ungültige JSON-Ausgabe, Refusal, Timeout, Abbruch oder Provider-Ausfall führen zu sichtbarem Fehler/Entwurf, nie zu Kanonänderung. Schemavalidierung plus fachliche Referenzprüfung; gültiges JSON ist keine Wahrheit. Optimistische Revisionsprüfung gegen veraltete Vorschläge. Exporte atomar; Originalskripte unverändert. Keine automatische Telemetrie; externe Modellnutzung und Kosten sichtbar machen.

## P0 Freigabekriterien
Projekt ohne Skript; Neustart ohne Verlust; Varianten isoliert; ungültige und veraltete Vorschläge ändern nichts; Providerwechsel ohne Datenmigration; nachweisbare Kontextauswahl; mindestens zwei kreative Verfahren plus kritischer Dialog; externe Datenfreigabe; Export und Wiederherstellung; Vergleich mit gewöhnlichem Chat nach F09. Fade-In-Vollintegration ausdrücklich kein Gate. Keine empirische Validierung erfolgt.

## Offene Entscheidungen
GUI endgültig, externe Anbieter und Budget, Kontextlimits, genaue Datenverträge nach ersten Tests, Qualität lokaler Modelle. Kein GIZMO-Code geprüft. API-Quellen: https://github.com/ollama/ollama/blob/main/docs/api.md ; https://developers.openai.com/api/docs/guides/structured-outputs (ursprüngliche Sichtung 26.11.2026).
