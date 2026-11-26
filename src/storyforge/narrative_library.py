"""Versionierte Wissenskarten und eine kleine deterministische Auswahl."""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CardId = Annotated[str, StringConstraints(pattern=r"^[MNDA][0-9]{2,}$")]


class KnowledgeCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CardId
    version: int = Field(ge=1, strict=True)
    category: Literal["M", "N", "D", "A"]
    name: NonEmpty
    principle: NonEmpty
    creative_instruction: NonEmpty
    applications: list[NonEmpty] = Field(min_length=1)
    quality_questions: list[NonEmpty] = Field(min_length=1)
    weaknesses: list[NonEmpty] = Field(min_length=1)
    audio_relevance: NonEmpty
    related_ids: list[CardId] = Field(default_factory=list)
    source: NonEmpty
    keywords: list[NonEmpty] = Field(min_length=1)
    task_types: list[NonEmpty] = Field(min_length=1)

    @model_validator(mode="after")
    def check_category(self):
        if self.id[0] != self.category:
            raise ValueError("Karten-ID und Kategorie widersprechen sich")
        if self.id in self.related_ids or len(self.related_ids) != len(set(self.related_ids)):
            raise ValueError("Ungültige verwandte Karten-IDs")
        return self

    @field_validator("keywords", "task_types")
    @classmethod
    def unique_terms(cls, value: list[str]) -> list[str]:
        if len({term.casefold() for term in value}) != len(value):
            raise ValueError("Doppelte Schlagwörter oder Aufgabenarten")
        return value


@dataclass(frozen=True)
class CardSelection:
    cards: tuple[KnowledgeCard, ...]
    task_type: str
    categories: tuple[str, ...]
    keywords: tuple[str, ...]
    reasons: tuple[str, ...]


class NarrativeLibrary:
    def __init__(self, cards: list[KnowledgeCard]):
        by_id: dict[str, KnowledgeCard] = {}
        for card in cards:
            if card.id in by_id:
                raise ValueError(f"Doppelte Karten-ID: {card.id}")
            by_id[card.id] = card
        for card in cards:
            for related_id in card.related_ids:
                if related_id not in by_id:
                    raise ValueError(f"Unbekannter Querverweis: {card.id} -> {related_id}")
        self._cards = by_id

    @classmethod
    def load(cls, directory: str | Path) -> "NarrativeLibrary":
        folder = Path(directory)
        if not folder.is_dir():
            raise ValueError(f"Kartenverzeichnis fehlt: {folder}")
        cards = []
        for path in sorted(folder.glob("*.json")):
            try:
                cards.append(KnowledgeCard.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, ValueError) as error:
                raise ValueError(f"Ungültige Wissenskarte in {path.name}: {error}") from error
        return cls(cards)

    def get(self, card_id: str) -> KnowledgeCard:
        return self._cards[card_id]

    def related(self, card_id: str) -> list[KnowledgeCard]:
        return [self._cards[related_id] for related_id in self.get(card_id).related_ids]

    def filter(self, *, categories: set[str] | None = None,
               keywords: set[str] | None = None) -> list[KnowledgeCard]:
        terms = {term.casefold() for term in keywords or set()}
        return [card for card in sorted(self._cards.values(), key=lambda item: item.id)
                if (categories is None or card.category in categories)
                and (not terms or terms.intersection(term.casefold() for term in card.keywords))]

    def select(self, task_type: str, *, categories: set[str] | None = None,
               keywords: set[str] | None = None, limit: int = 3) -> CardSelection:
        if not task_type.strip() or limit < 1:
            raise ValueError("Aufgabenart und positives Kartenlimit erforderlich")
        terms = {term.casefold() for term in keywords or set()}
        candidates = []
        for card in self.filter(categories=categories):
            if task_type.casefold() not in {kind.casefold() for kind in card.task_types}:
                continue
            matches = sorted(terms.intersection(term.casefold() for term in card.keywords))
            if terms and not matches:
                continue
            candidates.append((card, matches))
        candidates.sort(key=lambda entry: (-len(entry[1]), entry[0].id))
        chosen = candidates[:limit]
        return CardSelection(
            cards=tuple(card for card, _ in chosen), task_type=task_type,
            categories=tuple(sorted(categories or set())), keywords=tuple(sorted(terms)),
            reasons=tuple(f"{card.id}@{card.version}: Aufgabenart {task_type}; "
                          f"Schlagwörter {', '.join(matches) if matches else 'keine Vorgabe'}"
                          for card, matches in chosen),
        )
