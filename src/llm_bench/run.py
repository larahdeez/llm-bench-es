"""Ejecuta el benchmark de opción múltiple y guarda los resultados en CSV.

Uso desde la raíz del repositorio:

    python -m llm_bench.run --config configs/default.yaml

Cada respuesta se añade al CSV en cuanto llega. Si la ejecución se corta, se
continúa donde se quedó con `--resume`.

Las preguntas de tipo distinto a opción múltiple se omiten por ahora.
"""

from __future__ import annotations

import argparse
import csv
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


COLUMNS = [
    "model",
    "tag",
    "quantization",
    "repetition",
    "question_id",
    "topic",
    "difficulty",
    "choice_order",
    "gold",
    "prediction",
    "parsed",
    "correct",
    "raw_response",
    "total_seconds",
    "eval_count",
    "tokens_per_second",
]


def completed_keys(path: Path) -> set[tuple[str, int, str]]:
    """Devuelve las combinaciones (modelo, repetición, pregunta) que ya están en el CSV."""
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as fh:
        return {(r["model"], int(r["repetition"]), r["question_id"]) for r in csv.DictReader(fh)}


def append_row(path: Path, row: dict[str, Any]) -> None:
    """Añade una fila al CSV, escribiendo la cabecera si el fichero es nuevo.

    Se abre y se cierra el fichero en cada fila para que lo escrito quede en
    disco aunque el programa se corte justo después.
    """
    is_new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def run(config_path: Path, output: Path | None = None, resume: bool = False) -> pd.DataFrame:
    """Evalúa cada modelo sobre cada pregunta y guarda el CSV de resultados.

    Si se indica `output`, el CSV se guarda ahí en lugar de en la ruta de la
    configuración. Con `resume`, se saltan las combinaciones que ya están en el
    CSV; sin él, el CSV no debe existir, para no mezclar ejecuciones por error.
    """
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    exp = config["experiment"]
    inf = config["inference"]
    shuffle = bool(exp.get("shuffle_choices", False))

    if output is None:
        output = Path(config["output"]["results_csv"])
    if output.exists() and not resume:
        raise SystemExit(
            f"{output} ya existe. Usa --resume para continuar esa ejecución "
            "o --output para guardar en otro fichero."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    done = completed_keys(output)

    template = Path(inf["prompt_template"]).read_text(encoding="utf-8")
    questions = [
        q
        for q in load_questions(Path(config["dataset"]["path"]))
        if q["task_type"] == "multiple_choice"
    ]

    total = len(config["models"]) * exp["repetitions"] * len(questions)
    count = len(done)
    if done:
        print(f"Reanudando: {count}/{total} respuestas ya guardadas en {output}", flush=True)
    for model in config["models"]:
        for repetition in range(exp["repetitions"]):
            for question in questions:
                if (model["name"], repetition, question["id"]) in done:
                    continue
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
                    keep_alive=inf.get("keep_alive", "30m"),
                    retries=inf.get("retries", 5),
                )
                prediction = extract_choice(generation.text, len(choices))
                tokens_per_second = (
                    generation.eval_count / generation.eval_seconds
                    if generation.eval_seconds > 0
                    else float("nan")
                )
                append_row(
                    output,
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
                    },
                )
                count += 1
                # flush=True para que la línea aparezca en el momento y no al final.
                print(
                    f"[{count}/{total}] {model['name']} "
                    f"rep {repetition + 1}/{exp['repetitions']} {question['id']}: "
                    f"{prediction or '?'} (correcta {gold}) "
                    f"{'acierto' if prediction == gold else 'fallo'} "
                    f"{generation.total_seconds:.1f} s",
                    flush=True,
                )

    return pd.read_csv(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta el benchmark de LLMs.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument(
        "--output", type=Path, default=None, help="Ruta del CSV (por defecto, la de la config)."
    )
    parser.add_argument(
        "--resume", action="store_true", help="Continúa una ejecución cortada en el mismo CSV."
    )
    args = parser.parse_args()

    df = run(args.config, args.output, args.resume)
    summary = df.groupby("model").agg(
        accuracy=("correct", "mean"),
        unparsed=("parsed", lambda s: int((~s).sum())),
        questions=("correct", "size"),
        tokens_per_second=("tokens_per_second", "mean"),
    )
    print(summary.to_string())


if __name__ == "__main__":
    main()
