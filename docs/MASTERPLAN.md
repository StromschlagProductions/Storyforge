# STORYFORGE – Masterplan v1.0 (öffentliche, bereinigte Fassung)

Stand 26.11.2026. Technische Arbeitsgrundlage; private Beispiele und historische Nachträge ausgelassen. Originalforschung bleibt privat. SF-001 ist der erste Entwicklungsauftrag, alle weiteren benötigen separate Freigabe.

## Vision
Deutschsprachige KI-Hörspiel-Autorenwerkstatt für originelle Stoffe, ungewöhnliche Geheimnisse, Figuren, Varianten, kritische Reflexion und zusammenhängende Erzähluniversen. Freies Gespräch zuerst, Struktur im Hintergrund. Autor entscheidet; keine Geschichtenfabrik, kein zweiter Drehbucheditor, keine Pflichtdramaturgie. Fade In unterstützt später den kreativen Prozess, ist kein P0-Gate.

## Funktionale Architektur
- C01 Dokumentenadapter: Quellen, später Fade In lesend, Stile, Reihenfolge und Quellenanker.
- C02 Projekt- und Revisionsspeicher: Werke, optionale Universen, Revisionen, Varianten, Autorentscheidungen, Recherche.
- C03 Narratives Modell: Figuren, Ereignisse, Fakten, Wissen, Geheimnisse, Hinweise, Abhängigkeiten.
- C04 Kontext- und Modelladapter: selektiver Kontext und austauschbare lokale/externe LLMs.
- C05 Kreative Verfahren: Kombination, Mutation, Analogie, Hypothesen, narrative Archäologie, Ideenarchiv.
- C06 Analyse und Validierung: Regeln, Folgenanalyse, qualitative Befunde und Quellenbezug.
- C07 Dramaturgie- und Hörspielprofile: Handlungs-, Figuren-, Informationsbögen und akustische Perspektive.
- C08 Autorenoberfläche: Gespräch, Projektwahl, Varianten, Befunde, Freigabe.
Diese Grenzen sind keine separaten Dienste. Python, SQLite, Pydantic, modularer Monolith; Windows, JSON/Markdown-Export. Keine Microservices, Graphdatenbank, Modelltraining oder Daueragenten in P0. GUI-Vorschlag lokal im Browser, noch offen.

## Datenprinzipien
Stabile interne UUIDs für Werke unabhängig von externen Dokumentkennungen; Revisionen über Hashes und explizite Zuordnung. Werk und optionales Universum getrennt. Fiktionale Wahrheit, Figurenwissen/-glaube, vermittelte Informationen und mögliche Zuhörerschlüsse trennen. Fiktionale Zeit, Erzählreihenfolge, Hörzeit und Wissensentwicklung unterscheiden. Faktenstatus, Publikationsstatus, Geltungsbereich und Widersprüche separat. Bewusst offene Geheimnisse zulassen. Beobachtungen, Interpretationen, historische Überlieferungen und reale Recherche unterscheiden. Quellenanker auf Werk, Revision, Szene, Absatz; Unsicherheit sichtbar machen. Ereignisse mit Voraussetzungen und Wirkungen, keine behauptete vollständige Kausalitätsprüfung. Varianten isolieren; Autorfreigabe atomar, veraltete Revision ablehnen. Skript/Kanon-Konflikte melden, nicht still korrigieren. Figuren mit zeitabhängigen Überzeugungen, Absichten, gerichteten Beziehungen und qualitativen Verhaltensmustern, keine psychometrischen Scores.

## Forschungswissen
Versionierte, kleine Wissenskarten mit Prinzip, Einsatz, Risiken, Prüfungen, verwandten IDs und Quellen. F01: divergentes Erfinden und Reflexion, Kombination, Exploration, Transformation, Blending, Mutation, Quality Diversity (MAP-Elites nicht beschlossen). F02: Abduktion, Hypothesen und Hinweisnetze, M01–M16. F03: D01–D17; Save the Cat, Campbell/Vogler, Field, Truby, McKee, Harmon, Kishōtenketsu als optionale Lesarten, nicht verpflichtende Beats; Neugier, Spannung und Überraschung getrennt. F04: N01–N16 narrative Mechanismen. F05: BDI, CAPS, IPOCL, Generative Agents als Inspiration für Motivationsprüfung und begrenzte Simulation. F06: Saga, Kanon, narrative Archäologie. F07: A01–A10 akustische Mechanismen. Autorpräferenzen editierbar, unerwartete Ideen weiter zulassen. Keine objektive Kreativitätsnote. Vollständige private Berichte werden nicht öffentlich hinterlegt; für spätere Aufgaben gezielt bereinigte Karten bereitstellen.

## Roadmap
P0: kreative Werkstatt ohne Skriptpflicht, projektbezogener Dialog, Stoffkeime, Hypothesen, Varianten, Kritik, Gedächtnis, Revisionen, Modellwahl und bewusste externe Datenfreigabe. Optional Textimport. Kreativer Nutzen gegenüber Chat prüfen.
P1: Fakten/Wissen, Hinweise, Geheimnisse, Abhängigkeiten, Kanon, optionale Dramaturgieprofile, Hörspielanalyse; Fade-In-Connector bei Bedarf.
P2: strukturelle Vielfalt, narrative Evolution, kurze Figurensimulationen, Saga-Bögen, narrative Archäologie; nur nach Nutzenprüfung.
P3: optionale Produktionsvorbereitung, DAW-Anbindung, mögliche gemeinsame Bibliothek mit unabhängigem GIZMO-Projekt nach konkreter Prüfung.

## Hörspiel und Fade In
Klang, Stimmen, Musik, Stille und Perspektive als erzählerische Mittel; akustische Vermittlung von bloßer Regieanweisung unterscheiden. Absichtliche Mehrdeutigkeit zulassen. Simulierter Zuhörer erhält nur bis dahin vermittelte Informationen und ersetzt keinen Hörtest. Fade In zunächst lesend; unterschiedliche Versionen und benutzerdefinierte Stile erkennen, unbekannte Formate erhalten, Synopsen separat, eigene IDs, Snapshots und letzte gültige Fassung; keine automatische externe KI-Anfrage bei jedem Speichern, kein Überschreiben von Originalen. Keine unbestätigte Plugin-Schnittstelle voraussetzen.

## Qualität und Arbeitsorganisation
Lokale Ollama-Modelle und optionale externe Anbieter ergebnisoffen testen. Vergleich A: normaler Chat, B: Wissenskarten, C: mehrstufiges Verfahren; gleiche Modellversion, Kandidatenzahl und vergleichbarer Aufwand, anonymisierte Autorbewertung (Originalität, Faszination, Kohärenz, emotionale Bedeutung, Hörspielpotenzial, Weiterentwicklungswunsch). Separat technische Tests, Kosten, Latenz, Fehler und strukturelle Vielfalt erfassen. Keine Benchmarks behaupten. Synthetische öffentliche Fixtures; private Referenzwerke ausschließlich lokal. Keine unfreigegebene externe Übermittlung. Masterplan kompakt halten; Forschung archivieren, nur relevante Erkenntnisse konsolidieren. Pro Codex-Auftrag Ziel, Nicht-Ziele, Tests und Bericht. Siehe tasks/P0_Auftragsplan.md und research/08_Technische_Architektur.md.
