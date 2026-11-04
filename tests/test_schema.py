"""Pruebas del esquema del conjunto de preguntas.

Estas pruebas se activan cuando exista data/questions.jsonl. Mientras tanto
se omiten, para que el repositorio pase la integración continua desde el inicio.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

DATASET = Path("data/questions.jsonl")
REQUIRED = {"id", "task_type", "topic", "difficulty", "question", "answer", "source", "annotator"}
TASK_TYPES = {"multiple_choice", "short_answer", "extraction", "reasoning"}
DIFFICULTIES = {"facil", "media", "dificil"}
ID_PATTERN = re.compile(r"^[a-z]+-[0-9]{4}$")
LETTERS = "ABCDEFGH"


def load_items() -> list[dict[str, Any]]:
    """Lee todas las preguntas del conjunto."""
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]


def multiple_choice_items() -> list[dict[str, Any]]:
    return [item for item in load_items() if item["task_type"] == "multiple_choice"]


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


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_ids_follow_the_pattern() -> None:
    for item in load_items():
        assert ID_PATTERN.match(item["id"]), f"{item['id']} no cumple el patrón tema-0000"


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_answer_letter_points_to_an_existing_choice() -> None:
    for item in multiple_choice_items():
        valid = LETTERS[: len(item["choices"])]
        assert item["answer"] in valid, f"{item['id']}: la respuesta {item['answer']} no existe"


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_choices_are_not_repeated() -> None:
    for item in multiple_choice_items():
        choices = item["choices"]
        assert len(set(choices)) == len(choices), f"{item['id']}: opciones repetidas"


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_no_all_or_none_of_the_above() -> None:
    # La guía de anotación prohíbe estas opciones.
    forbidden = ("todas las anteriores", "ninguna de las anteriores")
    for item in multiple_choice_items():
        for choice in item["choices"]:
            assert not any(f in choice.lower() for f in forbidden), f"{item['id']}: '{choice}'"


@pytest.mark.skipif(not DATASET.exists(), reason="Conjunto de preguntas aún no creado")
def test_questions_are_not_duplicated() -> None:
    texts = [item["question"].strip().lower() for item in load_items()]
    assert len(texts) == len(set(texts)), "Hay enunciados duplicados"
