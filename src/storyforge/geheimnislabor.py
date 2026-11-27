"""V03: unverbindliche, strukturierte Mystery-Entwürfe auf bestehendem Projektkontext."""

import json
import re
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, model_validator

from .dialogue import Dialogue
from .memory import ConflictError, Memory, NotFoundError
from .narrative_library import CardSelection, NarrativeLibrary
from .providers import InvalidModelResponse, ModelCancelled, ModelProvider
from .stoffschmiede import Reflexion

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Arbeitsweise(str, Enum):
    RUECKWAERTS = "rueckwaerts"
    VORWAERTS = "vorwaerts"
    ALTERNATIVEN = "alternativen"
    PRUEFUNG = "pruefung"


class Beobachtung(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    beschreibung: Text


class Interpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beobachtung_id: UUID
    deutung: Text


class Hypothese(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    bezeichnung: Text
    verborgener_mechanismus: Text | None = None
    notwendige_annahmen: list[Text] = Field(default_factory=list)
    widersprueche: list[Text] = Field(default_factory=list)
    offene_fragen: list[Text] = Field(default_factory=list)
    hinweise: list[Text] = Field(default_factory=list)
    falsche_faehrten: list[Text] = Field(default_factory=list)
    vorbereitung: Text | None = None
    enthuellung: Text | None = None
    emotionale_folgen: list[Text] = Field(default_factory=list)
    hoerspielpotenzial: Text | None = None
    recherchebedarf: list[Text] = Field(default_factory=list)
    verwendete_karten_ids: list[str] = Field(default_factory=list)


class MatrixEintrag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beobachtung_id: UUID
    hypothese_id: UUID
    zustand: Annotated[str, StringConstraints(pattern=r"^(erklärt|zusätzliche Annahme erforderlich|widerspricht|ungeklärt)$")]
    begruendung: Text


class Schutzpruefung(BaseModel):
    model_config = ConfigDict(extra="forbid")
    element: Text
    status: Annotated[str, StringConstraints(pattern=r"^(bewahrt|verletzt|ungeklärt)$")]
    begruendung: Text


class Geheimnismodell(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beobachtungen: list[Beobachtung] = Field(min_length=1)
    interpretationen: list[Interpretation] = Field(default_factory=list)
    hypothesen: list[Hypothese] = Field(min_length=1)
    matrix: list[MatrixEintrag]
    bewusst_mehrdeutig: bool = False
    schutzpruefungen: list[Schutzpruefung] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_links(self):
        observations = [item.id for item in self.beobachtungen]
        hypotheses = [item.id for item in self.hypothesen]
        if len(observations) != len(set(observations)) or len(hypotheses) != len(set(hypotheses)):
            raise ValueError("Doppelte Beobachtungs- oder Hypothesen-ID")
        if any(item.beobachtung_id not in observations for item in self.interpretationen):
            raise ValueError("Interpretation verweist auf unbekannte Beobachtung")
        pairs = [(item.beobachtung_id, item.hypothese_id) for item in self.matrix]
        if len(pairs) != len(set(pairs)) or set(pairs) != {(o, h) for o in observations for h in hypotheses}:
            raise ValueError("Matrix benötigt genau eine begründete Zuordnung pro Beobachtung und Hypothese")
        elements = [item.element for item in self.schutzpruefungen]
        if len(elements) != len(set(elements)):
            raise ValueError("Doppelte Schutzprüfung")
        return self


@dataclass(frozen=True)
class GeheimnisErgebnis:
    id: UUID
    project_id: UUID
    branch_id: UUID
    base_revision_id: UUID
    mode: Arbeitsweise
    model: str
    entwurf: Geheimnismodell
    autor_wahrheit: str | None
    reflexion: Reflexion | None
    manifest: dict


class Geheimnislabor:
    def __init__(self, memory: Memory, provider: ModelProvider, library: NarrativeLibrary,
                 *, max_context_chars: int = 30_000, timeout_seconds: float = 60.0):
        self.memory = memory
        self.library = library
        self.dialogue = Dialogue(memory, provider, max_context_chars=max_context_chars,
                                 timeout_seconds=timeout_seconds)

    def select_cards(self, task: str, *, limit: int = 4,
                     card_ids: tuple[str, ...] = ()) -> CardSelection:
        if not task.strip() or not 1 <= limit <= 5:
            raise ValueError("Aufgabe und Kartenlimit zwischen 1 und 5 erforderlich")
        if len(card_ids) > limit or len(set(card_ids)) != len(card_ids):
            raise ValueError("Zu viele oder doppelte Karten-IDs")
        cards = []
        reasons = []
        for card_id in card_ids:
            card = self.library.get(card_id)
            cards.append(card)
            reasons.append(f"{card.id}@{card.version}: gezielt vom Autor gewählt")
        terms = set(re.findall(r"\w+", task.casefold()))
        for category in ("M", "N", "A", "D"):
            if len(cards) >= limit:
                break
            if any(card.category == category for card in cards):
                continue
            task_type = "dramaturgie" if category == "D" else "geheimnis"
            matched = self.library.select(task_type, categories={category}, keywords=terms, limit=1).cards
            fallback = self.library.select(task_type, categories={category}, limit=1).cards
            option = next((card for card in matched + fallback if card.id not in card_ids), None)
            if option:
                cards.append(option)
                reasons.append(f"{option.id}@{option.version}: " +
                               ("exakter Aufgabenbegriff" if option in matched else "Fallback ohne Schlagworttreffer"))
        return CardSelection(cards=tuple(cards), task_type="geheimnis",
                             categories=("M", "N", "A", "D"),
                             keywords=tuple(sorted({term for card in cards for term in card.keywords
                                                    if term.casefold() in terms})), reasons=tuple(reasons))

    def develop(self, project_id: UUID, branch_id: UUID, task: str, *, mode: Arbeitsweise,
                observations: tuple[Beobachtung, ...] = (), given_truth: str | None = None,
                card_ids: tuple[str, ...] = (), card_limit: int = 4, reflect: bool = False,
                cancel: threading.Event | None = None) -> GeheimnisErgebnis:
        mode = Arbeitsweise(mode)
        if mode == Arbeitsweise.VORWAERTS and not (given_truth and given_truth.strip()):
            raise ValueError("Vorwärtsentwicklung braucht eine vom Autor vorgegebene verborgene Wahrheit")
        if given_truth is not None and mode != Arbeitsweise.VORWAERTS:
            raise ValueError("Vorgegebene Wahrheit nur bei Vorwärtsentwicklung")
        if len({item.id for item in observations}) != len(observations):
            raise ValueError("Doppelte Eingangsbeobachtungen")
        selection = self.select_cards(task, limit=card_limit, card_ids=card_ids)
        branch = next((item for item in self.memory.list_branches(project_id) if item.id == branch_id), None)
        if branch is None:
            raise NotFoundError(branch_id)
        revision = self.memory.get_revision(branch.head_id)
        protected = sorted({element for idea in revision.snapshot.ideas
                            for element in idea.protected_elements})
        instructions = {
            Arbeitsweise.RUECKWAERTS: "Entwickle mindestens zwei konkurrierende, grundverschiedene Erklärungen aus Beobachtungen.",
            Arbeitsweise.VORWAERTS: "Leite aus der Autorvorgabe Beobachtungen, Hinweise und wahre, aber falsch gedeutete Fährten ab.",
            Arbeitsweise.ALTERNATIVEN: "Entwickle mindestens zwei alternative Auflösungen bei Beachtung aller geschützten Elemente.",
            Arbeitsweise.PRUEFUNG: "Untersuche eine bestehende Erklärung kritisch; eine einzelne Hypothese genügt.",
        }[mode]
        guidance = (instructions + " Eine faszinierende Auflösung zählt ebenso wie das Rätsel. "
                    "Überraschungen sollen Beobachtungen sinnvoll umdeuten. Vermeide willkürliche Zusatzannahmen; "
                    "beachte emotionale Folgen und hörbare Informationsvermittlung. Lasse kontrollierte Mehrdeutigkeit zu. "
                    "Unterscheide Beobachtung, Interpretation und Hypothese. Bestätigte fiktionale Wahrheit kommt "
                    "ausschließlich vom Autor; behaupte sie nicht selbst. Wissenschaftliche Spekulation ist kein gesichertes Wissen. "
                    "Ordne jede Beobachtung jeder Hypothese begründet zu; Ungeklärtes bleibt ungeklärt. "
                    "Wissenskarten sind freie Anregungen, keine Dramaturgieschablone. "
                    "Nutze nur übermittelte Karten-IDs. Liefere ausschließlich JSON nach Schema. ")
        if observations:
            guidance += "Autorbeobachtungen mit unveränderten IDs und Texten übernehmen: " + json.dumps(
                [item.model_dump(mode="json") for item in observations], ensure_ascii=False) + ". "
        if given_truth:
            guidance += "Vom Autor vorgegebene, nur für diesen Entwurf gültige fiktionale Wahrheit: " + given_truth + ". "
        if protected:
            guidance += ("Geschützte Elemente je einzeln in schutzpruefungen als bewahrt, verletzt oder ungeklärt "
                         "mit Begründung dokumentieren: " + json.dumps(protected, ensure_ascii=False) + ". ")
        result = self.dialogue.ask(project_id, branch_id, guidance + "\nAutoraufgabe: " + task,
                                   cards=selection, format_schema=Geheimnismodell.model_json_schema(),
                                   persist=False, cancel=cancel)
        try:
            draft = Geheimnismodell.model_validate_json(result.answer)
        except (ValidationError, ValueError) as error:
            raise InvalidModelResponse("Ungültiges Geheimnismodell") from error
        if result.manifest["revision_id"] != str(revision.id):
            raise ConflictError("Projektstand änderte sich vor der Modellausführung")
        if observations and {item.id: item.beschreibung for item in observations}.items() - {
                item.id: item.beschreibung for item in draft.beobachtungen}.items():
            raise InvalidModelResponse("Autorbeobachtungen fehlen oder wurden verändert")
        if mode in (Arbeitsweise.RUECKWAERTS, Arbeitsweise.ALTERNATIVEN) and len(draft.hypothesen) < 2:
            raise InvalidModelResponse("Mindestens zwei konkurrierende Hypothesen erforderlich")
        if {item.element for item in draft.schutzpruefungen} != set(protected):
            raise InvalidModelResponse("Geschützte Elemente nicht vollständig geprüft")
        allowed = {card.id for card in selection.cards}
        for hypothesis in draft.hypothesen:
            used = hypothesis.verwendete_karten_ids
            if len(used) != len(set(used)) or not set(used).issubset(allowed):
                raise InvalidModelResponse("Unbekannte oder doppelte Wissenskarten-ID")
        reflection = None
        if reflect:
            reflected = self.dialogue.ask(project_id, branch_id,
                                          "Prüfe diesen unverbindlichen Geheimnisentwurf kritisch; "
                                          "nenne Stärken, Risiken und offene Fragen. Ändere ihn nicht. " +
                                          draft.model_dump_json(), cards=selection,
                                          format_schema=Reflexion.model_json_schema(),
                                          persist=False, cancel=cancel)
            if reflected.manifest["revision_id"] != result.manifest["revision_id"]:
                raise ConflictError("Projektstand änderte sich vor der Reflexion")
            try:
                reflection = Reflexion.model_validate_json(reflected.answer)
            except (ValidationError, ValueError) as error:
                raise InvalidModelResponse("Ungültige Reflexion") from error
        if cancel is not None and cancel.is_set():
            raise ModelCancelled("Anfrage abgebrochen")
        current = next(item for item in self.memory.list_branches(project_id) if item.id == branch_id)
        if current.head_id != revision.id:
            raise ConflictError("Projektstand änderte sich während der Geheimnisentwicklung")
        manifest = {**result.manifest, "procedure": "V03", "mode": mode.value,
                    "protected_elements": protected,
                    "author_observation_ids": [str(item.id) for item in observations],
                    "author_given_truth": given_truth}
        run_id = self.memory.save_creative_run(project_id, branch_id, revision.id, result.model, task,
                                                manifest, [draft.model_dump(mode="json")],
                                                reflection.model_dump(mode="json") if reflection else None,
                                                {"generation": {"duration_seconds": result.duration_seconds,
                                                                "prompt_tokens": result.prompt_tokens,
                                                                "output_tokens": result.output_tokens}})
        return GeheimnisErgebnis(run_id, project_id, branch_id, revision.id, mode, result.model,
                                 draft, given_truth, reflection, manifest)

    def get_result(self, run_id: UUID) -> GeheimnisErgebnis:
        run = self.memory.get_creative_run(run_id)
        manifest = run["manifest"]
        if manifest.get("procedure") != "V03" or len(run["candidates"]) != 1:
            raise ValueError("Kein Geheimnislabor-Ergebnis")
        return GeheimnisErgebnis(run_id, UUID(run["project_id"]), UUID(run["branch_id"]),
                                 UUID(run["revision_id"]), Arbeitsweise(manifest["mode"]),
                                 run["model"], Geheimnismodell.model_validate(run["candidates"][0]),
                                 manifest["author_given_truth"],
                                 Reflexion.model_validate(run["reflection"]) if run["reflection"] else None,
                                 manifest)
