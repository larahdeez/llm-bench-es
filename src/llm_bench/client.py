"""Cliente mínimo para la API local de Ollama."""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class Generation:
    """Respuesta de un modelo junto con sus métricas de rendimiento."""

    text: str
    total_seconds: float
    eval_count: int
    eval_seconds: float


def chat(
    *,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    context_length: int,
    seed: int,
    think: bool | None = None,
    timeout: float = 300.0,
) -> Generation:
    """Envía un prompt a Ollama y devuelve la respuesta completa.

    `think` solo se envía si se indica, porque no todos los modelos
    soportan el modo de pensamiento.
    """
    payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": context_length,
            "seed": seed,
        },
    }
    if think is not None:
        payload["think"] = think

    start = time.perf_counter()
    response = requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    elapsed = time.perf_counter() - start

    return Generation(
        text=data["message"]["content"],
        total_seconds=elapsed,
        eval_count=int(data.get("eval_count", 0)),
        eval_seconds=float(data.get("eval_duration", 0)) / 1e9,
    )
