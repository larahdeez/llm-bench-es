"""Pruebas del esquema del conjunto de preguntas.

Estas pruebas se activan cuando exista data/questions.jsonl. Mientras tanto
se omiten, para que el repositorio pase la integración continua desde el inicio.
"""

import json
from pathlib import Path

import pytest

DATASET = Path("data/questions.jsonl")
REQUIRED = {"id", "task_type", "topic", "difficulty", "question", "answer", "source", "annotator"}
TASK_TYPES = {"multiple_choice", "short_answer", "extraction", "reasoning"}
DIFFICULTIES = {"facil", "media", "dificil"}


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_every_question_has_required_fields() -> None:
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        missing = REQUIRED - item.keys()
        assert not missing, f"{item.get('id', '?')} le faltan campos: {missing}"


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_ids_are_unique() -> None:
    ids = [json.loads(line)["id"] for line in DATASET.read_text(encoding="utf-8").splitlines()]
    assert len(ids) == len(set(ids)), "Hay identificadores duplicados"


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_enums_and_choices_are_valid() -> None:
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        assert item["task_type"] in TASK_TYPES
        assert item["difficulty"] in DIFFICULTIES
        if item["task_type"] == "multiple_choice":
            assert len(item.get("choices", [])) >= 4, f"{item['id']} necesita al menos 4 opciones"
