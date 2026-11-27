"""Prozessbesitz und lokales Beenden ohne echten Ollama-Dienst."""

import subprocess
from types import SimpleNamespace

from fastapi.testclient import TestClient

from storyforge.web import ollama_service as module
from storyforge.web.app import create_app


class Process:
    def __init__(self, exited=False):
        self.exited = exited
        self.terminated = False
        self.killed = False

    def poll(self):
        return 1 if self.exited else None

    def terminate(self):
        self.terminated = True
        self.exited = True

    def kill(self):
        self.killed = True
        self.exited = True

    def wait(self, timeout):
        return 0


def test_vorhandene_instanz_bleibt_unberuehrt(monkeypatch):
    monkeypatch.setattr(module, 'local_models', lambda: ['synthetisch:1'])
    monkeypatch.setattr(module, 'installed_ollama', lambda: None)
    service = module.OllamaService()
    assert service.start() == {'online': True, 'models': ['synthetisch:1']}
    service.stop()
    assert service.process is None


def test_fehlende_installation_ist_verstaendlich_und_startet_nichts(monkeypatch):
    monkeypatch.setattr(module, 'local_models', lambda: (_ for _ in ()).throw(OSError('offline')))
    monkeypatch.setattr(module, 'installed_ollama', lambda: None)
    service = module.OllamaService()
    status = service.start()
    assert status['online'] is False
    assert 'nicht installiert' in status['error']
    service.stop()


def test_eigener_prozess_wird_gestartet_und_beendet(monkeypatch):
    process = Process()
    calls = []
    probes = iter([OSError('offline'), OSError('noch nicht bereit'), ['modell:1']])

    def probe():
        value = next(probes)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(module, 'local_models', probe)
    monkeypatch.setattr(module, 'installed_ollama', lambda: 'ollama')
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *args, **kwargs: calls.append((args, kwargs)) or process)
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    service = module.OllamaService()
    assert service.start()['models'] == ['modell:1']
    assert calls[0][0][0] == ['ollama', 'serve']
    assert calls[0][1]['stdin'] == subprocess.DEVNULL
    assert calls[0][1]['stdout'] == subprocess.DEVNULL
    assert calls[0][1]['stderr'] == subprocess.DEVNULL
    service.stop()
    service.stop()
    assert process.terminated and not process.killed


def test_timeout_beendet_nur_eigenen_prozess(monkeypatch):
    process = Process()
    monkeypatch.setattr(module, 'local_models', lambda: (_ for _ in ()).throw(OSError('offline')))
    monkeypatch.setattr(module, 'installed_ollama', lambda: 'ollama')
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *args, **kwargs: process)
    service = module.OllamaService()
    assert 'nicht betriebsbereit' in service.start(timeout=0)['error']
    assert process.terminated


def test_startfehler_bleibt_als_status_sichtbar(monkeypatch):
    monkeypatch.setattr(module, 'local_models', lambda: (_ for _ in ()).throw(OSError('offline')))
    monkeypatch.setattr(module, 'installed_ollama', lambda: 'ollama')
    monkeypatch.setattr(module.subprocess, 'Popen',
                        lambda *args, **kwargs: (_ for _ in ()).throw(OSError('Start verweigert')))
    service = module.OllamaService()
    assert 'konnte nicht gestartet werden' in service.start()['error']
    assert service.process is None


def test_race_mit_fremder_instanz_uebernimmt_keinen_prozess(monkeypatch):
    process = Process(exited=True)
    probes = iter([OSError('offline'), ['fremd:1']])

    def probe():
        value = next(probes)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(module, 'local_models', probe)
    monkeypatch.setattr(module, 'installed_ollama', lambda: 'ollama')
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *args, **kwargs: process)
    service = module.OllamaService()
    assert service.start()['online']
    service.stop()
    assert not process.terminated


def test_windows_start_ohne_konsolenfenster(monkeypatch):
    process = Process(exited=True)
    monkeypatch.setattr(module, 'local_models', lambda: (_ for _ in ()).throw(OSError('offline')))
    monkeypatch.setattr(module, 'installed_ollama', lambda: 'ollama.exe')
    monkeypatch.setattr(module, 'os', SimpleNamespace(name='nt'))
    args = []
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *a, **kw: args.append(kw) or process)
    service = module.OllamaService()
    service.start(timeout=0)
    assert args[0]['creationflags'] & 0x08000000


def test_beenden_route_und_modellfehler(tmp_path):
    service = module.OllamaService()
    service.error = 'Ollama ist nicht installiert.'
    service.status = lambda: {'online': False, 'models': [], 'error': service.error}
    stopped = []
    app = create_app(tmp_path / 'ui.sqlite3', ollama_service=service,
                     shutdown_callback=lambda: stopped.append(True))
    with TestClient(app) as client:
        response = client.post('/api/shutdown')
        assert response.status_code == 200
        assert stopped == [True]
        assert 'STORYFORGE beenden' in client.get('/').text
        assert client.get('/api/models').json()['error'] == 'Ollama ist nicht installiert.'
        assert client.post('/api/shutdown', headers={'Origin': 'https://fremd.example'}).status_code == 403
    with TestClient(create_app(tmp_path / 'other.sqlite3')) as client:
        assert client.post('/api/shutdown').status_code == 503
