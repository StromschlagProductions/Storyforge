# SF-001 – Ergebnis und Architekturentscheidungen

Stand: 26.11.2026. Grundlage: bereinigter Masterplan v1.0, P0-Auftragsplan und Forschungsbericht 08 dieses Repositorys. Nur synthetische Testdaten verwendet.

## Architektur

- `src/storyforge/models.py`: kleine Pydantic-Verträge für Projekt, Stoffidee, Autorenentscheidung, Snapshot, Revision, Variante und Entwurf. Stabile UUIDs identifizieren Projekte und Werke unabhängig von Titeln; ein Universum ist optional und kann von mehreren Projekten referenziert werden.
- `src/storyforge/memory.py`: SQLite-Speicher als lokaler modularer Monolith. `PRAGMA user_version` führt die initiale Schema-Migration aus. Fremdschlüssel sind pro Verbindung aktiv. Zeitstempel sind UTC; Revisionen enthalten vollständige JSON-Snapshots und SHA-256-Hashes.
- Jede Variante besitzt einen eigenen Revisionskopf. Eine neue Variante verweist zunächst auf die Quellrevision; spätere Freigaben bewegen nur ihren eigenen Kopf. Historische Revisionen bleiben unverändert.
- `propose` speichert einen Entwurf und prüft die Ausgangsrevision. `approve` verlangt eine ausdrückliche Autorfreigabe und führt Revision, Kopfwechsel und Statuswechsel in einer `BEGIN IMMEDIATE`-Transaktion aus. Bei veraltetem Kopf wird die gesamte Übernahme abgelehnt. Ablehnung verändert den Revisionskopf nicht.
- Autorenentscheidungen sind innerhalb der Variantengeschichte append-only: ein Entwurf darf vorhandene Entscheidungen weder entfernen noch ändern. Eine Wiederherstellung übernimmt alte Stoffideen, erhält aber die aktuellen Entscheidungen; sie braucht erneut Freigabe.
- JSON exportiert Projekt, Varianten und vollständige Revisionshistorie. Markdown exportiert die aktuellen Stände der Varianten für Menschen. Dateiexporte entstehen zuerst als temporäre Datei im Zielverzeichnis und werden dann mit `os.replace` übernommen.
- Die Exportdaten werden innerhalb einer SQLite-Lesetransaktion erfasst. Damit passen Variantenköpfe und exportierte Revisionen auch während konkurrierender Freigaben zusammen.

## Erstellte und geänderte Dateien

SF-001: `pyproject.toml`, `src/storyforge/__init__.py`, `src/storyforge/models.py`, `src/storyforge/memory.py`, `tests/test_memory.py`, diese Ergebnisdatei; `README.md` geändert. Abschlussprüfung: `memory.py` und `tests/test_memory.py` ergänzt; `.github/workflows/tests.yml` neu. Vorhandene `AGENTS.md`, `.gitignore` und Konzeptdokumente wurden geprüft und nicht verändert.

## Tests

`.venv/bin/python -m pytest -q` in einer lokalen virtuellen Umgebung: **9 bestanden**. Tests decken einen vollständigen Prozessneustart, Migration, eindeutige Werke und Universumszuordnung, Variantenisolation, dauerhafte Entscheidungen, fehlende Autorfreigabe, atomaren Rollback bei Fehler, konkurrierende und abgelehnte Entwürfe, Wiederherstellung, ungültige Eingaben sowie JSON- und Markdown-Export ab. Der GitHub-Actions-Workflow prüft künftig Python 3.12 auf Linux und Windows; sein erster Windows-Lauf ist erst nach dem Push beobachtbar.

## Abschlussprüfung der Akzeptanzkriterien

1. Projekt ohne Skript, Speicherung, vollständiger Neustart: erfüllt; Test in zwei getrennten Python-Prozessen mit Umlautpfad.
2. Alternative Fassungen: erfüllt; eigener Variantenkopf, Original bleibt bei Freigabe einer Variante unverändert.
3. Autorenentscheidungen: erfüllt; in Snapshots gespeichert, nach Neustart erhalten und innerhalb einer Variante nicht entfernbar.
4. Atomare Freigabe: erfüllt; explizite Freigabe erforderlich, Rollback nach simuliertem Fehler geprüft.
5. Veraltete Revisionen: erfüllt; zweite Speicherinstanz kann einen überholten Entwurf nicht freigeben.
6. JSON/Markdown: erfüllt; aktuelle Variantenköpfe und Revisionshistorie konsistent gelesen, atomarer Dateiersatz mit Umlautpfad geprüft.
7. Automatisierte Kernfunktionstests: erfüllt; 9 pytest-Tests. Windows-Ausführung durch CI vorgesehen, Ergebnis nach erstem Lauf prüfen.

Vor der Veröffentlichung: ausschließlich bereinigte Konzeptdateien, Quellcode, synthetische Tests, README und Workflow aufgenommen. Keine Projekt-Datenbank, privaten Hörspielskripte, unveröffentlichten Stoffideen oder Zugangsdaten im Commit.

## Offene Fragen und Grenzen

- Es gibt noch keine Oberfläche und keinen Benutzerkonten-Nachweis. `approved_by` dokumentiert den angegebenen Namen; die tatsächliche Identität muss eine spätere lokale Oberfläche sicherstellen.
- JSON-Export ist ein portables Archiv; ein JSON-Import ist in SF-001 nicht implementiert. Wiederherstellung innerhalb der Datenbank erfolgt über `restore` und Freigabe. Eine regelmäßige Sicherung der SQLite-Datei bleibt Betriebsaufgabe.
- Der initiale Migrationsstand ist Version 1. Künftige Schemaänderungen benötigen explizite Folgemigrationen.

## Empfehlung für SF-002

Den Modelladapter und den kreativen Dialog an `propose` anbinden: Modellantworten nur als Entwürfe speichern, eine konkrete Ausgangsrevision mitgeben und Freigabe ausschließlich durch die Autorin oder den Autor auslösen. Kreative Entwicklung priorisieren; Fade In und Produktionsautomatisierung weiterhin zurückstellen.
