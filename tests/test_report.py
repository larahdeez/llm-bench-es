"""Pruebas del módulo de informes."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from llm_bench.report import (
    accuracy_table,
    bootstrap_ci,
    consistency,
    hardest_questions,
    original_choice,
    position_bias,
    report,
)


def make_results() -> pd.DataFrame:
    """Dos modelos, dos preguntas y dos repeticiones con opciones barajadas.

    - m1 acierta siempre.
    - m2 elige siempre la letra A: acierta q1 en la repetición 0 (la correcta
      está en A) y falla el resto.
    """
    rows = []
    # (repetición, pregunta, orden mostrado, letra correcta tras barajar)
    shown = [
        (0, "q1", "0,1,2,3", "A"),
        (1, "q1", "1,0,2,3", "B"),
        (0, "q2", "2,1,0,3", "C"),
        (1, "q2", "3,1,2,0", "D"),
    ]
    for model in ("m1", "m2"):
        for repetition, qid, order, gold in shown:
            prediction = gold if model == "m1" else "A"
            rows.append(
                {
                    "model": model,
                    "repetition": repetition,
                    "question_id": qid,
                    "topic": "redes" if qid == "q1" else "sistemas",
                    "difficulty": "facil",
                    "gold": gold,
                    "prediction": prediction,
                    "parsed": True,
                    "correct": prediction == gold,
                    "choice_order": order,
                }
            )
    return pd.DataFrame(rows)


def test_bootstrap_ci_contains_the_mean_and_is_reproducible() -> None:
    values = np.array([0.0, 1.0, 1.0, 0.5, 1.0])
    low, high = bootstrap_ci(values, 500, seed=1)
    assert low <= values.mean() <= high
    assert (low, high) == bootstrap_ci(values, 500, seed=1)


def test_bootstrap_ci_of_constant_values_has_no_width() -> None:
    assert bootstrap_ci(np.ones(10), 200, seed=0) == (1.0, 1.0)


def test_accuracy_table_resamples_questions() -> None:
    table = accuracy_table(make_results(), 200, seed=0)
    assert table.loc["m1", "accuracy"] == 1.0
    assert table.loc["m2", "accuracy"] == 0.25
    assert table.loc["m2", "questions"] == 2
    assert table.loc["m2", "repetitions"] == 2
    assert table.index[0] == "m1"  # ordenada de mayor a menor acierto


def test_original_choice_undoes_the_shuffle() -> None:
    # Se mostró la opción original 3 en la posición A.
    assert original_choice("A", "3,1,2,0") == "D"
    assert original_choice("B", "") == "B"
    assert original_choice("", "0,1,2,3") == ""


def test_consistency_compares_content_not_letters() -> None:
    cons = consistency(make_results())
    # m1 elige siempre la opción correcta (mismo contenido aunque cambie la letra).
    assert cons["m1"] == 1.0
    # m2 elige siempre la A, pero la A muestra opciones distintas en cada repetición.
    assert cons["m2"] == 0.0


def test_position_bias_detects_a_preferred_letter() -> None:
    shares = position_bias(make_results())
    assert shares.loc["m2", "A"] == 1.0
    assert shares.loc["(correctas)", "A"] == pytest.approx(0.25)


def test_hardest_questions_lists_those_below_threshold() -> None:
    # q1: 3 de 4 aciertos (75 %); q2: 2 de 4 (50 %). Ordenadas de menor a mayor.
    assert list(hardest_questions(make_results(), threshold=0.8).index) == ["q2", "q1"]
    assert list(hardest_questions(make_results(), threshold=0.7).index) == ["q2"]


def test_report_writes_summary_and_figures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    results = tmp_path / "results_prueba.csv"
    make_results().to_csv(results, index=False)
    config = tmp_path / "config.yaml"
    config.write_text(
        "experiment: {seed: 0, bootstrap_samples: 100}\noutput: {figures_dir: reports/figures}\n",
        encoding="utf-8",
    )

    summary = report(results, config)

    text = summary.read_text(encoding="utf-8")
    assert "## Acierto por modelo" in text
    assert "figures/results_prueba/accuracy.png" in text
    for name in ("accuracy", "accuracy_by_topic", "accuracy_by_difficulty", "position_bias"):
        assert (tmp_path / "reports/figures/results_prueba" / f"{name}.png").exists()
