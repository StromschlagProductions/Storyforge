import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from storyforge import (InvalidModelResponse, ModelCancelled, ModelError, ModelTimeout,
                        OllamaProvider)
from storyforge.providers import ModelRequest


class OllamaTestServer:
    def __init__(self, body, *, status=200, delay=0, chunks=None):
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))) )
                if delay:
                    time.sleep(delay)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                try:
                    if chunks is not None:
                        for chunk in chunks:
                            self.wfile.write(json.dumps(chunk).encode() + b'\n')
                            self.wfile.flush()
                            if delay:
                                time.sleep(delay)
                    else:
                        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"


def test_ollama_freie_und_strukturierte_antworten():
    body = {"model": "lokales-testmodell", "message": {"content": "Ein neuer Ansatz."},
            "done": True, "total_duration": 2_000_000_000,
            "prompt_eval_count": 12, "eval_count": 5}
    with OllamaTestServer(body) as server:
        provider = OllamaProvider("lokales-testmodell", base_url=server.url,
                                  options={"temperature": 0.3})
        plain = provider.generate(ModelRequest(messages=[{"role": "user", "content": "Hallo"}]))
        schema = {"type": "object", "properties": {"ideas": {"type": "array"}}}
        structured = provider.generate(ModelRequest(messages=[{"role": "user", "content": "Idee"}],
                                                    format_schema=schema))
        assert plain.content == structured.content == "Ein neuer Ansatz."
        assert plain.model == "lokales-testmodell"
        assert (plain.prompt_tokens, plain.output_tokens, plain.duration_seconds) == (12, 5, 2.0)
        assert all(path == "/api/chat" for path, _ in server.requests)
        assert server.requests[0][1]["stream"] is False
        assert server.requests[0][1]["options"] == {"temperature": 0.3}
        assert "format" not in server.requests[0][1]
        assert server.requests[1][1]["format"] == schema


def test_ollama_fehler_und_ungueltige_antwort():
    with OllamaTestServer({"error": "nicht vorhanden"}, status=404) as server:
        with pytest.raises(ModelError, match="HTTP 404"):
            OllamaProvider("test", base_url=server.url).generate(ModelRequest(messages=[]))
    with OllamaTestServer(b"kein JSON") as server:
        with pytest.raises(InvalidModelResponse):
            OllamaProvider("test", base_url=server.url).generate(ModelRequest(messages=[]))
    with OllamaTestServer({"model": "test", "message": {"content": ""}, "done": True}) as server:
        with pytest.raises(InvalidModelResponse):
            OllamaProvider("test", base_url=server.url).generate(ModelRequest(messages=[]))
    with pytest.raises(ValueError, match="lokal"):
        OllamaProvider("test", base_url="http://example.com:11434")


def test_ollama_timeout_und_abbruch():
    body = {"model": "test", "message": {"content": "spät"}, "done": True}
    with OllamaTestServer(body, delay=0.3) as server:
        provider = OllamaProvider("test", base_url=server.url)
        with pytest.raises(ModelTimeout):
            provider.generate(ModelRequest(messages=[], timeout_seconds=0.03))
        cancel = threading.Event()
        timer = threading.Timer(0.03, cancel.set)
        timer.start()
        try:
            with pytest.raises(ModelCancelled):
                provider.generate(ModelRequest(messages=[], timeout_seconds=1), cancel)
        finally:
            timer.join()


def test_ollama_offline_und_optionale_metriken():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        unused_port = probe.getsockname()[1]
    provider = OllamaProvider("test", base_url=f"http://127.0.0.1:{unused_port}")
    # Auf Windows kann ein geschlossener Port als Timeout statt ConnectionRefused erscheinen.
    with pytest.raises(ModelError):
        provider.generate(ModelRequest(messages=[], timeout_seconds=1))
    with OllamaTestServer({"model": "test", "message": {"content": "Antwort"}, "done": True}) as server:
        response = OllamaProvider("test", base_url=server.url).generate(ModelRequest(messages=[]))
        assert response.prompt_tokens is None
        assert response.output_tokens is None
        assert response.duration_seconds is None


def test_unvollstaendige_ollama_antwort_wird_abgelehnt():
    with OllamaTestServer({"model": "test", "message": {"content": "Teilantwort"},
                           "done": False}) as server:
        with pytest.raises(InvalidModelResponse):
            OllamaProvider("test", base_url=server.url).generate(ModelRequest(messages=[]))


@pytest.mark.parametrize(("body", "meldung"), [
    (b"kein JSON", "HTTP-JSON"),
    ({"model": "gemma", "message": {"content": ""}, "done": True}, "leeren Antwortinhalt"),
    ({"model": "gemma", "message": {"content": "", "thinking": "privater Gedanke"},
      "done": True}, "nur Thinking-Text"),
    ({"model": "gemma", "message": {"content": "teil"}, "done": False}, "nicht abgeschlossen"),
    ({"model": "gemma", "message": {"content": "teil"}, "done": True,
      "done_reason": "length"}, "Ausgabelimit"),
    ({"model": "gemma", "done": True}, "message-Objekt"),
])
def test_ollama_diagnose_ohne_rohen_inhalt(body, meldung):
    with OllamaTestServer(body) as server:
        with pytest.raises(InvalidModelResponse, match=meldung):
            OllamaProvider("gemma", base_url=server.url).generate(ModelRequest(messages=[]))


def test_gemma_artige_strukturantwort_und_generierungsgeschwindigkeit():
    body = {"model": "gemma:synthetisch", "message": {"role": "assistant", "content": '{"ideen":[]}'},
            "done": True, "done_reason": "stop", "total_duration": 4_000_000_000,
            "prompt_eval_count": 100, "eval_count": 50, "eval_duration": 2_000_000_000}
    with OllamaTestServer(body) as server:
        provider = OllamaProvider("gemma:synthetisch", base_url=server.url)
        reply = provider.generate(ModelRequest(messages=[], format_schema={"type": "object"}))
        assert reply.content == '{"ideen":[]}'
        assert reply.generation_tokens_per_second == 25
        assert reply.wall_seconds is not None and reply.wall_seconds >= 0
        assert server.requests[0][1]["format"] == {"type": "object"}


def test_lokale_diagnose_ohne_prompt_antwort_und_thinking(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STORYFORGE_MODEL_DIAGNOSTICS", "1")
    private = "VERTRAULICHER SYNTHETISCHER TEXT"
    body = {"model": "gemma", "message": {"content": "", "thinking": private}, "done": True,
            "eval_count": 9}
    with OllamaTestServer(body) as server:
        with pytest.raises(InvalidModelResponse):
            OllamaProvider("gemma", base_url=server.url).generate(
                ModelRequest(messages=[{"role": "user", "content": private}]))
    log = (tmp_path / "local/ollama-diagnostics.jsonl").read_text(encoding="utf-8")
    assert private not in log
    assert json.loads(log)["status"] == "thinking_only"


def test_konfigurierbare_ollama_limits_und_timeout(monkeypatch):
    from storyforge.providers import local_timeout
    monkeypatch.setenv("STORYFORGE_MODEL_TIMEOUT_SECONDS", "480")
    monkeypatch.setenv("STORYFORGE_OLLAMA_NUM_CTX", "8192")
    monkeypatch.setenv("STORYFORGE_OLLAMA_NUM_PREDICT", "4096")
    assert local_timeout() == 480
    provider = OllamaProvider("gemma")
    assert provider.options == {"num_ctx": 8192, "num_predict": 4096}
    monkeypatch.setenv("STORYFORGE_OLLAMA_NUM_CTX", "unzulässig")
    with pytest.raises(ValueError, match="NUM_CTX"):
        OllamaProvider("gemma")


def test_ollama_streaming_liefert_teile_und_endmetrik():
    chunks = [
        {"model":"gemma", "message":{"content":"Erster "}, "done":False},
        {"model":"gemma", "message":{"content":"Teil"}, "done":False},
        {"model":"gemma", "message":{"content":""}, "done":True,
         "done_reason":"stop", "eval_count":2, "eval_duration":1_000_000_000},
    ]
    seen = []
    with OllamaTestServer(None, chunks=chunks) as server:
        result = OllamaProvider("gemma", base_url=server.url).generate_stream(
            ModelRequest(messages=[{"role":"user", "content":"Synthetisch"}]), seen.append)
        assert server.requests[0][1]["stream"] is True
    assert seen == ["Erster ", "Teil"]
    assert result.content == "Erster Teil"
    assert result.generation_tokens_per_second == 2


def test_ollama_streaming_abbruch_und_fehlender_abschluss():
    chunks = [{"model":"gemma", "message":{"content":"Teil"}, "done":False},
              {"model":"gemma", "message":{"content":"Rest"}, "done":True}]
    cancel = threading.Event()
    with OllamaTestServer(None, chunks=chunks, delay=.1) as server:
        with pytest.raises(ModelCancelled):
            OllamaProvider("gemma", base_url=server.url).generate_stream(
                ModelRequest(messages=[], timeout_seconds=2), lambda _: cancel.set(), cancel)
    with OllamaTestServer(None, chunks=chunks[:1]) as server:
        with pytest.raises(InvalidModelResponse, match="ohne Abschluss"):
            OllamaProvider("gemma", base_url=server.url).generate_stream(
                ModelRequest(messages=[]), lambda _: None)
