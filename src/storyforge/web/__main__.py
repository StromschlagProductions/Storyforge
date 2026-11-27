"""Startet die Autorenwerkstatt ausschließlich über Loopback."""

import argparse
import threading
import webbrowser
from pathlib import Path

import uvicorn

from .app import create_app
from .ollama_service import OllamaService


def main():
    parser = argparse.ArgumentParser(description="STORYFORGE lokal starten")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", type=Path, default=Path("local/storyforge.sqlite3"))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port muss zwischen 1 und 65535 liegen")
    ollama = OllamaService()
    try:
        ollama.start()
        server = uvicorn.Server(uvicorn.Config(
            create_app(args.database, ollama_service=ollama,
                       shutdown_callback=lambda: setattr(server, "should_exit", True)),
            host="127.0.0.1", port=args.port, access_log=False))
        if not args.no_browser:
            timer = threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}"))
            timer.daemon = True
            timer.start()
        server.run()
    finally:
        ollama.stop()


if __name__ == "__main__":
    main()
