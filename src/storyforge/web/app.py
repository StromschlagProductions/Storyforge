"""Schmale lokale HTTP-Brücke zu den bestehenden STORYFORGE-Verfahren."""

import json
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from storyforge import (Analysebereich, Arbeitsweise, Autorenredaktion, ConflictError, Dialogue,
                        FakeProvider, Geheimnislabor, Memory, NarrativeLibrary, NotFoundError, OllamaProvider,
                        Operation, Quelle, Snapshot, Stoffschmiede)

STATIC = Path(__file__).parent / "static"
CARDS = Path.cwd() / "library" / "cards"


class ProjectInput(BaseModel):
    title: str = Field(min_length=1)
    universe_title: str | None = None


class BranchInput(BaseModel):
    name: str = Field(min_length=1)
    from_revision_id: UUID


class JobInput(BaseModel):
    project_id: UUID
    branch_id: UUID
    procedure: str
    task: str = Field(min_length=1)
    model: str = Field(min_length=1)
    options: dict = Field(default_factory=dict)


class ApproveInput(BaseModel):
    author: str = Field(min_length=1)
    explicit_approval: bool


class AppService:
    def __init__(self, database: Path, library: Path = CARDS, provider_factory=OllamaProvider):
        self.memory = Memory(database)
        self.library = NarrativeLibrary.load(library)
        self.provider_factory = provider_factory
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="storyforge")
        self.jobs: dict[str, dict] = {}
        self.lock = threading.Lock()

    def launch(self, request: JobInput) -> str:
        if request.procedure not in {"V01", "V02", "V03", "V04", "V05"}:
            raise ValueError("Unbekanntes Verfahren")
        branch = next((b for b in self.memory.list_branches(request.project_id)
                       if b.id == request.branch_id), None)
        if branch is None:
            raise NotFoundError(request.branch_id)
        job_id = str(uuid4())
        cancel = threading.Event()
        with self.lock:
            self.jobs[job_id] = {"id": job_id, "project_id": str(request.project_id),
                                 "branch_id": str(request.branch_id), "status": "läuft",
                                 "cancel": cancel, "result": None, "error": None}
        self.executor.submit(self._work, job_id, request)
        return job_id

    def _work(self, job_id: str, request: JobInput):
        with self.lock:
            job = self.jobs[job_id]
        try:
            provider = self.provider_factory(request.model)
            options = request.options
            if request.procedure == "V01":
                result = Dialogue(self.memory, provider).ask(request.project_id, request.branch_id,
                                                              request.task, cancel=job["cancel"])
                payload = {"answer": result.answer, "manifest": result.manifest, "model": result.model}
            elif request.procedure == "V02":
                run = Stoffschmiede(self.memory, provider, self.library).develop(
                    request.project_id, request.branch_id, request.task,
                    count=int(options.get("count", 3)), reflect=bool(options.get("reflect", False)),
                    cancel=job["cancel"])
                payload = {"run_id": str(run.id), "candidates": [c.model_dump(mode="json")
                           for c in run.candidates], "reflection": run.reflection.model_dump(mode="json")
                           if run.reflection else None, "manifest": run.manifest}
            elif request.procedure == "V03":
                run = Geheimnislabor(self.memory, provider, self.library).develop(
                    request.project_id, request.branch_id, request.task,
                    mode=Arbeitsweise(options.get("mode", "rueckwaerts")),
                    given_truth=options.get("given_truth"), cancel=job["cancel"])
                payload = {"run_id": str(run.id), "result": run.entwurf.model_dump(mode="json"),
                           "manifest": run.manifest}
            else:
                source = Quelle.model_validate(options.get("source", {"art": "frei", "beschreibung": request.task}))
                editor = Autorenredaktion(self.memory, provider, self.library)
                if request.procedure == "V04":
                    run = editor.mutate(request.project_id, request.branch_id, request.task, source,
                                        operation=Operation(options.get("operation", "frei")),
                                        erhalten=tuple(options.get("erhalten", [])),
                                        veraenderbar=tuple(options.get("veraenderbar", [])),
                                        gezielt_aendern=tuple(options.get("gezielt_aendern", [])),
                                        moeglichkeiten=tuple(options.get("moeglichkeiten", [])),
                                        cancel=job["cancel"])
                else:
                    areas = tuple(Analysebereich(value) for value in options.get("bereiche", list(Analysebereich)))
                    run = editor.critique(request.project_id, request.branch_id, request.task, source,
                                          bereiche=areas, cancel=job["cancel"])
                payload = {"run_id": str(run.id), "result": run.result.model_dump(mode="json"),
                           "manifest": run.manifest}
            with self.lock:
                job["status"] = "fertig"
                job["result"] = payload
        except Exception as error:
            with self.lock:
                job["status"] = "abgebrochen" if job["cancel"].is_set() else "fehler"
                job["error"] = f"{type(error).__name__}: {error}"

    def state(self, job_id: str) -> dict:
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise NotFoundError(job_id)
            return {key: value for key, value in job.items() if key != "cancel"}

    def cancel(self, job_id: str):
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise NotFoundError(job_id)
            job["cancel"].set()
            if job["status"] == "läuft":
                job["status"] = "abbruch angefordert"


def create_app(database: Path, library: Path = CARDS, provider_factory=OllamaProvider) -> FastAPI:
    service = AppService(database, library, provider_factory)
    app = FastAPI(title="STORYFORGE", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = service

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0].strip("[]")
        origin = request.headers.get("origin")
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return PlainTextResponse("Nur lokale Zugriffe erlaubt", status_code=403)
        parsed = urlsplit(origin) if origin else None
        if parsed and (parsed.scheme != "http" or parsed.netloc != request.headers.get("host")):
            return PlainTextResponse("Fremde Herkunft abgelehnt", status_code=403)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(ValueError)
    async def value_error(_request, error):
        return PlainTextResponse(str(error), status_code=409 if isinstance(error, ConflictError) else 400)

    @app.exception_handler(NotFoundError)
    async def missing(_request, error):
        return PlainTextResponse(f"Nicht gefunden: {error}", status_code=404)

    @app.exception_handler(PermissionError)
    async def permission(_request, error):
        return PlainTextResponse(str(error), status_code=403)

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/projects")
    def projects():
        return [p.model_dump(mode="json") for p in service.memory.list_projects()]

    @app.post("/api/projects")
    def create_project(data: ProjectInput):
        return service.memory.create_project(data.title, universe_title=data.universe_title).model_dump(mode="json")

    @app.get("/api/projects/{project_id}")
    def project(project_id: UUID):
        p = service.memory.get_project(project_id)
        branches = service.memory.list_branches(project_id)
        return {"project": p.model_dump(mode="json"),
                "branches": [b.model_dump(mode="json") for b in branches],
                "revisions": [service.memory.get_revision(b.head_id).model_dump(mode="json") for b in branches]}

    @app.post("/api/projects/{project_id}/branches")
    def create_branch(project_id: UUID, data: BranchInput):
        return service.memory.create_branch(project_id, data.name, data.from_revision_id).model_dump(mode="json")

    @app.get("/api/projects/{project_id}/runs")
    def runs(project_id: UUID, branch_id: UUID | None = None):
        return service.memory.list_creative_runs(project_id, branch_id)

    @app.get("/api/projects/{project_id}/revisions")
    def revisions(project_id: UUID):
        return [r.model_dump(mode="json") for r in service.memory.list_revisions(project_id)]

    @app.get("/api/runs/{run_id}")
    def run(run_id: UUID):
        return service.memory.get_creative_run(run_id)

    @app.get("/api/projects/{project_id}/proposals")
    def proposals(project_id: UUID, branch_id: UUID | None = None):
        return [p.model_dump(mode="json") for p in service.memory.list_proposals(project_id, branch_id)]

    @app.post("/api/runs/{run_id}/candidates/{candidate_id}/stage")
    def stage(run_id: UUID, candidate_id: UUID):
        proposal = Stoffschmiede(service.memory, FakeProvider([]), service.library).stage_candidate(
            run_id, candidate_id)
        return proposal.model_dump(mode="json")

    @app.post("/api/proposals/{proposal_id}/approve")
    def approve(proposal_id: UUID, data: ApproveInput):
        return service.memory.approve(proposal_id, approved_by=data.author,
                                      explicit_approval=data.explicit_approval).model_dump(mode="json")

    @app.post("/api/proposals/{proposal_id}/reject")
    def reject(proposal_id: UUID):
        service.memory.reject(proposal_id)
        return {"status": "abgelehnt"}

    @app.get("/api/projects/{project_id}/turns")
    def turns(project_id: UUID, branch_id: UUID):
        return service.memory.list_turns(project_id, branch_id, limit=100)

    @app.get("/api/projects/{project_id}/export/{format}")
    def export(project_id: UUID, format: str):
        if format == "json":
            return PlainTextResponse(service.memory.export_json(project_id), media_type="application/json")
        if format == "markdown":
            return PlainTextResponse(service.memory.export_markdown(project_id), media_type="text/markdown")
        raise ValueError("Unbekanntes Exportformat")

    @app.get("/api/models")
    def models():
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
                data = json.load(response)
            return {"online": True, "models": [m["name"] for m in data.get("models", [])]}
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            return {"online": False, "models": []}

    @app.post("/api/jobs")
    def start_job(data: JobInput):
        return {"id": service.launch(data)}

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return service.state(job_id)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel(job_id: str):
        service.cancel(job_id)
        return service.state(job_id)

    return app
