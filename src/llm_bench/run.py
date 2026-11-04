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
from llm_bench.score import extract_choice, format_prompt, shuffle_choices


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Lee un fichero JSON Lines con una pregunta por línea."""
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def run(config_path: Path, output: Path | None = None) -> pd.DataFrame:
    """Evalúa cada modelo sobre cada pregunta y guarda el CSV de resultados.

    Si se indica `output`, el CSV se guarda ahí en lugar de en la ruta de la
    configuración.
    """
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    exp = config["experiment"]
    inf = config["inference"]
    shuffle = bool(exp.get("shuffle_choices", False))

    template = Path(inf["prompt_template"]).read_text(encoding="utf-8")
    questions = [
        q
        for q in load_questions(Path(config["dataset"]["path"]))
        if q["task_type"] == "multiple_choice"
    ]

    total = len(config["models"]) * exp["repetitions"] * len(questions)
    rows: list[dict[str, Any]] = []
    for model in config["models"]:
        for repetition in range(exp["repetitions"]):
            for question in questions:
                choices: list[str] = question["choices"]
                gold: str = question["answer"]
                order = list(range(len(choices)))
                if shuffle:
                    # La clave no depende del modelo: todos ven el mismo orden.
                    key = f"{exp['seed']}-{repetition}-{question['id']}"
                    choices, gold, order = shuffle_choices(choices, gold, key)
                prompt = format_prompt(template, question["question"], choices)
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
                prediction = extract_choice(generation.text, len(choices))
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
                        "choice_order": ",".join(str(i) for i in order),
                        "gold": gold,
                        "prediction": prediction or "",
                        "parsed": prediction is not None,
                        "correct": prediction == gold,
                        "raw_response": generation.text,
                        "total_seconds": generation.total_seconds,
                        "eval_count": generation.eval_count,
                        "tokens_per_second": tokens_per_second,
                    }
                )
                # flush=True para que la línea aparezca en el momento y no al final.
                print(
                    f"[{len(rows)}/{total}] {model['name']} "
                    f"rep {repetition + 1}/{exp['repetitions']} {question['id']}: "
                    f"{prediction or '?'} (correcta {gold}) "
                    f"{'acierto' if prediction == gold else 'fallo'} "
                    f"{generation.total_seconds:.1f} s",
                    flush=True,
                )

    df = pd.DataFrame(rows)
    if output is None:
        output = Path(config["output"]["results_csv"])
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta el benchmark de LLMs.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument(
        "--output", type=Path, default=None, help="Ruta del CSV (por defecto, la de la config)."
    )
    args = parser.parse_args()

    df = run(args.config, args.output)
    summary = df.groupby("model").agg(
        accuracy=("correct", "mean"),
        unparsed=("parsed", lambda s: int((~s).sum())),
        questions=("correct", "size"),
        tokens_per_second=("tokens_per_second", "mean"),
    )
    print(summary.to_string())


if __name__ == "__main__":
    main()
