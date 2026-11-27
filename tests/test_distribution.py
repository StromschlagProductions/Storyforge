from pathlib import Path
from zipfile import ZipFile


def test_windows_testarchiv_enthaelt_programm_karten_und_keine_projektdaten():
    root = Path(__file__).resolve().parents[1]
    archive = root / 'downloads' / 'Storyforge-SF004-Windows-Test.zip'
    with ZipFile(archive) as package:
        names = package.namelist()
        assert len([name for name in names if '/library/cards/' in name and name.endswith('.json')]) == 59
        for suffix in ('Start_Storyforge.bat', 'WINDOWS_KURZANLEITUNG.txt', 'pyproject.toml',
                       'src/storyforge/web/app.py', 'src/storyforge/web/static/logo-dunkel.png',
                       'src/storyforge/web/static/logo-hell.png'):
            assert any(name.endswith('/' + suffix) for name in names)
        assert not any(any(part in name.lower() for part in
                           ('.sqlite', '.db', '.env', '.venv', '__pycache__', '/private/'))
                       for name in names)


def test_entpackte_distribution_startet_python_kern(tmp_path):
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    archive = root / 'downloads' / 'Storyforge-SF004-Windows-Test.zip'
    with ZipFile(archive) as package:
        package.extractall(tmp_path)
    folder = tmp_path / 'Storyforge-SF004-Windows-Test'
    env = {**os.environ, 'PYTHONPATH': str(folder / 'src')}
    command = ('from pathlib import Path; from storyforge.web.app import create_app; '
               'from fastapi.testclient import TestClient; '
               'app=create_app(Path("local/test.sqlite3")); '
               'client=TestClient(app); '
               'assert client.get("/").status_code == 200; '
               'assert len(app.state.service.library.filter()) == 59')
    subprocess.run([sys.executable, '-c', command], cwd=folder, env=env, check=True,
                   capture_output=True, text=True)
