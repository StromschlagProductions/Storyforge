"""SF-005: lokaler, verblindeter Qualitätspilot mit synthetischen Fällen."""

import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from .autorenredaktion import Autorenredaktion, Mutationsantwort, Operation, Quelle
from .dialogue import Dialogue
from .memory import Memory
from .narrative_library import NarrativeLibrary
from .providers import InvalidModelResponse, ModelCancelled, ModelProvider
from .stoffschmiede import Stoffschmiede, _StoffAntwort

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CASES = Path.cwd() / "pilot" / "cases"
CARDS = Path.cwd() / "library" / "cards"


class PilotCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Annotated[str, StringConstraints(pattern=r"^T0[1-6]$")]
    version: int = Field(ge=1, strict=True)
    title: Text
    kind: Literal["stoff", "mutation"]
    count: int = Field(ge=1, le=5)
    task: Text
    source: str | None
    protected: list[Text]


class PilotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    model: Text
    temperature: float = Field(ge=0, le=2)
    num_predict: int = Field(ge=128, le=4096)
    repetitions: int = Field(ge=1, le=5)


class PilotRating(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fascination: int | None = Field(default=None, ge=1, le=5)
    originality: int | None = Field(default=None, ge=1, le=5)
    mystery: int | None = Field(default=None, ge=1, le=5)
    logic: int | None = Field(default=None, ge=1, le=5)
    emotion: int | None = Field(default=None, ge=1, le=5)
    audio: int | None = Field(default=None, ge=1, le=5)
    develop: int | None = Field(default=None, ge=1, le=5)
    notes: str = ""


class PilotLab:
    def __init__(self, database: str | Path, provider_factory, *,
                 cases: str | Path = CASES, cards: str | Path = CARDS):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.core = Memory(self.path.with_name(self.path.stem + "-core.sqlite3"))
        self.library = NarrativeLibrary.load(cards)
        self.provider_factory = provider_factory
        loaded = [PilotCase.model_validate_json(path.read_text(encoding="utf-8"))
                  for path in sorted(Path(cases).glob("*.json"))]
        if len(loaded) != 6 or len({case.id for case in loaded}) != 6:
            raise ValueError("Sechs eindeutige Pilotfälle erforderlich")
        self.cases = {case.id: case for case in loaded}
        with self._db() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY, case_id TEXT NOT NULL, case_version INTEGER NOT NULL,
                case_payload TEXT NOT NULL,
                model TEXT NOT NULL, parameters TEXT NOT NULL, repetitions INTEGER NOT NULL,
                project_id TEXT NOT NULL, branch_id TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, group_id TEXT NOT NULL REFERENCES groups(id),
                blind_id TEXT NOT NULL UNIQUE, blind_order TEXT NOT NULL,
                arm TEXT NOT NULL CHECK(arm IN ('A','B','C')), repetition INTEGER NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, result TEXT, manifest TEXT,
                metrics TEXT, error TEXT, UNIQUE(group_id,arm,repetition));
                CREATE TABLE IF NOT EXISTS ratings (
                run_id TEXT PRIMARY KEY REFERENCES runs(id), value TEXT NOT NULL, created_at TEXT NOT NULL);""")

    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def create_group(self, config: PilotConfig) -> str:
        if config.case_id not in self.cases:
            raise ValueError("Unbekannter Testfall")
        case = self.cases[config.case_id]
        project = self.core.create_project("Synthetischer Pilot " + case.id)
        branch = self.core.list_branches(project.id)[0]
        group_id = str(uuid4())
        params = {"temperature": config.temperature, "num_predict": config.num_predict}
        with self._db() as db, db:
            db.execute("INSERT INTO groups VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (group_id, case.id, case.version, case.model_dump_json(), config.model,
                        json.dumps(params), config.repetitions, str(project.id),
                        str(branch.id), _now()))
        return group_id

    def _group(self, group_id: str) -> dict:
        with self._db() as db:
            row = db.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
        if row is None:
            raise KeyError(group_id)
        return {**dict(row), "parameters": json.loads(row["parameters"]),
                "case": PilotCase.model_validate_json(row["case_payload"])}

    def execute(self, group_id: str, arm: Literal["A", "B", "C"], repetition: int,
                cancel: threading.Event | None = None) -> str:
        group = self._group(group_id)
        if arm not in {"A", "B", "C"} or not 1 <= repetition <= group["repetitions"]:
            raise ValueError("Ungültiges Verfahren oder Wiederholung")
        case = group["case"]
        run_id, blind_id = str(uuid4()), str(uuid4())
        try:
            with self._db() as db, db:
                db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (run_id, group_id, blind_id, secrets.token_hex(12), arm, repetition,
                            "läuft", _now(), None, None, None, None))
        except sqlite3.IntegrityError as error:
            raise ValueError("Dieser Lauf wurde bereits gestartet") from error
        provider = None
        try:
            provider = _RecordingProvider(self.provider_factory(group["model"], group["parameters"]))
            result, manifest, metrics = self._generate(group, case, arm, cancel, provider)
            if cancel is not None and cancel.is_set():
                raise ModelCancelled("Pilotlauf abgebrochen")
            with self._db() as db, db:
                db.execute("UPDATE runs SET status='fertig',result=?,manifest=?,metrics=? WHERE id=?",
                           (json.dumps(result, ensure_ascii=False), json.dumps(manifest, ensure_ascii=False),
                            json.dumps(metrics), run_id))
        except Exception as error:
            failure_metrics = {"model": group["model"], "model_parameters": group["parameters"],
                               "calls": len(provider.requests) if provider else 0,
                               "optional_reflection_calls": 0}
            with self._db() as db, db:
                db.execute("UPDATE runs SET status=?,error=?,metrics=?,manifest=? WHERE id=?",
                           ("abgebrochen" if isinstance(error, ModelCancelled) else "fehler",
                            f"{type(error).__name__}: {error}", json.dumps(failure_metrics),
                            json.dumps({"case_version": case.version,
                                        "transmitted_requests": provider.requests if provider else []},
                                       ensure_ascii=False), run_id))
            raise
        return run_id

    def _generate(self, group: dict, case: PilotCase, arm: str, cancel, provider: ModelProvider):
        project_id, branch_id = UUID(group["project_id"]), UUID(group["branch_id"])
        task = case.task + ("\nAusgangsmaterial: " + case.source if case.source else "")
        if case.protected:
            task += "\nZu erhalten: " + json.dumps(case.protected, ensure_ascii=False)
        selection = None
        if arm != "A":
            if case.kind == "stoff":
                selection = Stoffschmiede(self.core, provider, self.library).select_cards(task)
            else:
                selection = self.library.select("mutation", limit=4)
        start = monotonic()
        if arm in {"A", "B"}:
            schema = _StoffAntwort if case.kind == "stoff" else Mutationsantwort
            neutral = (f"Entwickle genau {case.count} kurze, unterscheidbare Hörspielansätze. "
                       "Fülle den gemeinsamen Ergebnisvertrag als JSON aus. "
                       "Keine zusätzliche Reflexion.\n" + task)
            if case.kind == "stoff":
                revision = self.core.get_revision(self.core.list_branches(project_id)[0].head_id)
                neutral += f"\nbase_revision_id: {revision.id}."
            reply = Dialogue(self.core, provider).ask(project_id, branch_id, neutral,
                                                     cards=selection, format_schema=schema.model_json_schema(),
                                                     persist=False, cancel=cancel)
            try:
                parsed = schema.model_validate_json(reply.answer)
            except (ValidationError, ValueError) as error:
                raise InvalidModelResponse("Ungültige Pilotantwort") from error
            items = parsed.candidates if case.kind == "stoff" else parsed.alternativen
            if len(items) != case.count:
                raise InvalidModelResponse("Falsche Kandidatenzahl")
            allowed_cards = {card.id for card in selection.cards} if selection else set()
            for item in items:
                used = set(item.used_card_ids if case.kind == "stoff" else item.verwendete_karten_ids)
                if used - allowed_cards or (case.kind == "stoff" and item.mechanism_card_id
                                            and item.mechanism_card_id not in allowed_cards):
                    raise InvalidModelResponse("Nicht übermittelte Wissenskarte verwendet")
                if case.kind == "mutation" and {check.element for check in item.schutzpruefungen} != set(case.protected):
                    raise InvalidModelResponse("Schutzprüfung unvollständig")
            if case.kind == "stoff":
                if parsed.base_revision_id != self.core.list_branches(project_id)[0].head_id:
                    raise InvalidModelResponse("Falsche Ausgangsrevision")
                candidates = [{"title": item.title, "description": item.premise,
                               "mechanism": item.mechanism, "audio_potential": item.audio_potential,
                               "details": item.model_dump(mode="json")}
                              for item in items]
            else:
                candidates = [{"title": item.bezeichnung, "description": item.kurzbeschreibung,
                               "mechanism": item.operation.value,
                               "audio_potential": "; ".join(item.hoerspielpotenzial) or "ungeklärt",
                               "details": item.model_dump(mode="json")}
                              for item in items]
            manifest = reply.manifest
            model = reply.model
            prompt_tokens, output_tokens = reply.prompt_tokens, reply.output_tokens
            duration = reply.duration_seconds
        elif case.kind == "stoff":
            run = Stoffschmiede(self.core, provider, self.library).develop(
                project_id, branch_id, case.task, count=case.count,
                card_limit=len(selection.cards), reflect=False, cancel=cancel)
            candidates = [{"title": item.title, "description": item.premise,
                           "mechanism": item.mechanism, "audio_potential": item.audio_potential,
                           "details": item.model_dump(mode="json", exclude={"id"})}
                          for item in run.candidates]
            manifest = run.manifest
            model = run.model
            stored = self.core.get_creative_run(run.id)["metrics"]["generation"]
            prompt_tokens, output_tokens = stored["prompt_tokens"], stored["output_tokens"]
            duration = stored["duration_seconds"]
        else:
            run = Autorenredaktion(self.core, provider, self.library).mutate(
                project_id, branch_id, case.task, Quelle(art="frei", beschreibung=case.source),
                operation=Operation.FREI, erhalten=tuple(case.protected),
                card_ids=tuple(card.id for card in selection.cards),
                card_limit=len(selection.cards), cancel=cancel)
            if len(run.result.alternativen) != case.count:
                raise InvalidModelResponse("Falsche Kandidatenzahl")
            candidates = [{"title": item.bezeichnung, "description": item.kurzbeschreibung,
                           "mechanism": item.operation.value,
                           "audio_potential": "; ".join(item.hoerspielpotenzial) or "ungeklärt",
                           "details": item.model_dump(mode="json")}
                          for item in run.result.alternativen]
            manifest = run.manifest
            model = run.model
            stored = self.core.get_creative_run(run.id)["metrics"]["generation"]
            prompt_tokens, output_tokens = stored["prompt_tokens"], stored["output_tokens"]
            duration = stored["duration_seconds"]
        if cancel is not None and cancel.is_set():
            raise ModelCancelled("Pilotlauf abgebrochen")
        metrics = {"model": model, "model_parameters": group["parameters"],
                   "calls": len(provider.requests), "optional_reflection_calls": 0,
                   "duration_seconds": duration, "wall_seconds": monotonic() - start,
                   "prompt_tokens": prompt_tokens, "output_tokens": output_tokens,
                   "input_characters": sum(len(json.dumps(r["messages"], ensure_ascii=False)) for r in provider.requests),
                   "output_characters": sum(len(r.content) for r in provider.responses)}
        manifest = {"creative_context": manifest, "transmitted_requests": provider.requests,
                    "case_version": case.version, "procedure": arm == "C"}
        return candidates, manifest, metrics

    def blind_runs(self, group_id: str) -> list[dict]:
        self._group(group_id)
        with self._db() as db:
            rows = db.execute("SELECT id,blind_id,status,result,error FROM runs WHERE group_id=? "
                              "ORDER BY blind_order", (group_id,)).fetchall()
            rated = {row[0] for row in db.execute("SELECT run_id FROM ratings")}
        return [{"blind_id": row["blind_id"], "status": row["status"],
                 "candidates": json.loads(row["result"]) if row["result"] else None,
                 "error": "Lauf fehlgeschlagen" if row["status"] == "fehler" else
                          ("Lauf abgebrochen" if row["status"] == "abgebrochen" else None),
                 "rated": row["id"] in rated} for row in rows]

    def rate(self, blind_id: str, rating: PilotRating):
        with self._db() as db, db:
            row = db.execute("SELECT id,status FROM runs WHERE blind_id=?", (blind_id,)).fetchone()
            if row is None or row["status"] != "fertig":
                raise ValueError("Nur fertige, verblindete Ergebnisse bewerten")
            db.execute("INSERT OR REPLACE INTO ratings VALUES (?,?,?)",
                       (row["id"], rating.model_dump_json(), _now()))

    def report(self, group_id: str, *, reveal: bool = False) -> dict:
        group = self._group(group_id)
        with self._db() as db:
            rows = db.execute("SELECT r.*,v.value AS rating FROM runs r LEFT JOIN ratings v ON v.run_id=r.id "
                              "WHERE r.group_id=? ORDER BY r.blind_order", (group_id,)).fetchall()
        if reveal and any(row["status"] == "fertig" and row["rating"] is None for row in rows):
            raise ValueError("Alle fertigen Ergebnisse müssen vor der Auflösung bewertet sein")
        data = []
        for row in rows:
            item = {"blind_id": row["blind_id"], "status": row["status"],
                    "candidates": json.loads(row["result"]) if row["result"] else None,
                    "rating": json.loads(row["rating"]) if row["rating"] else None,
                    "error": row["error"] if reveal else
                             ("Lauf fehlgeschlagen" if row["status"] == "fehler" else
                              ("Lauf abgebrochen" if row["status"] == "abgebrochen" else None))}
            if reveal:
                item.update({"arm": row["arm"], "repetition": row["repetition"],
                             "manifest": json.loads(row["manifest"]) if row["manifest"] else None,
                             "metrics": json.loads(row["metrics"]) if row["metrics"] else None})
            data.append(item)
        return {"schema_version": 1, "case": group["case"].model_dump(),
                "group_id": group_id, "model": group["model"],
                "model_parameters": group["parameters"], "repetitions": group["repetitions"],
                "revealed": reveal, "runs": data}

    def markdown(self, group_id: str, *, reveal: bool = False) -> str:
        report = self.report(group_id, reveal=reveal)
        lines = ["# STORYFORGE – Qualitätspilot", "", f"Testfall: {report['case']['id']} – {report['case']['title']}",
                 f"Modell: {report['model']}", f"Parameter: {json.dumps(report['model_parameters'])}",
                 f"Verfahren aufgelöst: {'ja' if reveal else 'nein'}", ""]
        for run in report["runs"]:
            lines += [f"## Ergebnis {run['blind_id']}", "", f"Status: {run['status']}"]
            if reveal:
                lines += [f"Verfahren: {run['arm']}, Wiederholung: {run['repetition']}",
                          f"Metriken: {json.dumps(run['metrics'], ensure_ascii=False)}",
                          "", "Kontextmanifest und tatsächlich übermittelte Nachrichten:", "```json",
                          json.dumps(run['manifest'], ensure_ascii=False, indent=2), "```"]
            for candidate in run["candidates"] or []:
                lines += ["", f"### {candidate['title']}", candidate["description"],
                          f"Mechanismus: {candidate['mechanism']}",
                          f"Hörspielpotenzial: {candidate['audio_potential']}", "",
                          "Vollständiges Ergebnis:", "```json",
                          json.dumps(candidate["details"], ensure_ascii=False, indent=2), "```"]
            if run["rating"]:
                lines += ["", "Bewertung: " + json.dumps(run["rating"], ensure_ascii=False)]
            if run["error"]:
                lines += ["", "Fehler: " + run["error"]]
            lines.append("")
        return "\n".join(lines)


def _now():
    return datetime.now(timezone.utc).isoformat()


class _RecordingProvider:
    """Erfasst den tatsächlich übermittelten Kontext ohne zweiten Modellaufruf."""

    def __init__(self, provider: ModelProvider):
        self.provider = provider
        self.model = provider.model
        self.capabilities = provider.capabilities
        self.requests: list[dict] = []
        self.responses = []

    def generate(self, request, cancel=None):
        self.requests.append({"messages": request.messages, "format_schema": request.format_schema,
                              "timeout_seconds": request.timeout_seconds})
        response = self.provider.generate(request, cancel=cancel)
        self.responses.append(response)
        return response
