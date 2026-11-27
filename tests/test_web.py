import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from storyforge import FakeProvider, Memory, NarrativeLibrary, Stoffschmiede
from storyforge.web.app import create_app
from test_autorenredaktion import critique, mutation
from test_geheimnislabor import answer as mystery_answer
from test_stoffschmiede import _response as stoff_answer
from storyforge import Operation

CARDS = Path(__file__).resolve().parents[1] / 'library' / 'cards'


def await_job(client, job_id):
    for _ in range(200):
        state = client.get('/api/jobs/' + job_id).json()
        if state['status'] not in ('läuft', 'abbruch angefordert'):
            return state
        time.sleep(.01)
    raise AssertionError('Hintergrundauftrag blieb hängen')


def test_fuenf_verfahren_projektakte_und_export_ohne_ollama(tmp_path):
    db = tmp_path / 'ui.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetische Werkstatt')
    branch = memory.list_branches(project.id)[0]
    cards = NarrativeLibrary.load(CARDS)
    ids = [card.id for card in Stoffschmiede(memory, FakeProvider([]), cards).select_cards('Klang', limit=3).cards]
    answers = iter(['Freie synthetische Antwort', stoff_answer(branch.head_id, ids),
                    json.dumps(mystery_answer()), mutation(Operation.FREI), critique()])
    app = create_app(db, provider_factory=lambda model: FakeProvider([next(answers)], model=model))
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        assert client.get('/static/style.css').status_code == 200
        assert client.get('/static/logo-dunkel.png').status_code == 200
        assert client.get('/static/logo-hell.png').status_code == 200
        assert client.get('/api/projects').json()[0]['id'] == str(project.id)
        assert client.get(f'/api/projects/{project.id}').json()['branches'][0]['id'] == str(branch.id)
        for procedure in ('V01', 'V02', 'V03', 'V04', 'V05'):
            options = {'source': {'art': 'frei', 'beschreibung': 'Synthetischer Ton'},
                       'operation': 'frei'} if procedure in ('V04', 'V05') else {}
            response = client.post('/api/jobs', json={'project_id': str(project.id),
                'branch_id': str(branch.id), 'procedure': procedure, 'task': 'Klang',
                'model': 'fake', 'options': options})
            assert response.status_code == 200
            job = await_job(client, response.json()['id'])
            assert job['status'] == 'fertig', job['error']
            assert job['project_id'] == str(project.id)
            if procedure == 'V02':
                candidate = job['result']['candidates'][0]
                proposal = client.post(f"/api/runs/{job['result']['run_id']}/candidates/{candidate['id']}/stage").json()
                assert proposal['status'] == 'offen'
        assert len(client.get(f'/api/projects/{project.id}/runs?branch_id={branch.id}').json()) == 4
        assert len(client.get(f'/api/projects/{project.id}/turns?branch_id={branch.id}').json()) == 2
        assert len(client.get(f'/api/projects/{project.id}/revisions').json()) == 1
        assert client.get(f'/api/projects/{project.id}/export/json').status_code == 200
        assert client.get(f'/api/projects/{project.id}/export/markdown').status_code == 200
        assert Memory(db).list_branches(project.id)[0].head_id == branch.head_id
        proposal_id = client.get(f'/api/projects/{project.id}/proposals').json()[0]['id']
        assert client.post(f'/api/proposals/{proposal_id}/approve',
                           json={'author': 'Autor', 'explicit_approval': False}).status_code != 200
        assert client.post(f'/api/proposals/{proposal_id}/approve',
                           json={'author': 'Autor', 'explicit_approval': True}).status_code == 200
        assert Memory(db).list_branches(project.id)[0].head_id != branch.head_id


def test_loopback_schutz_und_projektwechsel_beim_job(tmp_path):
    db = tmp_path / 'ui.sqlite3'
    memory = Memory(db)
    a = memory.create_project('Synthetisches A')
    b = memory.create_project('Synthetisches B')
    branch = memory.list_branches(a.id)[0]
    app = create_app(db, provider_factory=lambda model: FakeProvider(['Antwort A']))
    with TestClient(app) as client:
        assert client.get('/api/projects', headers={'host': 'evil.example'}).status_code == 403
        assert client.post('/api/projects', headers={'origin': 'http://evil.example'},
                           json={'title': 'Fremd'}).status_code == 403
        job = client.post('/api/jobs', json={'project_id': str(a.id), 'branch_id': str(branch.id),
                          'procedure': 'V01', 'task': 'Frage', 'model': 'fake'}).json()
        assert client.get(f'/api/projects/{b.id}').status_code == 200
        outcome = await_job(client, job['id'])
        assert outcome['project_id'] == str(a.id)
        assert memory.list_turns(b.id, memory.list_branches(b.id)[0].id) == []


def test_einzelner_stoffkeim_als_quelle_und_fremde_id(tmp_path):
    from uuid import UUID, uuid4
    from storyforge import Autorenredaktion, Operation, Quelle

    db = tmp_path / 'einzel.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetische Quelle')
    branch = memory.list_branches(project.id)[0]
    seed_id = uuid4()
    run_id = memory.save_creative_run(project.id, branch.id, branch.head_id, 'fake', 'Zwei Keime',
                                      {'procedure': 'V02'}, [{'id': str(seed_id), 'title': 'Gewählter Keim'},
                                                            {'id': str(uuid4()), 'title': 'Anderer Keim'}])
    app = create_app(db, provider_factory=lambda model: FakeProvider([mutation(Operation.FREI)]))
    with TestClient(app) as client:
        runs = client.get(f'/api/projects/{project.id}/runs?branch_id={branch.id}').json()
        assert len(runs[0]['candidates']) == 2
    editor = Autorenredaktion(memory, FakeProvider([mutation(Operation.FREI)]), NarrativeLibrary.load(CARDS))
    selected = editor.mutate(project.id, branch.id, 'Wandel',
                             Quelle(art='creative_run', id=run_id, candidate_id=seed_id),
                             operation=Operation.FREI)
    assert selected.manifest['source']['candidate_id'] == str(seed_id)
    try:
        editor.mutate(project.id, branch.id, 'Wandel',
                      Quelle(art='creative_run', id=run_id, candidate_id=uuid4()),
                      operation=Operation.FREI)
    except KeyError:
        pass
    else:
        raise AssertionError('Fremder Stoffkeim wurde akzeptiert')


def test_hintergrundabbruch_ohne_gespeicherten_dialog(tmp_path):
    from storyforge import ModelCancelled

    db = tmp_path / 'abbruch.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetischer Abbruch')
    branch = memory.list_branches(project.id)[0]

    class WaitingProvider(FakeProvider):
        def generate(self, request, cancel=None):
            for _ in range(200):
                if cancel is not None and cancel.wait(.005):
                    raise ModelCancelled('Abgebrochen')
            return super().generate(request, cancel)

    app = create_app(db, provider_factory=lambda model: WaitingProvider(['Nicht speichern']))
    with TestClient(app) as client:
        job_id = client.post('/api/jobs', json={'project_id': str(project.id), 'branch_id': str(branch.id),
            'procedure': 'V01', 'task': 'Warte', 'model': 'fake'}).json()['id']
        assert client.get('/api/projects').status_code == 200
        client.post('/api/jobs/' + job_id + '/cancel')
        outcome = await_job(client, job_id)
        assert outcome['status'] == 'abgebrochen'
        assert memory.list_turns(project.id, branch.id) == []


def test_modellstatus_offline_und_online(tmp_path, monkeypatch):
    import io
    from unittest.mock import patch
    db = tmp_path / 'modelle.sqlite3'
    app = create_app(db)
    with TestClient(app) as client:
        with patch('urllib.request.urlopen', side_effect=OSError('offline')):
            assert client.get('/api/models').json() == {'online': False, 'models': []}
        response = io.BytesIO(json.dumps({'models': [{'name': 'synthetisch:latest'}]}).encode())
        with patch('urllib.request.urlopen', return_value=response):
            assert client.get('/api/models').json() == {'online': True, 'models': ['synthetisch:latest']}


def test_projekt_und_variante_per_http_nach_neustart(tmp_path):
    db = tmp_path / 'start.sqlite3'
    with TestClient(create_app(db)) as client:
        project = client.post('/api/projects', json={'title': 'Synthetischer Neubeginn'}).json()
        assert project['title'] == 'Synthetischer Neubeginn'
        branch = client.get('/api/projects/' + project['id']).json()['branches'][0]
        alternative = client.post('/api/projects/' + project['id'] + '/branches',
                                  json={'name': 'Zweite Fassung',
                                        'from_revision_id': branch['head_id']}).json()
        assert alternative['name'] == 'Zweite Fassung'
    with TestClient(create_app(db)) as client:
        restored = client.get('/api/projects/' + project['id']).json()
        assert {b['name'] for b in restored['branches']} == {'Original', 'Zweite Fassung'}


def test_streaming_teilantwort_erst_nach_abschluss_persistiert(tmp_path):
    from threading import Event
    from storyforge import ModelResponse

    db = tmp_path / 'stream.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetisches Gespräch')
    branch = memory.list_branches(project.id)[0]
    first, release = Event(), Event()

    class Streaming(FakeProvider):
        def generate_stream(self, request, on_chunk, cancel=None):
            on_chunk('Sichtbarer ')
            first.set()
            release.wait(2)
            if cancel and cancel.is_set():
                from storyforge import ModelCancelled
                raise ModelCancelled('Abgebrochen')
            on_chunk('Abschluss')
            return ModelResponse(content='Sichtbarer Abschluss', model=self.model,
                                 wall_seconds=1.5, output_tokens=2,
                                 generation_tokens_per_second=1.3)

    with TestClient(create_app(db, provider_factory=lambda model: Streaming([]))) as client:
        job_id = client.post('/api/jobs', json={'project_id': str(project.id),
            'branch_id': str(branch.id), 'procedure': 'V01', 'task': 'Testfrage', 'model': 'fake'}).json()['id']
        assert first.wait(2)
        assert client.get('/api/jobs/' + job_id).json()['partial'] == 'Sichtbarer '
        assert client.get(f'/api/projects/{project.id}/turns?branch_id={branch.id}').json() == []
        release.set()
        done = await_job(client, job_id)
        assert done['status'] == 'fertig'
        assert done['result']['output_tokens'] == 2
    with TestClient(create_app(db)) as restarted:
        turns = restarted.get(f'/api/projects/{project.id}/turns?branch_id={branch.id}').json()
        assert [turn['content'] for turn in turns] == ['Testfrage', 'Sichtbarer Abschluss']
        assert turns[0]['sequence'] < turns[1]['sequence']


def test_streaming_abbruch_speichert_keine_teilantwort(tmp_path):
    from threading import Event
    from storyforge import ModelCancelled

    db = tmp_path / 'cancel-stream.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetischer Abbruch')
    branch = memory.list_branches(project.id)[0]
    first = Event()

    class Streaming(FakeProvider):
        def generate_stream(self, request, on_chunk, cancel=None):
            on_chunk('Unvollständig')
            first.set()
            cancel.wait(2)
            raise ModelCancelled('Abgebrochen')

    with TestClient(create_app(db, provider_factory=lambda model: Streaming([]))) as client:
        job_id = client.post('/api/jobs', json={'project_id': str(project.id),
            'branch_id': str(branch.id), 'procedure': 'V01', 'task': 'Test', 'model': 'fake'}).json()['id']
        assert first.wait(2)
        client.post('/api/jobs/' + job_id + '/cancel')
        done = await_job(client, job_id)
        assert done['status'] == 'abgebrochen'
        assert done['partial'] == 'Unvollständig'
        assert client.get(f'/api/projects/{project.id}/turns?branch_id={branch.id}').json() == []


def test_gespraechsquelle_und_idee_bleiben_projektbezogen_und_unverbindlich(tmp_path):
    db = tmp_path / 'quellen.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetisches A')
    other = memory.create_project('Synthetisches B')
    branch = memory.list_branches(project.id)[0]
    other_branch = memory.list_branches(other.id)[0]
    _, turn_id = memory.save_exchange(project.id, branch.id, branch.head_id,
                                      'Frage', 'Ausgewählter synthetischer Gedanke', {}, 'fake')
    with TestClient(create_app(db, provider_factory=lambda model: FakeProvider(['Vertiefung']))) as client:
        wrong = client.post(f'/api/turns/{turn_id}/stage?project_id={other.id}&branch_id={other_branch.id}')
        assert wrong.status_code == 404
        proposal = client.post(f'/api/turns/{turn_id}/stage?project_id={project.id}&branch_id={branch.id}').json()
        assert proposal['status'] == 'offen'
        assert memory.list_branches(project.id)[0].head_id == branch.head_id
        job = client.post('/api/jobs', json={'project_id': str(project.id), 'branch_id': str(branch.id),
            'procedure': 'V01', 'task': 'Vertiefe', 'model': 'fake',
            'options': {'source_turn_id': str(turn_id)}}).json()['id']
        assert await_job(client, job)['status'] == 'fertig'
        turns = client.get(f'/api/projects/{project.id}/turns?branch_id={branch.id}').json()
        assert 'Ausgewählter synthetischer Gedanke' in turns[-2]['content']
        foreign_job = client.post('/api/jobs', json={'project_id': str(other.id),
            'branch_id': str(other_branch.id), 'procedure': 'V01', 'task': 'Fremd', 'model': 'fake',
            'options': {'source_turn_id': str(turn_id)}}).json()['id']
        assert await_job(client, foreign_job)['status'] == 'fehler'
        assert memory.list_turns(other.id, other_branch.id) == []
        approved = client.post(f"/api/proposals/{proposal['id']}/approve",
                               json={'author': 'Testautor', 'explicit_approval': True})
        assert approved.status_code == 200
        assert client.post(f'/api/turns/{turn_id}/stage?project_id={project.id}&branch_id={branch.id}').status_code == 409


def test_gespraechsverlauf_ohne_anzeigegrenze(tmp_path):
    db = tmp_path / 'voll.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetischer Verlauf')
    branch = memory.list_branches(project.id)[0]
    for number in range(55):
        memory.save_exchange(project.id, branch.id, branch.head_id,
                             f'Frage {number}', f'Antwort {number}', {}, 'fake')
    with TestClient(create_app(db)) as client:
        turns = client.get(f'/api/projects/{project.id}/turns?branch_id={branch.id}').json()
        assert len(turns) == 110
        assert turns[0]['content'] == 'Frage 0'
        assert turns[-1]['content'] == 'Antwort 54'


def test_gespeicherter_stoffkeim_als_folgequelle_und_fremdquelle_abgelehnt(tmp_path):
    from uuid import uuid4

    db = tmp_path / 'folge.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetisches Quellenprojekt')
    other = memory.create_project('Fremdes Projekt')
    branch = memory.list_branches(project.id)[0]
    other_branch = memory.list_branches(other.id)[0]
    candidate_id = uuid4()
    run_id = memory.save_creative_run(project.id, branch.id, branch.head_id, 'fake', 'Ideen',
                                      {'procedure': 'V02'},
                                      [{'id': str(candidate_id), 'title': 'Gewählter Keim',
                                        'premise': 'Synthetische Quelle'},
                                       {'id': str(uuid4()), 'title': 'Anderer Keim'}])
    provider = FakeProvider(['Neue Antwort'])
    with TestClient(create_app(db, provider_factory=lambda model: provider)) as client:
        job = client.post('/api/jobs', json={'project_id': str(project.id), 'branch_id': str(branch.id),
            'procedure': 'V01', 'task': 'Vertiefe', 'model': 'fake',
            'options': {'source_run_id': str(run_id), 'source_candidate_id': str(candidate_id)}}).json()['id']
        assert await_job(client, job)['status'] == 'fertig'
        sent = provider.requests[0].messages[-1]['content']
        assert 'Gewählter Keim' in sent and 'Anderer Keim' not in sent
        wrong = client.post('/api/jobs', json={'project_id': str(other.id),
            'branch_id': str(other_branch.id), 'procedure': 'V01', 'task': 'Vertiefe', 'model': 'fake',
            'options': {'source_run_id': str(run_id)}}).json()['id']
        assert await_job(client, wrong)['status'] == 'fehler'
        assert memory.list_turns(other.id, other_branch.id) == []


def test_gespraechsquelle_darf_nicht_veraendert_werden(tmp_path):
    db = tmp_path / 'turn-quelle.sqlite3'
    memory = Memory(db)
    project = memory.create_project('Synthetisches Gespräch')
    branch = memory.list_branches(project.id)[0]
    _, turn_id = memory.save_exchange(project.id, branch.id, branch.head_id,
                                      'Frage', 'Originaltext', {}, 'fake')
    with TestClient(create_app(db, provider_factory=lambda model: FakeProvider([critique()]))) as client:
        job = client.post('/api/jobs', json={'project_id': str(project.id), 'branch_id': str(branch.id),
            'procedure': 'V05', 'task': 'Prüfen', 'model': 'fake',
            'options': {'source_turn_id': str(turn_id), 'source': {'art': 'frei',
                        'beschreibung': 'Veränderter Text'}}}).json()['id']
        outcome = await_job(client, job)
        assert outcome['status'] == 'fehler'
        assert 'verändert' in outcome['error']
        assert memory.list_creative_runs(project.id, branch.id) == []
