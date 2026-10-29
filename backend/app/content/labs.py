"""Лабораторные из файлов; проверочные программы остаются на сервере."""
import json
import re
from pydantic import BaseModel, Field, model_validator
from fastapi import HTTPException
from app.config import settings
from app.content.loader import TestCase

class Stage(BaseModel):
    id: str = Field(pattern=r'^[a-z0-9-]{1,60}$')
    title: str
    description: str = ''
    hint: str = ''
    tests: list[TestCase] = Field(default_factory=list, max_length=20)
    harness: str = ''

class Lab(BaseModel):
    title: str
    order: int = 0
    variant: str = ''
    source: str = ''
    stages: list[Stage] = Field(default_factory=list, max_length=30)
    tests: list[TestCase] = Field(default_factory=list, max_length=20)
    max_points: int = 0
    execution_note: str = ''
    defense: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def unique_stages(self):
        if len({s.id for s in self.stages}) != len(self.stages):
            raise ValueError('Повторяющиеся id этапов')
        return self

def load_lab(slug):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,60}', slug):
        raise HTTPException(404, 'Лабораторная не найдена')
    base = (settings.content_dir / 'labs').resolve()
    folder = (base / slug).resolve()
    if not folder.is_relative_to(base) or not (folder / 'lab.json').is_file():
        raise HTTPException(404, 'Лабораторная не найдена')
    def read(name):
        p = (folder / name).resolve()
        if not p.is_relative_to(base):
            raise ValueError('Файл вне папки лабораторных')
        return p.read_text(encoding='utf-8')
    return Lab.model_validate(json.loads(read('lab.json'))), read('statement.md'), read('template.c')

def lab_slugs():
    folder = settings.content_dir / 'labs'
    if not folder.exists():
        return []
    return sorted((p.name for p in folder.iterdir() if (p / 'lab.json').is_file()),
                  key=lambda s: (load_lab(s)[0].order, s))
