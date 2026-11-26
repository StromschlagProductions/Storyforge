"""Validierte, absichtlich kleine Datenverträge für SF-001."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Idea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1)
    premise: str = Field(min_length=1)
    mechanism: str = ""
    protected_elements: list[str] = Field(default_factory=list)
    status: str = "offen"


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    target: str = Field(min_length=1)
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    author: str = Field(min_length=1)


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ideas: list[Idea] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1)
    work_id: UUID
    work_title: str = Field(min_length=1)
    universe_id: UUID | None = None
    universe_title: str | None = None


class Revision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    branch_id: UUID
    parent_id: UUID | None
    created_at: str
    author: str
    description: str
    content_hash: str
    snapshot: Snapshot


class Branch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    name: str
    head_id: UUID


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    branch_id: UUID
    base_revision_id: UUID
    description: str
    snapshot: Snapshot
    status: str
