"""Provider adapters, exercised against mocked HTTP (no keys, no network)."""

from __future__ import annotations

import pytest

from finground import llm


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


COHERE_OK = {
    "message": {"role": "assistant", "content": [{"type": "text", "text": "Revenue rose [C1]."}]},
    "usage": {"tokens": {"input_tokens": 120, "output_tokens": 7}},
}


def test_cohere_parses_text_and_usage(monkeypatch):
    monkeypatch.setenv("COHERE_API_KEY", "test-key")
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json))
        return _FakeResponse(200, COHERE_OK)

    monkeypatch.setattr(llm.requests, "post", fake_post)
    resp = llm.LLMClient("cohere:command-r7b-12-2024", use_cache=False).complete("sys", "q")

    assert resp.text == "Revenue rose [C1]."
    assert (resp.prompt_tokens, resp.completion_tokens) == (120, 7)
    url, headers, body = calls[0]
    assert url.endswith("/v2/chat")
    assert headers["Authorization"] == "Bearer test-key"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert resp.cost_usd is not None


def test_cohere_retries_on_rate_limit(monkeypatch):
    monkeypatch.setenv("COHERE_API_KEY", "test-key")
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)
    responses = iter(
        [_FakeResponse(429, headers={"Retry-After": "1"}), _FakeResponse(200, COHERE_OK)]
    )
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: next(responses))

    resp = llm.LLMClient("cohere:command-a-03-2025", use_cache=False).complete("sys", "q")
    assert resp.text == "Revenue rose [C1]."


def test_cohere_without_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    assert "cohere" not in llm.available_providers()
    with pytest.raises(llm.LLMUnavailable):
        llm.LLMClient("cohere:command-a-03-2025", use_cache=False).complete("sys", "q")
