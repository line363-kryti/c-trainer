import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.deps import get_current_user
from app.content.labs import load_lab, lab_slugs
from app.db import get_db
from app.models import LabProgress, User
from app.limiter import limiter, user_key
from app.routers.tasks import CodeIn, TaskRunIn, CheckIn, _judge
from app.runner.deps import execute, get_runner

router = APIRouter(prefix='/api/labs', tags=['labs'])
def digest(code):
    return hashlib.sha256(code.encode()).hexdigest()
def row_for(db, user, slug, template):
    # Сначала создаём строку, затем блокируем её на время короткого изменения.
    from sqlalchemy.dialects.postgresql import insert
    db.execute(insert(LabProgress).values(user_id=user.id, lab_slug=slug, code=template, state='{}')
               .on_conflict_do_nothing())
    return db.scalar(select(LabProgress).where(LabProgress.user_id == user.id,
                     LabProgress.lab_slug == slug).with_for_update())
def status(row):
    if row is None: return 'Не начата'
    state = json.loads(row.state)
    if state.get('defended'): return 'Защищена'
    if state.get('final', {}).get('hash') == digest(row.code) and state['final']['passed']:
        return 'Тесты пройдены'
    return 'В работе'

@router.get('')
def listing(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = {r.lab_slug: r for r in db.scalars(select(LabProgress).where(LabProgress.user_id == user.id))}
    return [dict(slug=s, title=load_lab(s)[0].title, variant=load_lab(s)[0].variant,
                 max_points=load_lab(s)[0].max_points, status=status(rows.get(s))) for s in lab_slugs()]

@router.get('/{slug}')
def detail(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lab, statement, template = load_lab(slug)
    row = db.get(LabProgress, (user.id, slug))
    return dict(title=lab.title, variant=lab.variant, source=lab.source, statement=statement,
        max_points=lab.max_points, can_check=bool(lab.tests), execution_note=lab.execution_note,
        code=row.code if row else template, state=json.loads(row.state) if row else {},
        status=status(row), defense=lab.defense,
        stages=[dict(id=s.id, title=s.title, description=s.description, hint=s.hint,
                     automatic=bool(s.tests)) for s in lab.stages])

@router.put('/{slug}/code')
def save(slug: str, data: CodeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, _, template = load_lab(slug)
    row = row_for(db, user, slug, template)
    row.code = data.code
    db.commit()
    return {'saved': True}

@router.post('/{slug}/run')
@limiter.limit('10/minute', key_func=user_key)
async def run(request: Request, slug: str, data: TaskRunIn,
              user: User = Depends(get_current_user), runner=Depends(get_runner)):
    load_lab(slug)
    return await execute(runner, data.code, data.stdin)

class LabCheckIn(CheckIn):
    stage: str | None = None

@router.post('/{slug}/check')
@limiter.limit('5/minute', key_func=user_key)
async def check(request: Request, slug: str, data: LabCheckIn,
                user: User = Depends(get_current_user), db: Session = Depends(get_db), runner=Depends(get_runner)):
    lab, _, template = load_lab(slug)
    tests, code = lab.tests, data.code
    if data.stage is not None:
        stage = next((s for s in lab.stages if s.id == data.stage), None)
        if stage is None: raise HTTPException(404, 'Этап не найден')
        if not stage.tests: raise HTTPException(400, 'Этот этап отмечается вручную')
        tests = stage.tests
        if stage.harness:
            code = '#define main student_main\n' + code + '\n#undef main\n' + stage.harness
    if not tests:
        raise HTTPException(409, 'Для этой работы автоматические тесты пока не настроены. Используй чек-лист требований.')
    results, error = [], None
    for i, test in enumerate(tests, 1):
        outcome = await execute(runner, code, test.input)
        if outcome.status == 'compile_error':
            error = outcome.compile_output
            break
        results.append(_judge(i, test, outcome).model_dump())
    passed = not error and len(results) == len(tests) and all(r['passed'] for r in results)
    record = dict(hash=digest(data.code), passed=bool(passed), manual=False)
    # Код мог измениться, пока шли тесты: сохраняем результат с хэшем,
    # но никогда не затираем более свежий черновик результатом проверки.
    row = row_for(db, user, slug, template)
    state = json.loads(row.state)
    if data.stage:
        state.setdefault('stages', {})[data.stage] = record
    else:
        state['final'] = record
    row.state = json.dumps(state)
    db.commit()
    return dict(**record, results=results, compile_error=error, total=len(tests))

class MarkIn(CodeIn):
    done: bool

@router.put('/{slug}/stages/{stage_id}')
def mark(slug: str, stage_id: str, data: MarkIn,
         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lab, _, template = load_lab(slug)
    stage = next((s for s in lab.stages if s.id == stage_id), None)
    if stage is None: raise HTTPException(404, 'Этап не найден')
    if stage.tests: raise HTTPException(400, 'Для этого этапа нужна проверка тестами')
    row = row_for(db, user, slug, template)
    state = json.loads(row.state)
    state.setdefault('stages', {})[stage_id] = dict(hash=digest(data.code), passed=data.done, manual=True)
    row.state = json.dumps(state)
    db.commit()
    return state

class DefendedIn(BaseModel):
    done: bool

@router.put('/{slug}/defended')
def defended(slug: str, data: DefendedIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, _, template = load_lab(slug)
    row = row_for(db, user, slug, template)
    state = json.loads(row.state)
    state['defended'] = data.done
    row.state = json.dumps(state)
    db.commit()
    return state
