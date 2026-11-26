"""V02: mehrere unverbindliche Hörspiel-Stoffkeime aus einem Modellaufruf."""

import json
import re
import threading
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from .dialogue import Dialogue
from .memory import ConflictError, Memory, NotFoundError
from .models import Idea, Proposal, Snapshot
from .narrative_library import CardSelection, NarrativeLibrary
from .providers import InvalidModelResponse, ModelCancelled, ModelProvider


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Stoffkeim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: Text
    premise: Text
    narrative_promise: Text
    mechanism: Text
    mechanism_card_id: str | None
    central_mystery: str | None
    personal_conflict: Text
    development: Text
    audio_potential: Text
    fictional_assumptions: list[Text]
    research_questions: list[Text]
    weaknesses: list[Text]
    used_card_ids: list[str]


class _StoffkeimAntwort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Text
    premise: Text
    narrative_promise: Text
    mechanism: Text
    mechanism_card_id: str | None
    central_mystery: str | None
    personal_conflict: Text
    development: Text
    audio_potential: Text
    fictional_assumptions: list[Text]
    research_questions: list[Text]
    weaknesses: list[Text]
    used_card_ids: list[str]


class _StoffAntwort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_revision_id: UUID
    candidates: list[_StoffkeimAntwort] = Field(min_length=2)


class Reflexion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strengths: list[Text] = Field(min_length=1)
    risks: list[Text] = Field(min_length=1)
    questions: list[Text] = Field(min_length=1)


@dataclass(frozen=True)
class StoffschmiedeErgebnis:
    id: UUID
    project_id: UUID
    branch_id: UUID
    base_revision_id: UUID
    model: str
    candidates: tuple[Stoffkeim, ...]
    reflection: Reflexion | None
    manifest: dict


class Stoffschmiede:
    def __init__(self, memory: Memory, provider: ModelProvider, library: NarrativeLibrary,
                 *, max_context_chars: int = 30_000, timeout_seconds: float = 60.0):
        self.memory = memory
        self.library = library
        self.dialogue = Dialogue(memory, provider, max_context_chars=max_context_chars,
                                 timeout_seconds=timeout_seconds)

    def select_cards(self, task: str, *, limit: int = 4) -> CardSelection:
        """Exakte Treffer vorziehen; pro Kategorie höchstens eine erste Karte."""
        if not task.strip() or not 2 <= limit <= 5:
            raise ValueError("Aufgabe und Kartenlimit zwischen 2 und 5 erforderlich")
        terms = set(re.findall(r"\w+", task.casefold()))
        categories = ("M", "N", "A", "D")
        chosen = []
        reasons = []
        for exact in (True, False):
            for category in categories:
                if len(chosen) >= limit or any(card.category == category for card in chosen):
                    continue
                options = self.library.select("stoffidee", categories={category},
                                              keywords=terms if exact else None, limit=1).cards
                if options:
                    chosen.append(options[0])
                    reasons.append(f"{options[0].id}@{options[0].version}: " +
                                   ("exakter Aufgabenbegriff" if exact else "Fallback ohne Schlagworttreffer"))
        if len(chosen) < limit:
            for card in self.library.select("stoffidee", limit=limit).cards:
                if len(chosen) >= limit:
                    break
                if card.id not in {item.id for item in chosen}:
                    chosen.append(card)
                    reasons.append(f"{card.id}@{card.version}: zusätzliche Alternative")
        matched_terms = {term for card in chosen for term in card.keywords if term.casefold() in terms}
        return CardSelection(cards=tuple(chosen), task_type="stoffidee",
                             categories=categories, keywords=tuple(sorted(matched_terms)),
                             reasons=tuple(reasons))

    def develop(self, project_id: UUID, branch_id: UUID, task: str, *, count: int = 3,
                card_limit: int = 4, reflect: bool = False,
                cancel: threading.Event | None = None) -> StoffschmiedeErgebnis:
        if not 2 <= count <= 5:
            raise ValueError("Zwei bis fünf Stoffkeime erforderlich")
        selection = self.select_cards(task, limit=max(count, card_limit))
        assignments = [selection.cards[index].id if index < len(selection.cards) else None
                       for index in range(count)]
        guidance = (f"Entwickle genau {count} eigenständige Hörspielprämissen als JSON. "
                    "Jede Prämisse braucht einen anderen zentralen narrativen Mechanismus; "
                    "Namen, Orte oder Berufe allein zählen nicht als Unterschied. "
                    "Schreibe kurze Stoffkeime, keine Drehbücher. Wissenskarten sind Anregungen. "
                    "Nutze ausschließlich tatsächlich übermittelte Karten-IDs. "
                    "Für Kandidat 1 bis N gelten als unterschiedliche Ausgangspunkte diese Karten-IDs "
                    f"(null bedeutet frei und ohne Karte): {json.dumps(assignments)}. "
                    "Setze mechanism_card_id entsprechend und führe diese ID in used_card_ids auf. "
                    "base_revision_id muss die aktuelle Kontextrevision sein. ")
        result = self.dialogue.ask(project_id, branch_id, guidance + "\nAutoraufgabe: " + task,
                                   cards=selection, format_schema=_StoffAntwort.model_json_schema(),
                                   persist=False, cancel=cancel)
        try:
            answer = _StoffAntwort.model_validate_json(result.answer)
        except (ValidationError, ValueError) as error:
            raise InvalidModelResponse("Ungültige Stoffkeim-Antwort") from error
        if answer.base_revision_id != UUID(result.manifest["revision_id"]):
            raise ConflictError("Stoffkeime beziehen sich auf eine andere Revision")
        if len(answer.candidates) != count:
            raise InvalidModelResponse("Falsche Anzahl an Stoffkeimen")
        allowed = {card.id for card in selection.cards}
        mechanisms = set()
        for index, candidate in enumerate(answer.candidates):
            if len(candidate.used_card_ids) != len(set(candidate.used_card_ids)) or \
                    not set(candidate.used_card_ids).issubset(allowed):
                raise InvalidModelResponse("Unbekannte oder doppelte Wissenskarten-ID")
            if candidate.mechanism_card_id != assignments[index]:
                raise InvalidModelResponse("Narrativer Ausgangsmechanismus stimmt nicht mit der Vorgabe überein")
            if candidate.mechanism_card_id and candidate.mechanism_card_id not in candidate.used_card_ids:
                raise InvalidModelResponse("Mechanismuskarte fehlt bei verwendeten Karten")
            key = candidate.mechanism.casefold()
            if key in mechanisms:
                raise InvalidModelResponse("Narrative Mechanismen müssen unterscheidbar benannt sein")
            mechanisms.add(key)
        candidates = tuple(Stoffkeim(id=uuid4(), **item.model_dump()) for item in answer.candidates)
        reflection = None
        reflection_metrics = None
        if reflect:
            if cancel is not None and cancel.is_set():
                raise ModelCancelled("Anfrage abgebrochen")
            reflection_task = ("Prüfe diese unverbindlichen Stoffkeime kritisch, ohne sie zu ändern. "
                               "Nenne konkrete Stärken, Risiken und offene Fragen; keine Kreativitätsnote. "
                               + json.dumps([item.model_dump(mode="json") for item in candidates], ensure_ascii=False))
            reflected = self.dialogue.ask(project_id, branch_id, reflection_task, cards=selection,
                                          format_schema=Reflexion.model_json_schema(), persist=False,
                                          cancel=cancel)
            if reflected.manifest["revision_id"] != result.manifest["revision_id"]:
                raise ConflictError("Projektstand änderte sich vor der Reflexion")
            try:
                reflection = Reflexion.model_validate_json(reflected.answer)
            except (ValidationError, ValueError) as error:
                raise InvalidModelResponse("Ungültige Reflexion") from error
            reflection_metrics = {"model": reflected.model, "duration_seconds": reflected.duration_seconds,
                                  "prompt_tokens": reflected.prompt_tokens, "output_tokens": reflected.output_tokens}
        manifest = {**result.manifest, "procedure": "V02", "mechanism_assignments": assignments}
        metrics = {"generation": {"duration_seconds": result.duration_seconds,
                                  "prompt_tokens": result.prompt_tokens,
                                  "output_tokens": result.output_tokens}}
        if reflection_metrics is not None:
            metrics["reflection"] = reflection_metrics
        if cancel is not None and cancel.is_set():
            raise ModelCancelled("Anfrage abgebrochen")
        run_id = self.memory.save_creative_run(project_id, branch_id, answer.base_revision_id,
                                                result.model, task, manifest,
                                                [item.model_dump(mode="json") for item in candidates],
                                                reflection.model_dump(mode="json") if reflection else None,
                                                metrics)
        return StoffschmiedeErgebnis(id=run_id, project_id=project_id, branch_id=branch_id,
                                     base_revision_id=answer.base_revision_id, model=result.model,
                                     candidates=candidates, reflection=reflection, manifest=manifest)

    def stage_candidate(self, run_id: UUID, candidate_id: UUID) -> Proposal:
        """Erstellt nach bewusster Auswahl einen SF-001-Entwurf, niemals eine Freigabe."""
        run = self.memory.get_creative_run(run_id)
        candidate = next((item for item in run["candidates"] if item["id"] == str(candidate_id)), None)
        if candidate is None:
            raise NotFoundError(candidate_id)
        seed = Stoffkeim.model_validate(candidate)
        base_id = UUID(run["revision_id"])
        base = self.memory.get_revision(base_id)
        idea = Idea(id=uuid4(), title=seed.title, premise=seed.premise,
                    mechanism=seed.mechanism)
        snapshot = Snapshot(ideas=[*base.snapshot.ideas, idea], decisions=base.snapshot.decisions)
        return self.memory.propose(UUID(run["branch_id"]), base_id, snapshot,
                                   f"Ausgewählter Stoffkeim {seed.id}")
