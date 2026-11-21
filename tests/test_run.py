"""Pruebas del guardado continuo, la reanudación y los reintentos.

No hace falta Ollama: las llamadas HTTP se sustituyen por respuestas falsas.
"""

from pathlib import Path
from typing import Any

import pytest
import requests

from llm_bench import client, run


class FakeResponse:
    def __init__(self, status_code: int, text: str = "A") -> None:
        self.status_code = status_code
        self._text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self) -> dict[str, Any]:
        return {"message": {"content": self._text}, "eval_count": 1, "eval_duration": 1e8}


CHAT_ARGS: dict[str, Any] = {
    "base_url": "http://ollama",
    "model": "m",
    "prompt": "p",
    "temperature": 0.0,
    "max_tokens": 4,
    "context_length": 128,
    "seed": 0,
    "backoff": 0.0,
}


def test_chat_retries_server_errors_and_connection_drops(monkeypatch: pytest.MonkeyPatch) -> None:
    answers: list[Any] = [requests.ConnectionError(), FakeResponse(500), FakeResponse(200, "B")]

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(client.requests, "post", fake_post)
    assert client.chat(**CHAT_ARGS, retries=3).text == "B"
    assert answers == []


def test_chat_gives_up_after_the_last_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client.requests, "post", lambda *a, **k: FakeResponse(500))
    with pytest.raises(RuntimeError, match="2 reintentos"):
        client.chat(**CHAT_ARGS, retries=2)


def test_chat_does_not_retry_client_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        calls.append(1)
        return FakeResponse(404)

    monkeypatch.setattr(client.requests, "post", fake_post)
    with pytest.raises(requests.HTTPError):
        client.chat(**CHAT_ARGS, retries=3)
    assert len(calls) == 1


def write_experiment(tmp_path: Path) -> Path:
    """Crea una config mínima: 1 modelo, 2 repeticiones y 2 preguntas."""
    questions = tmp_path / "questions.jsonl"
    questions.write_text(
        '{"id": "q-0001", "task_type": "multiple_choice", "topic": "t", "difficulty": "facil", '
        '"question": "Pregunta uno", "choices": ["a", "b", "c", "d"], "answer": "A"}\n'
        '{"id": "q-0002", "task_type": "multiple_choice", "topic": "t", "difficulty": "facil", '
        '"question": "Pregunta dos", "choices": ["a", "b", "c", "d"], "answer": "B"}\n',
        encoding="utf-8",
    )
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("{question}\n{options}", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        f"experiment: {{seed: 1, repetitions: 2, shuffle_choices: true}}\n"
        f"dataset: {{path: '{questions.as_posix()}'}}\n"
        f"inference: {{base_url: 'http://ollama', temperature: 0.0, max_tokens: 4, "
        f"context_length: 128, prompt_template: '{prompt.as_posix()}', retries: 0}}\n"
        f"models: [{{name: m1, tag: 'm1:tag'}}]\n"
        f"output: {{results_csv: '{(tmp_path / 'results.csv').as_posix()}'}}\n",
        encoding="utf-8",
    )
    return config


def test_resume_continues_after_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = write_experiment(tmp_path)
    output = tmp_path / "results.csv"
    prompts: list[str] = []

    def crash_on_third_call(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        prompts.append(json["messages"][0]["content"])
        if len(prompts) == 3:
            raise requests.ConnectionError()
        return FakeResponse(200)

    monkeypatch.setattr(client.requests, "post", crash_on_third_call)
    with pytest.raises(RuntimeError):
        run.run(config)
    # Las dos respuestas anteriores al corte ya están en disco.
    assert len(run.completed_keys(output)) == 2

    # Sin --resume no se toca un CSV que ya existe.
    with pytest.raises(SystemExit):
        run.run(config)

    monkeypatch.setattr(client.requests, "post", lambda url, json, timeout: FakeResponse(200))
    df = run.run(config, resume=True)

    assert len(df) == 4
    assert not df.duplicated(["model", "repetition", "question_id"]).any()
    assert "Reanudando: 2/4" in capsys.readouterr().out
