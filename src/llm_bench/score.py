"""Formato de los prompts y extracción de la respuesta en preguntas de opción múltiple."""

from __future__ import annotations

import random
import re

LETTERS = "ABCDEFGH"

# Acepta una letra al inicio de la primera línea, opcionalmente entre
# asteriscos o paréntesis y seguida de ")", ".", ":" o un espacio.
_LEADING_LETTER = re.compile(r"^\W*([A-H])(?:[\)\.:]|\s|$)")


def format_prompt(template: str, question: str, choices: list[str]) -> str:
    """Rellena la plantilla con el enunciado y las opciones etiquetadas."""
    options = "\n".join(f"{LETTERS[i]}) {choice}" for i, choice in enumerate(choices))
    return template.format(question=question, options=options)


def shuffle_choices(choices: list[str], answer: str, key: str) -> tuple[list[str], str, list[int]]:
    """Baraja las opciones de forma reproducible y recoloca la letra correcta.

    `key` fija el orden: la misma clave produce siempre la misma permutación,
    en cualquier ordenador. Devuelve las opciones barajadas, la nueva letra
    correcta y `order`, donde `order[i]` es la posición original de la opción
    que ahora se muestra en el lugar `i`.
    """
    order = list(range(len(choices)))
    random.Random(key).shuffle(order)
    shuffled = [choices[i] for i in order]
    new_answer = LETTERS[order.index(LETTERS.index(answer))]
    return shuffled, new_answer, order


def extract_choice(text: str, n_choices: int) -> str | None:
    """Devuelve la letra elegida por el modelo, o None si no se puede leer.

    Solo se mira la primera línea no vacía. Si el modelo responde con una frase
    en lugar de una letra, la respuesta cuenta como no interpretable.
    """
    valid = set(LETTERS[:n_choices])
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        cleaned = line.strip().strip("*_`").strip()
        match = _LEADING_LETTER.match(cleaned)
        if match and match.group(1) in valid:
            return match.group(1)
        return None
    return None
