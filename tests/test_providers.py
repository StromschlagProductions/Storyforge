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
    def __init__(self, body, *, status=200, delay=0):
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
            "total_duration": 2_000_000_000, "prompt_eval_count": 12, "eval_count": 5}
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
    with OllamaTestServer({"model": "test", "message": {"content": ""}}) as server:
        with pytest.raises(InvalidModelResponse):
            OllamaProvider("test", base_url=server.url).generate(ModelRequest(messages=[]))
    with pytest.raises(ValueError, match="lokal"):
        OllamaProvider("test", base_url="http://example.com:11434")


def test_ollama_timeout_und_abbruch():
    body = {"model": "test", "message": {"content": "spät"}}
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
    with pytest.raises(ModelError, match="nicht erreichbar"):
        provider.generate(ModelRequest(messages=[], timeout_seconds=1))
    with OllamaTestServer({"model": "test", "message": {"content": "Antwort"}}) as server:
        response = OllamaProvider("test", base_url=server.url).generate(ModelRequest(messages=[]))
        assert response.prompt_tokens is None
        assert response.output_tokens is None
        assert response.duration_seconds is None
