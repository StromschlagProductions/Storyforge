"""Lebensdauer eines optionalen, ausschließlich lokalen Ollama-Dienstes."""

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path


TAGS_URL = "http://127.0.0.1:11434/api/tags"


def installed_ollama() -> str | None:
    executable = shutil.which("ollama")
    if executable:
        return executable
    if os.name == "nt":
        for root, suffix in ((os.environ.get("LOCALAPPDATA"), "Programs/Ollama/ollama.exe"),
                             (os.environ.get("PROGRAMFILES"), "Ollama/ollama.exe")):
            if root:
                path = Path(root) / suffix
                if path.is_file():
                    return str(path)
    return None


def local_models() -> list[str]:
    with urllib.request.urlopen(TAGS_URL, timeout=1) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        raise ValueError("Ungültige Ollama-Antwort")
    return [model["name"] for model in data["models"] if isinstance(model, dict)]


class OllamaService:
    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.error: str | None = None

    def status(self) -> dict:
        try:
            models = local_models()
            self.error = None
            return {"online": True, "models": models}
        except (OSError, ValueError, KeyError, TypeError):
            return {"online": False, "models": [], "error": self.error or
                    "Ollama ist nicht erreichbar. Prüfe die lokale Installation."}

    def start(self, timeout: float = 20) -> dict:
        status = self.status()
        if status["online"]:
            return status  # Eine bereits laufende Instanz gehört nicht STORYFORGE.
        executable = installed_ollama()
        if executable is None:
            self.error = "Ollama ist nicht installiert. Installiere Ollama und ein lokales Modell."
            return self.status()
        try:
            self.process = subprocess.Popen(
                [executable, "serve"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0,
            )
        except OSError as error:
            self.error = f"Ollama konnte nicht gestartet werden: {error}"
            return self.status()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = self.status()
            if status["online"]:
                if self.process.poll() is not None:
                    self.process = None  # Eine andere Instanz hat den Port übernommen.
                return status
            if self.process.poll() is not None:
                break
            time.sleep(0.2)
        self.error = "Ollama wurde nicht betriebsbereit. Prüfe die lokale Installation."
        self.stop()
        return self.status()

    def stop(self):
        process, self.process = self.process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
