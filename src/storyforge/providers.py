"""Schmaler Modellvertrag, lokaler Ollama-Adapter und deterministischer Testanbieter."""

import http.client
import json
import threading
from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Protocol
from urllib.parse import urlsplit


class ModelError(RuntimeError):
    """Einheitlicher, für den Dialog behandelbarer Modellfehler."""


class ModelTimeout(ModelError):
    pass


class ModelCancelled(ModelError):
    pass


class InvalidModelResponse(ModelError):
    pass


@dataclass(frozen=True)
class ModelRequest:
    messages: list[dict[str, str]]
    format_schema: dict[str, Any] | None = None
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class ModelResponse:
    content: str
    model: str
    capabilities: tuple[str, ...] = ("text", "structured")
    duration_seconds: float | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None


class ModelProvider(Protocol):
    model: str
    capabilities: tuple[str, ...]

    def generate(self, request: ModelRequest, cancel: threading.Event | None = None) -> ModelResponse: ...


@dataclass
class FakeProvider:
    """Spielt vorgegebene Antworten oder Fehler in fester Reihenfolge ab."""

    answers: list[str | ModelResponse | Exception]
    model: str = "fake-sf002"
    capabilities: tuple[str, ...] = ("text", "structured")
    requests: list[ModelRequest] = field(default_factory=list, init=False)

    def __post_init__(self):
        self._queue = deque(self.answers)

    def generate(self, request: ModelRequest, cancel: threading.Event | None = None) -> ModelResponse:
        if cancel is not None and cancel.is_set():
            raise ModelCancelled("Anfrage abgebrochen")
        self.requests.append(request)
        if not self._queue:
            raise ModelError("Keine Fake-Antwort vorhanden")
        answer = self._queue.popleft()
        if isinstance(answer, Exception):
            raise answer if isinstance(answer, ModelError) else ModelError(str(answer)) from answer
        return answer if isinstance(answer, ModelResponse) else ModelResponse(content=answer, model=self.model)


class OllamaProvider:
    capabilities = ("text", "structured")

    def __init__(self, model: str, *, base_url: str = "http://127.0.0.1:11434",
                 options: dict[str, Any] | None = None, allow_remote: bool = False):
        url = urlsplit(base_url)
        if not model.strip() or url.scheme != "http" or not url.hostname or url.path not in ("", "/"):
            raise ValueError("Ungültiger Ollama-Modellname oder Serveradresse")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Serveradresse darf keine Zugangsdaten oder Parameter enthalten")
        if not allow_remote and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Ollama-Kommunikation ist standardmäßig nur lokal erlaubt")
        self.model = model
        self.host = url.hostname
        self.port = url.port or 80
        self.options = dict(options or {})

    def generate(self, request: ModelRequest, cancel: threading.Event | None = None) -> ModelResponse:
        if request.timeout_seconds <= 0:
            raise ValueError("Timeout muss positiv sein")
        if cancel is not None and cancel.is_set():
            raise ModelCancelled("Anfrage abgebrochen")
        payload: dict[str, Any] = {"model": self.model, "messages": request.messages, "stream": False}
        if request.format_schema is not None:
            payload["format"] = request.format_schema
        if self.options:
            payload["options"] = self.options

        done = threading.Event()
        state: dict[str, Any] = {}

        def worker():
            connection = http.client.HTTPConnection(self.host, self.port, timeout=request.timeout_seconds)
            state["connection"] = connection
            try:
                connection.request("POST", "/api/chat", body=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"})
                response = connection.getresponse()
                state["status"] = response.status
                state["body"] = response.read(4_000_001)
            except Exception as error:
                state["error"] = error
            finally:
                connection.close()
                done.set()

        threading.Thread(target=worker, daemon=True).start()
        deadline = monotonic() + request.timeout_seconds
        while not done.wait(min(0.05, max(0, deadline - monotonic()))):
            if cancel is not None and cancel.is_set():
                connection = state.get("connection")
                if connection is not None:
                    connection.close()
                raise ModelCancelled("Anfrage abgebrochen")
            if monotonic() >= deadline:
                connection = state.get("connection")
                if connection is not None:
                    connection.close()
                raise ModelTimeout("Ollama hat nicht rechtzeitig geantwortet")
        if cancel is not None and cancel.is_set():
            raise ModelCancelled("Anfrage abgebrochen")
        if "error" in state:
            if isinstance(state["error"], TimeoutError):
                raise ModelTimeout("Ollama hat nicht rechtzeitig geantwortet") from state["error"]
            raise ModelError(f"Ollama nicht erreichbar: {type(state['error']).__name__}") from state["error"]
        if state["status"] != 200:
            raise ModelError(f"Ollama HTTP {state['status']}")
        if len(state["body"]) > 4_000_000:
            raise InvalidModelResponse("Ollama-Antwort zu groß")
        try:
            data = json.loads(state["body"])
            content = data["message"]["content"]
            model = data["model"]
            if (not isinstance(content, str) or not content.strip() or
                    not isinstance(model, str) or not model.strip() or data.get("done") is not True):
                raise ValueError("Leerer oder ungültiger Inhalt")
            return ModelResponse(content=content, model=model,
                                 duration_seconds=data["total_duration"] / 1_000_000_000
                                 if data.get("total_duration") is not None else None,
                                 prompt_tokens=data.get("prompt_eval_count"),
                                 output_tokens=data.get("eval_count"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise InvalidModelResponse("Ungültige Ollama-Antwort") from error
