"""Ejecuta el benchmark de opción múltiple y guarda los resultados en CSV.

Uso desde la raíz del repositorio:

    python -m llm_bench.run --config configs/default.yaml

Las preguntas de tipo distinto a opción múltiple se omiten por ahora.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from llm_bench.client import chat
from llm_bench.score import extract_choice, format_prompt


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Lee un fichero JSON Lines con una pregunta por línea."""
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def run(config_path: Path) -> pd.DataFrame:
    """Evalúa cada modelo sobre cada pregunta y guarda el CSV de resultados."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    exp = config["experiment"]
    inf = config["inference"]

    template = Path(inf["prompt_template"]).read_text(encoding="utf-8")
    questions = [
        q
        for q in load_questions(Path(config["dataset"]["path"]))
        if q["task_type"] == "multiple_choice"
    ]

    rows: list[dict[str, Any]] = []
    for model in config["models"]:
        for repetition in range(exp["repetitions"]):
            for question in questions:
                prompt = format_prompt(template, question["question"], question["choices"])
                generation = chat(
                    base_url=inf["base_url"],
                    model=model["tag"],
                    prompt=prompt,
                    temperature=inf["temperature"],
                    max_tokens=inf["max_tokens"],
                    context_length=inf["context_length"],
                    seed=exp["seed"] + repetition,
                    think=model.get("think"),
                )
                prediction = extract_choice(generation.text, len(question["choices"]))
                tokens_per_second = (
                    generation.eval_count / generation.eval_seconds
                    if generation.eval_seconds > 0
                    else float("nan")
                )
                rows.append(
                    {
                        "model": model["name"],
                        "tag": model["tag"],
                        "quantization": model.get("quantization", ""),
                        "repetition": repetition,
                        "question_id": question["id"],
                        "topic": question["topic"],
                        "difficulty": question["difficulty"],
                        "gold": question["answer"],
                        "prediction": prediction or "",
                        "parsed": prediction is not None,
                        "correct": prediction == question["answer"],
                        "raw_response": generation.text,
                        "total_seconds": generation.total_seconds,
                        "eval_count": generation.eval_count,
                        "tokens_per_second": tokens_per_second,
                    }
                )

    df = pd.DataFrame(rows)
    output = Path(config["output"]["results_csv"])
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta el benchmark de LLMs.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    args = parser.parse_args()

    df = run(args.config)
    summary = df.groupby("model").agg(
        accuracy=("correct", "mean"),
        unparsed=("parsed", lambda s: int((~s).sum())),
        questions=("correct", "size"),
        tokens_per_second=("tokens_per_second", "mean"),
    )
    print(summary.to_string())


if __name__ == "__main__":
    main()
