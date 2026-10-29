import json
import pytest
from app.config import settings
from app.main import app
from app.runner.deps import get_runner
from app.runner.base import RunResult

@pytest.fixture
def labs(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'content_dir', tmp_path)
    folder = tmp_path / 'labs' / 'fixture'
    folder.mkdir(parents=True)
    data = dict(title='Тестовая работа', tests=[dict(input='2', output='2')],
                stages=[dict(id='auto', title='Функция', tests=[dict(input='2', output='2')], harness='int main(){return 0;}'),
                        dict(id='manual', title='Проверка требований')])
    (folder / 'lab.json').write_text(json.dumps(data), encoding='utf-8')
    (folder / 'statement.md').write_text('Условие', encoding='utf-8')
    (folder / 'template.c').write_text('int main(){}', encoding='utf-8')
    return folder

@pytest.fixture
def user(client):
    assert client.post('/api/auth/register', json=dict(email='labs@example.com', password='secret123')).status_code == 201
    return client

class Runner:
    def __init__(self): self.code = ''
    async def run(self, code, stdin):
        self.code = code
        if code == 'BROKEN': return RunResult(status='compile_error', compile_output='error')
        return RunResult(status='ok', stdout=stdin)

@pytest.fixture
def runner():
    r = Runner()
    app.dependency_overrides[get_runner] = lambda: r
    yield r
    app.dependency_overrides.pop(get_runner, None)

B = '/api/labs/fixture'

def test_auth_and_empty(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'content_dir', tmp_path)
    assert client.get('/api/labs').status_code == 401
    client.post('/api/auth/register', json=dict(email='empty@example.com', password='secret123'))
    assert client.get('/api/labs').json() == []

def test_save_and_isolation(user, labs):
    assert user.put(B+'/code', json={'code':'draft'}).status_code == 200
    assert user.get(B).json()['code'] == 'draft'
    user.post('/api/auth/logout')
    user.post('/api/auth/register', json=dict(email='other@example.com', password='secret123'))
    assert user.get(B).json()['code'] == 'int main(){}'
    assert user.get('/api/labs').json()[0]['status'] == 'Не начата'

def test_checks_stale_and_preserve_new_draft(user, labs, runner):
    user.put(B+'/code', json={'code':'draft'})
    result = user.post(B+'/check', json={'code':'draft'}).json()
    assert result['passed']
    assert user.get('/api/labs').json()[0]['status'] == 'Тесты пройдены'
    user.put(B+'/code', json={'code':'new draft'})
    assert user.get('/api/labs').json()[0]['status'] == 'В работе'
    user.post(B+'/check', json={'code':'draft'})
    assert user.get(B).json()['code'] == 'new draft'
    assert user.get('/api/labs').json()[0]['status'] == 'В работе'

def test_stage_harness_and_manual(user, labs, runner):
    data = user.get(B).json()
    assert 'tests' not in data and 'harness' not in data['stages'][0]
    assert user.post(B+'/check', json={'code':'int main(){}','stage':'auto'}).json()['passed']
    assert '#define main student_main' in runner.code
    assert user.put(B+'/stages/auto', json={'code':'x','done':True}).status_code == 400
    assert user.put(B+'/stages/manual', json={'code':'x','done':True}).json()['stages']['manual']['manual']
    assert user.post(B+'/check', json={'code':'x','stage':'manual'}).status_code == 400
    assert user.post(B+'/check', json={'code':'x','stage':'missing'}).status_code == 404

def test_compilation_and_defense(user, labs, runner):
    result = user.post(B+'/check', json={'code':'BROKEN'}).json()
    assert result['compile_error'] == 'error' and not result['passed']
    user.put(B+'/defended', json={'done':True})
    assert user.get('/api/labs').json()[0]['status'] == 'Защищена'
    user.put(B+'/defended', json={'done':False})
    assert user.get('/api/labs').json()[0]['status'] == 'В работе'

def test_missing_invalid_and_code_limit(user, labs):
    assert user.get('/api/labs/not-found').status_code == 404
    assert user.get('/api/labs/..%5C..').status_code == 404
    assert user.put(B+'/code', json={'code':'x'*70000}).status_code == 422

def test_work_without_automatic_tests(user, labs, runner):
    data = json.loads((labs / 'lab.json').read_text(encoding='utf-8'))
    data['tests'] = []
    (labs / 'lab.json').write_text(json.dumps(data), encoding='utf-8')
    assert user.get(B).json()['can_check'] is False
    response = user.post(B+'/check', json={'code':'int main(){}'})
    assert response.status_code == 409
    assert user.get('/api/labs').json()[0]['status'] == 'Не начата'
