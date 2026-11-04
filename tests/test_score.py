"""Pruebas de formato de prompts y extracción de respuestas."""

from llm_bench.score import extract_choice, format_prompt, shuffle_choices


def test_format_prompt_labels_options_with_letters() -> None:
    template = "P: {question}\n{options}"
    assert format_prompt(template, "¿x?", ["a", "b"]) == "P: ¿x?\nA) a\nB) b"


def test_extract_plain_letter() -> None:
    assert extract_choice("C", 4) == "C"


def test_extract_letter_followed_by_text() -> None:
    assert extract_choice("B) 443, porque es HTTPS", 4) == "B"


def test_extract_ignores_leading_blank_lines_and_markdown() -> None:
    assert extract_choice("\n**A**\n", 4) == "A"


def test_rejects_letter_outside_choices() -> None:
    assert extract_choice("E", 4) is None


def test_sentence_is_not_read_as_a_letter() -> None:
    assert extract_choice("Aunque no estoy seguro", 4) is None


def test_empty_response_returns_none() -> None:
    assert extract_choice("   ", 4) is None


CHOICES = ["Física", "Enlace", "Red", "Transporte"]


def test_shuffle_is_deterministic_for_the_same_key() -> None:
    assert shuffle_choices(CHOICES, "C", "42-0-redes-0001") == shuffle_choices(
        CHOICES, "C", "42-0-redes-0001"
    )


def test_shuffle_keeps_the_same_options() -> None:
    shuffled, _, order = shuffle_choices(CHOICES, "C", "42-1-redes-0001")
    assert sorted(shuffled) == sorted(CHOICES)
    assert sorted(order) == [0, 1, 2, 3]


def test_shuffle_moves_the_answer_letter_with_its_option() -> None:
    for repetition in range(20):
        shuffled, answer, _ = shuffle_choices(CHOICES, "C", f"42-{repetition}-redes-0001")
        assert shuffled["ABCD".index(answer)] == "Red"


def test_different_keys_give_different_orders() -> None:
    orders = {tuple(shuffle_choices(CHOICES, "C", f"42-{r}-x")[2]) for r in range(20)}
    assert len(orders) > 1
