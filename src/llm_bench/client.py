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
    keep_alive: str = "30m",
    timeout: float = 300.0,
    retries: int = 5,
    backoff: float = 5.0,
) -> Generation:
    """Envía un prompt a Ollama y devuelve la respuesta completa.

    `think` solo se envía si se indica, porque no todos los modelos
    soportan el modo de pensamiento. `keep_alive` indica cuánto tiempo mantiene
    Ollama el modelo en memoria tras la petición, para no recargarlo entre preguntas.

    Si Ollama no responde, tarda más de `timeout` segundos o devuelve un error
    del servidor (5xx), se reintenta hasta `retries` veces esperando `backoff`,
    `2 * backoff`, `4 * backoff`... segundos entre intentos.
    """
    payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": keep_alive,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": context_length,
            "seed": seed,
        },
    }
    if think is not None:
        payload["think"] = think

    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            response = requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
            if response.status_code < 500:
                break
            error = f"error {response.status_code} del servidor"
        except (requests.ConnectionError, requests.Timeout) as exc:
            error = type(exc).__name__
        if attempt == retries:
            raise RuntimeError(f"Ollama sigue fallando tras {retries} reintentos ({error})")
        wait = backoff * 2**attempt
        print(f"  {error}; reintento {attempt + 1}/{retries} en {wait:.0f} s", flush=True)
        time.sleep(wait)

    # Los errores 4xx (modelo inexistente, petición mal formada) no se reintentan.
    response.raise_for_status()
    data = response.json()
    elapsed = time.perf_counter() - start

    return Generation(
        text=data["message"]["content"],
        total_seconds=elapsed,
        eval_count=int(data.get("eval_count", 0)),
        eval_seconds=float(data.get("eval_duration", 0)) / 1e9,
    )
