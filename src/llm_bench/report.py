"""Genera tablas, gráficas y un resumen en Markdown a partir de un CSV de resultados.

Uso desde la raíz del repositorio:

    python -m llm_bench.report --results reports/results_60preguntas.csv

Escribe `reports/summary_<nombre>.md` y las figuras en `<figures_dir>/<nombre>/`,
donde `<nombre>` es el nombre del CSV sin extensión y `figures_dir` sale de la
configuración.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import PercentFormatter

plt.switch_backend("Agg")  # sin ventana: solo se guardan ficheros

LETTERS = "ABCDEFGH"
DIFFICULTY_ORDER = ["facil", "media", "dificil"]

# Paleta categórica validada para daltonismo (los tres primeros colores son
# distinguibles entre sí en cualquier combinación). El color sigue al modelo,
# no a su posición en el ranking.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
SEQUENTIAL_BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE = "#fcfcfb"
TEXT = "#2b2b29"
MUTED = "#6b6a63"
GRID = "#e4e3de"


def load_results(path: Path) -> pd.DataFrame:
    """Lee un CSV de resultados y normaliza las columnas que pueden faltar.

    Los CSV anteriores al barajado no tienen `choice_order`; en ese caso se
    supone que las opciones se mostraron en su orden original.
    """
    df = pd.read_csv(path)
    df["prediction"] = df["prediction"].fillna("").astype(str)
    if "choice_order" not in df.columns:
        df["choice_order"] = ""
    df["choice_order"] = df["choice_order"].fillna("").astype(str)
    return df


def bootstrap_ci(
    values: np.ndarray, n_samples: int, seed: int, level: float = 0.95
) -> tuple[float, float]:
    """Intervalo de confianza de la media por bootstrap de percentiles.

    Se remuestrean los valores con reemplazo `n_samples` veces y se toman los
    percentiles de las medias obtenidas.
    """
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_samples, len(values)))
    means = values[idx].mean(axis=1)
    tail = (1 - level) / 2 * 100
    return float(np.percentile(means, tail)), float(np.percentile(means, 100 - tail))


def accuracy_table(df: pd.DataFrame, n_samples: int, seed: int) -> pd.DataFrame:
    """Acierto por modelo con su intervalo de confianza al 95 %.

    El bootstrap remuestrea preguntas, no filas: las repeticiones de una misma
    pregunta no son independientes y tratarlas como tales estrecharía el
    intervalo de forma engañosa.
    """
    rows = []
    for model, group in df.groupby("model"):
        per_question = group.groupby("question_id")["correct"].mean().to_numpy(dtype=float)
        low, high = bootstrap_ci(per_question, n_samples, seed)
        rows.append(
            {
                "model": model,
                "accuracy": float(group["correct"].mean()),
                "ci_low": low,
                "ci_high": high,
                "questions": int(group["question_id"].nunique()),
                "repetitions": int(group["repetition"].nunique()),
                "unparsed": int((~group["parsed"].astype(bool)).sum()),
            }
        )
    return pd.DataFrame(rows).set_index("model").sort_values("accuracy", ascending=False)


def breakdown(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Acierto medio de cada modelo agrupado por `by` (por ejemplo, `topic`)."""
    return df.pivot_table(index=by, columns="model", values="correct", aggfunc="mean")


def position_bias(df: pd.DataFrame) -> pd.DataFrame:
    """Proporción de veces que cada modelo elige cada letra, junto a la de las correctas.

    Si un modelo elige una letra mucho más a menudo de lo que esa letra es la
    correcta, tiene preferencia por esa posición.
    """
    answered = df[df["prediction"] != ""]
    shares = pd.crosstab(answered["model"], answered["prediction"], normalize="index")
    one_model = df[df["model"] == df["model"].iloc[0]]
    shares.loc["(correctas)"] = one_model["gold"].value_counts(normalize=True)
    return shares.fillna(0.0).reindex(columns=sorted(shares.columns))


def original_choice(prediction: str, choice_order: str) -> str:
    """Traduce la letra elegida a la letra que esa opción tenía sin barajar."""
    if not prediction:
        return ""
    if not choice_order:
        return prediction
    order = [int(i) for i in choice_order.split(",")]
    return LETTERS[order[LETTERS.index(prediction)]]


def consistency(df: pd.DataFrame) -> pd.Series:
    """Proporción de preguntas en las que el modelo elige la misma opción en todas las repeticiones.

    Se compara el contenido de la opción, no la letra, porque con el barajado
    la misma opción puede aparecer en letras distintas.
    """
    chosen = [
        original_choice(p, o) for p, o in zip(df["prediction"], df["choice_order"], strict=True)
    ]
    same = df.assign(chosen=chosen).groupby(["model", "question_id"])["chosen"].nunique() == 1
    return same.groupby("model").mean()


def hardest_questions(df: pd.DataFrame, threshold: float = 0.5) -> pd.Series:
    """Preguntas cuyo acierto medio entre todos los modelos queda por debajo de `threshold`."""
    per_question = df.groupby("question_id")["correct"].mean().sort_values()
    return per_question[per_question < threshold]


# --- Gráficas ---------------------------------------------------------------


def _style(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelcolor=TEXT)


def plot_accuracy(table: pd.DataFrame, path: Path) -> None:
    """Barras horizontales de acierto con el intervalo de confianza."""
    table = table.sort_values("accuracy")
    fig, ax = plt.subplots(figsize=(7, 0.7 * len(table) + 1.4), facecolor=SURFACE)
    _style(ax)
    y = np.arange(len(table))
    errors = [table["accuracy"] - table["ci_low"], table["ci_high"] - table["accuracy"]]
    ax.barh(y, table["accuracy"], height=0.5, color=SERIES_COLORS[0])
    ax.errorbar(table["accuracy"], y, xerr=errors, fmt="none", ecolor=TEXT, capsize=4, lw=1.2)
    for yi, (acc, high) in enumerate(zip(table["accuracy"], table["ci_high"], strict=True)):
        ax.text(high + 0.02, yi, f"{acc:.0%}", va="center", color=TEXT, fontsize=10)
    ax.set_yticks(y, table.index)
    ax.set_xlim(0, 1.1)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Acierto por modelo (IC 95 % por bootstrap)", color=TEXT, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_heatmap(matrix: pd.DataFrame, title: str, path: Path) -> None:
    """Mapa de calor de acierto (filas: categorías; columnas: modelos)."""
    cmap = LinearSegmentedColormap.from_list("blues", SEQUENTIAL_BLUES)
    fig, ax = plt.subplots(
        figsize=(1.8 * len(matrix.columns) + 2, 0.5 * len(matrix) + 1.5), facecolor=SURFACE
    )
    ax.imshow(matrix.to_numpy(dtype=float), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for (i, j), value in np.ndenumerate(matrix.to_numpy(dtype=float)):
        ax.text(
            j,
            i,
            f"{value:.0%}",
            ha="center",
            va="center",
            fontsize=10,
            # A partir del azul medio, el texto oscuro pierde contraste.
            color="white" if value >= 0.45 else TEXT,
        )
    ax.set_xticks(range(len(matrix.columns)), matrix.columns)
    ax.set_yticks(range(len(matrix.index)), matrix.index)
    ax.tick_params(length=0, labelcolor=TEXT)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, color=TEXT, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_position_bias(shares: pd.DataFrame, path: Path) -> None:
    """Barras agrupadas: qué proporción de respuestas va a cada letra, por modelo."""
    models = [m for m in shares.index if m != "(correctas)"]
    letters = list(shares.columns)
    fig, ax = plt.subplots(figsize=(8, 4), facecolor=SURFACE)
    _style(ax)
    width = 0.8 / len(models)
    x = np.arange(len(letters))
    for k, model in enumerate(models):
        ax.bar(
            x + (k - (len(models) - 1) / 2) * width,
            shares.loc[model],
            width=width * 0.9,
            color=SERIES_COLORS[k % len(SERIES_COLORS)],
            label=model,
        )
    # Referencia: con qué frecuencia cada letra es la correcta (una línea por grupo).
    ax.hlines(
        shares.loc["(correctas)"],
        x - 0.45,
        x + 0.45,
        color=TEXT,
        linewidth=2,
        label="Proporción de correctas",
        zorder=3,
    )
    ax.set_xticks(x, letters)
    ax.set_ylim(0, float(shares.to_numpy().max()) * 1.35)  # hueco para la leyenda
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, labelcolor=TEXT, ncols=len(models) + 1, loc="upper left")
    ax.set_title("Letra elegida por cada modelo", color=TEXT, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- Resumen en Markdown -----------------------------------------------------


def to_markdown(df: pd.DataFrame, percent: bool = True) -> str:
    """Convierte una tabla en Markdown sin depender de librerías externas."""

    def fmt(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.0%}" if percent else f"{value:.2f}"
        return str(value)

    header = [str(df.index.name or "")] + [str(c) for c in df.columns]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for index, row in df.iterrows():
        lines.append("| " + " | ".join([str(index)] + [fmt(v) for v in row]) + " |")
    return "\n".join(lines)


def write_summary(
    df: pd.DataFrame,
    results_path: Path,
    summary_path: Path,
    figures: dict[str, Path],
    n_samples: int,
    seed: int,
) -> None:
    """Escribe el resumen en Markdown con todas las tablas y enlaces a las figuras."""
    acc = accuracy_table(df, n_samples, seed)
    shown = acc.assign(
        ic_95=[f"{lo:.0%} - {hi:.0%}" for lo, hi in zip(acc["ci_low"], acc["ci_high"], strict=True)]
    )[["accuracy", "ic_95", "questions", "repetitions", "unparsed"]]
    shown.columns = ["acierto", "IC 95 %", "preguntas", "repeticiones", "no interpretables"]
    shown.index.name = "modelo"

    cons = consistency(df).to_frame("misma opción en todas las repeticiones")
    cons.index.name = "modelo"
    hard = hardest_questions(df).to_frame("acierto medio")
    hard.index.name = "pregunta"
    by_topic = breakdown(df, "topic").rename_axis(index="tema", columns=None)
    by_difficulty = (
        breakdown(df, "difficulty")
        .reindex(DIFFICULTY_ORDER)
        .dropna(how="all")
        .rename_axis(index="dificultad", columns=None)
    )
    bias = position_bias(df).rename_axis(index="modelo", columns=None)

    def link(name: str) -> str:
        return Path(os.path.relpath(figures[name], summary_path.parent)).as_posix()

    sections = [
        f"# Resumen de `{results_path.as_posix()}`",
        "Generado con `python -m llm_bench.report`. No edites este fichero a mano.",
        (
            f"Preguntas: {df['question_id'].nunique()} · Modelos: {df['model'].nunique()} · "
            f"Repeticiones: {df['repetition'].nunique()} · Remuestreos bootstrap: {n_samples}"
        ),
        "## Acierto por modelo",
        to_markdown(shown),
        f"![Acierto por modelo]({link('accuracy')})",
        "## Acierto por tema",
        to_markdown(by_topic),
        f"![Acierto por tema]({link('topic')})",
        "## Acierto por dificultad",
        to_markdown(by_difficulty),
        f"![Acierto por dificultad]({link('difficulty')})",
        "## Sesgo de posición",
        (
            "Proporción de respuestas que van a cada letra. La fila `(correctas)` indica "
            "con qué frecuencia cada letra es la correcta."
        ),
        to_markdown(bias),
        f"![Letra elegida]({link('position')})",
        "## Consistencia entre repeticiones",
        to_markdown(cons),
        "## Preguntas más falladas",
        (
            "Acierto medio de todos los modelos por debajo del 50 %. Conviene revisar "
            "que la clave y el enunciado sean correctos."
        ),
        to_markdown(hard) if len(hard) else "_Ninguna._",
    ]
    summary_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")


def report(results_path: Path, config_path: Path) -> Path:
    """Genera figuras y resumen para un CSV de resultados. Devuelve la ruta del resumen."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    n_samples = int(config["experiment"]["bootstrap_samples"])
    seed = int(config["experiment"]["seed"])
    figures_dir = Path(config["output"]["figures_dir"]) / results_path.stem
    figures_dir.mkdir(parents=True, exist_ok=True)

    df = load_results(results_path)
    figures = {
        "accuracy": figures_dir / "accuracy.png",
        "topic": figures_dir / "accuracy_by_topic.png",
        "difficulty": figures_dir / "accuracy_by_difficulty.png",
        "position": figures_dir / "position_bias.png",
    }
    plot_accuracy(accuracy_table(df, n_samples, seed), figures["accuracy"])
    plot_heatmap(breakdown(df, "topic"), "Acierto por tema", figures["topic"])
    difficulty = breakdown(df, "difficulty").reindex(DIFFICULTY_ORDER).dropna(how="all")
    plot_heatmap(difficulty, "Acierto por dificultad", figures["difficulty"])
    plot_position_bias(position_bias(df), figures["position"])

    summary_path = Path("reports") / f"summary_{results_path.stem}.md"
    write_summary(df, results_path, summary_path, figures, n_samples, seed)
    return summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el informe de un CSV de resultados.")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    args = parser.parse_args()
    summary = report(args.results, args.config)
    print(f"Resumen escrito en {summary}")


if __name__ == "__main__":
    main()
