"""Manueller lokaler Ollama-Smoke-Test mit ausschließlich synthetischem Projekt."""

import argparse
from pathlib import Path

from storyforge import Memory, NarrativeLibrary, OllamaProvider, Stoffschmiede


ROOT = Path(__file__).resolve().parents[1]


def format_result(run) -> str:
    lines = [f"Ergebnis: {run.id}", f"Modell: {run.model}",
             f"Ausgangsrevision: {run.base_revision_id}",
             f"Ausgewählte Karten: {run.manifest['cards']}", ""]
    labels = (("title", "Titel"), ("premise", "Prämisse"),
              ("narrative_promise", "Erzählerisches Versprechen"),
              ("mechanism", "Narrativer Mechanismus"),
              ("mechanism_card_id", "Mechanismuskarte"),
              ("central_mystery", "Zentrales Rätsel"),
              ("personal_conflict", "Persönlicher Konflikt"),
              ("development", "Entwicklung"), ("audio_potential", "Hörspielpotenzial"),
              ("fictional_assumptions", "Fiktionale Annahmen"),
              ("research_questions", "Recherchefragen"),
              ("weaknesses", "Schwächen"), ("used_card_ids", "Verwendete Karten"))
    for number, seed in enumerate(run.candidates, 1):
        lines.extend((f"=== Stoffkeim {number}: {seed.id} ===",))
        for field, label in labels:
            value = getattr(seed, field)
            if isinstance(value, list):
                value = "\n    - " + "\n    - ".join(value) if value else "(keine)"
            lines.append(f"{label}: {value if value is not None else '(keines)'}")
        lines.append("")
    if run.reflection is not None:
        lines.append("=== Optionale Reflexion ===")
        for field, label in (("strengths", "Stärken"), ("risks", "Risiken"),
                             ("questions", "Offene Fragen")):
            lines.append(f"{label}:\n    - " + "\n    - ".join(getattr(run.reflection, field)))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lokaler Stoffschmiede-Test mit synthetischem Projekt")
    parser.add_argument("--model", required=True, help="Name eines bereits installierten Ollama-Modells")
    parser.add_argument("--count", type=int, default=3, choices=range(2, 6))
    parser.add_argument("--reflect", action="store_true", help="Optionaler zweiter Modellaufruf")
    parser.add_argument("--database", type=Path, default=ROOT / "local" / "stoffschmiede-smoke.sqlite3")
    args = parser.parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)
    memory = Memory(args.database)
    project = memory.create_project("Synthetischer Hörspieltest")
    branch = memory.list_branches(project.id)[0]
    library = NarrativeLibrary.load(ROOT / "library" / "cards")
    forge = Stoffschmiede(memory, OllamaProvider(args.model), library)
    run = forge.develop(project.id, branch.id,
                        "Entwickle unterschiedliche Hörspielansätze um ein rätselhaftes Geräusch "
                        "in einer vollständig erfundenen Kleinstadt.",
                        count=args.count, reflect=args.reflect)
    print(format_result(run))
    print("Revisionskopf unverändert:", memory.list_branches(project.id)[0].head_id == branch.head_id)
    print("Ergebnis lokal gespeichert in:", args.database)


if __name__ == "__main__":
    main()
