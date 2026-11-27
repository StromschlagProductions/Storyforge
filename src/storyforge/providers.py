"""Schmaler Modellvertrag, lokaler Ollama-Adapter und deterministischer Testanbieter."""

import http.client
import json
import os
import queue
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from math import isfinite
from time import monotonic
from typing import Any, Callable, Protocol
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
    wall_seconds: float | None = None
    generation_tokens_per_second: float | None = None


def local_timeout() -> float:
    """Langes lokales Modellbudget; über Umgebungsvariable änderbar."""
    raw = os.environ.get("STORYFORGE_MODEL_TIMEOUT_SECONDS", "300")
    try:
        seconds = float(raw)
    except ValueError as error:
        raise ValueError("STORYFORGE_MODEL_TIMEOUT_SECONDS muss eine Zahl sein") from error
    if not 1 <= seconds <= 3600:
        raise ValueError("STORYFORGE_MODEL_TIMEOUT_SECONDS muss zwischen 1 und 3600 liegen")
    return seconds


def _diagnostic(record: dict[str, Any]):
    """Optionales lokales Metadatenprotokoll, niemals Prompts oder Antworttexte."""
    if os.environ.get("STORYFORGE_MODEL_DIAGNOSTICS") != "1":
        return
    try:
        safe = {"status": record["status"]}
        for key in ("wall_seconds", "total_duration_seconds", "prompt_tokens", "output_tokens",
                    "generation_tokens_per_second", "http_status", "response_bytes"):
            value = record.get(key)
            if type(value) in (int, float) and isfinite(value) and value >= 0:
                safe[key] = value
        if record.get("done_reason") in ("stop", "length", "unload"):
            safe["done_reason"] = record["done_reason"]
        path = Path("local/ollama-diagnostics.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps({"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                     **safe}, ensure_ascii=False) + "\n")
    except OSError:
        pass  # Ein optionales Diagnoseprotokoll darf keinen Modelllauf verhindern.


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
        for key, variable in (("num_ctx", "STORYFORGE_OLLAMA_NUM_CTX"),
                              ("num_predict", "STORYFORGE_OLLAMA_NUM_PREDICT")):
            if key not in self.options and variable in os.environ:
                try:
                    value = int(os.environ[variable])
                except ValueError as error:
                    raise ValueError(f"{variable} muss eine ganze Zahl sein") from error
                if not 128 <= value <= 65536:
                    raise ValueError(f"{variable} muss zwischen 128 und 65536 liegen")
                self.options[key] = value

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

        started = monotonic()
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
                _diagnostic({"status": "cancelled", "wall_seconds": monotonic() - started})
                raise ModelCancelled("Anfrage abgebrochen")
            if monotonic() >= deadline:
                connection = state.get("connection")
                if connection is not None:
                    connection.close()
                _diagnostic({"status": "timeout", "wall_seconds": monotonic() - started})
                raise ModelTimeout("Ollama hat nicht rechtzeitig geantwortet")
        if cancel is not None and cancel.is_set():
            _diagnostic({"status": "cancelled", "wall_seconds": monotonic() - started})
            raise ModelCancelled("Anfrage abgebrochen")
        if "error" in state:
            if isinstance(state["error"], TimeoutError):
                _diagnostic({"status": "timeout", "wall_seconds": monotonic() - started})
                raise ModelTimeout("Ollama hat nicht rechtzeitig geantwortet") from state["error"]
            _diagnostic({"status": "connection_error", "wall_seconds": monotonic() - started})
            raise ModelError(f"Ollama nicht erreichbar: {type(state['error']).__name__}") from state["error"]
        if state["status"] != 200:
            _diagnostic({"status": "http_error", "http_status": state["status"],
                         "wall_seconds": monotonic() - started})
            raise ModelError(f"Ollama HTTP {state['status']}")
        if len(state["body"]) > 4_000_000:
            _diagnostic({"status": "response_too_large", "response_bytes": len(state["body"])})
            raise InvalidModelResponse("Ollama-Antwort zu groß")
        try:
            data = json.loads(state["body"])
        except (ValueError, UnicodeDecodeError) as error:
            _diagnostic({"status": "invalid_json", "response_bytes": len(state["body"])})
            raise InvalidModelResponse("Ollama lieferte kein gültiges HTTP-JSON") from error
        return self._finish(data, started)

    def generate_stream(self, request: ModelRequest, on_chunk: Callable[[str], None],
                        cancel: threading.Event | None = None) -> ModelResponse:
        """Liest echte Ollama-NDJSON-Teile; ein unvollständiger Lauf wird nie als Antwort gespeichert."""
        if request.format_schema is not None:
            raise ValueError("Strukturierte Antworten werden nicht gestreamt")
        if request.timeout_seconds <= 0:
            raise ValueError("Timeout muss positiv sein")
        if cancel is not None and cancel.is_set():
            raise ModelCancelled("Anfrage abgebrochen")
        payload = {"model": self.model, "messages": request.messages, "stream": True}
        if self.options:
            payload["options"] = self.options
        events: queue.Queue = queue.Queue()
        connection = http.client.HTTPConnection(self.host, self.port, timeout=request.timeout_seconds)
        started = monotonic()

        def worker():
            try:
                connection.request("POST", "/api/chat", body=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"})
                response = connection.getresponse()
                events.put(("status", response.status))
                if response.status != 200:
                    return
                while line := response.readline(4_000_001):
                    events.put(("line", line))
                    if len(line) > 4_000_000:
                        return
            except Exception as error:
                events.put(("error", error))
            finally:
                connection.close()
                events.put(("end", None))

        threading.Thread(target=worker, daemon=True).start()
        deadline = started + request.timeout_seconds
        parts: list[str] = []
        total_bytes = 0
        final = None
        while True:
            if cancel is not None and cancel.is_set():
                connection.close()
                _diagnostic({"status": "cancelled", "wall_seconds": monotonic() - started})
                raise ModelCancelled("Anfrage abgebrochen")
            remaining = deadline - monotonic()
            if remaining <= 0:
                connection.close()
                _diagnostic({"status": "timeout", "wall_seconds": monotonic() - started})
                raise ModelTimeout("Ollama hat nicht rechtzeitig geantwortet")
            try:
                kind, value = events.get(timeout=min(0.05, remaining))
            except queue.Empty:
                continue
            if kind == "status":
                if value != 200:
                    connection.close()
                    _diagnostic({"status": "http_error", "http_status": value})
                    raise ModelError(f"Ollama HTTP {value}")
            elif kind == "error":
                if isinstance(value, TimeoutError):
                    raise ModelTimeout("Ollama hat nicht rechtzeitig geantwortet") from value
                raise ModelError(f"Ollama nicht erreichbar: {type(value).__name__}") from value
            elif kind == "line":
                total_bytes += len(value)
                if total_bytes > 4_000_000:
                    connection.close()
                    raise InvalidModelResponse("Ollama-Antwort zu groß")
                try:
                    item = json.loads(value)
                except (ValueError, UnicodeDecodeError) as error:
                    connection.close()
                    raise InvalidModelResponse("Ungültiges Ollama-Streaming-JSON") from error
                if not isinstance(item, dict) or not isinstance(item.get("message"), dict):
                    connection.close()
                    raise InvalidModelResponse("Ungültiger Ollama-Streaming-Teil")
                chunk = item["message"].get("content", "")
                if not isinstance(chunk, str):
                    connection.close()
                    raise InvalidModelResponse("Ungültiger Ollama-Streaming-Text")
                if chunk:
                    parts.append(chunk)
                    try:
                        on_chunk(chunk)
                    except Exception:
                        connection.close()
                        raise
                if item.get("done") is True:
                    final = item
            elif kind == "end":
                break
        if final is None:
            _diagnostic({"status": "incomplete", "response_bytes": total_bytes})
            raise InvalidModelResponse("Ollama-Streaming endete ohne Abschluss")
        final = {**final, "message": {**final["message"], "content": "".join(parts)}}
        return self._finish(final, started)

    def _finish(self, data: Any, started: float) -> ModelResponse:
        if not isinstance(data, dict):
            raise InvalidModelResponse("Ollama-JSON ist kein Objekt")
        if data.get("done") is not True:
            reason = data.get("done_reason")
            _diagnostic({"status": "incomplete", "done_reason": reason})
            raise InvalidModelResponse("Ollama-Antwort ist nicht abgeschlossen (done fehlt oder ist false)")
        if data.get("done_reason") == "length":
            _diagnostic({"status": "output_limit", "output_tokens": data.get("eval_count")})
            raise InvalidModelResponse("Ollama erreichte das Ausgabelimit (done_reason=length)")
        message = data.get("message")
        if not isinstance(message, dict):
            raise InvalidModelResponse("Ollama-Antwort enthält kein message-Objekt")
        content = message.get("content")
        thinking = message.get("thinking")
        if not isinstance(content, str) or not content.strip():
            category = "thinking_only" if isinstance(thinking, str) and thinking.strip() else "empty_content"
            _diagnostic({"status": category, "output_tokens": data.get("eval_count")})
            raise InvalidModelResponse("Ollama lieferte nur Thinking-Text, aber keinen Antwortinhalt" if
                                       category == "thinking_only" else "Ollama lieferte leeren Antwortinhalt")
        model = data.get("model")
        if not isinstance(model, str) or not model.strip():
            raise InvalidModelResponse("Ollama-Antwort enthält keine Modellkennung")
        total_ns = data.get("total_duration")
        eval_ns = data.get("eval_duration")
        output_tokens = data.get("eval_count")
        duration = total_ns / 1_000_000_000 if isinstance(total_ns, (int, float)) and total_ns >= 0 else None
        speed = (output_tokens / (eval_ns / 1_000_000_000)
                 if isinstance(output_tokens, int) and isinstance(eval_ns, (int, float)) and eval_ns > 0 else None)
        wall = monotonic() - started
        _diagnostic({"status": "transport_ok", "wall_seconds": wall, "total_duration_seconds": duration,
                     "prompt_tokens": data.get("prompt_eval_count"), "output_tokens": output_tokens,
                     "generation_tokens_per_second": speed, "done_reason": data.get("done_reason")})
        return ModelResponse(content=content, model=model, duration_seconds=duration,
                             prompt_tokens=data.get("prompt_eval_count"), output_tokens=output_tokens,
                             wall_seconds=wall, generation_tokens_per_second=speed)
