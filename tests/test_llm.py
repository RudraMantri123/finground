"""Provider adapters, exercised against mocked HTTP (no keys, no network)."""

from __future__ import annotations

import traceback

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


# ---------------------------------------------------------------------------
# OpenAI-compatible providers (mistral, gemini, groq, cerebras, openrouter, github)
# ---------------------------------------------------------------------------

CHAT_OK = {
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Margin fell [C2]."}}],
    "usage": {"prompt_tokens": 210, "completion_tokens": 9, "total_tokens": 219},
}


def _capture_post(monkeypatch, response):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return response

    monkeypatch.setattr(llm.requests, "post", fake_post)
    return calls


def test_mistral_parses_text_and_usage(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-test-key")
    calls = _capture_post(monkeypatch, _FakeResponse(200, CHAT_OK))

    resp = llm.LLMClient("mistral:mistral-small-latest", use_cache=False).complete("sys", "q")

    assert resp.text == "Margin fell [C2]."
    assert (resp.prompt_tokens, resp.completion_tokens) == (210, 9)
    call = calls[0]
    assert call["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer mistral-test-key"
    assert call["json"]["model"] == "mistral-small-latest"
    assert call["json"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "q"},
    ]
    assert call["timeout"] and call["timeout"] > 0
    assert resp.cost_usd is None  # unpriced -> unknown, never guessed


def test_gemini_uses_openai_compatible_endpoint(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    calls = _capture_post(monkeypatch, _FakeResponse(200, CHAT_OK))

    resp = llm.LLMClient("gemini:gemini-2.5-flash", use_cache=False).complete("sys", "q")

    assert resp.text == "Margin fell [C2]."
    assert calls[0]["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )
    assert calls[0]["headers"]["Authorization"] == "Bearer gemini-test-key"
    assert calls[0]["json"]["model"] == "gemini-2.5-flash"


def test_openrouter_model_id_with_slash_and_colon(monkeypatch):
    spec = "openrouter:meta-llama/llama-3.3-70b-instruct:free"
    assert llm.parse_model(spec) == ("openrouter", "meta-llama/llama-3.3-70b-instruct:free")

    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    calls = _capture_post(monkeypatch, _FakeResponse(200, CHAT_OK))
    resp = llm.LLMClient(spec, use_cache=False).complete("sys", "q")

    assert resp.text == "Margin fell [C2]."
    assert resp.model == spec
    assert calls[0]["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls[0]["json"]["model"] == "meta-llama/llama-3.3-70b-instruct:free"
    # The ":free" suffix is part of the model, so it must change the cache key.
    k_free = llm._cache_key("openrouter", "meta-llama/llama-3.3-70b-instruct:free", "s", "u", 0.0)
    k_paid = llm._cache_key("openrouter", "meta-llama/llama-3.3-70b-instruct", "s", "u", 0.0)
    assert k_free != k_paid


def test_openai_compatible_retries_on_429_and_5xx(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    waits = []
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    responses = iter(
        [
            _FakeResponse(429, headers={"Retry-After": "3"}),
            _FakeResponse(503),
            _FakeResponse(200, CHAT_OK),
        ]
    )
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: next(responses))

    resp = llm.LLMClient("groq:llama-3.3-70b-versatile", use_cache=False).complete("sys", "q")

    assert resp.text == "Margin fell [C2]."
    assert waits[0] == 3  # Retry-After honoured
    assert len(waits) == 2


def test_openai_compatible_gives_up_after_retries(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "cb-test-key")
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResponse(429))

    with pytest.raises(llm.LLMUnavailable, match="cerebras"):
        llm.LLMClient("cerebras:llama-3.3-70b", use_cache=False).complete("sys", "q")


@pytest.mark.parametrize(
    "provider", ["mistral", "gemini", "groq", "cerebras", "openrouter", "github"]
)
def test_openai_compatible_without_key_is_unavailable(monkeypatch, provider):
    _url, env = llm.OPENAI_COMPATIBLE[provider]
    monkeypatch.delenv(env, raising=False)

    def no_network(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("request sent without a key")

    monkeypatch.setattr(llm.requests, "post", no_network)
    assert provider not in llm.available_providers()
    with pytest.raises(llm.LLMUnavailable, match=env):
        llm.LLMClient(f"{provider}:some-model", use_cache=False).complete("sys", "q")


def test_available_providers_reports_keyed_compatible_providers(monkeypatch):
    for _url, env in llm.OPENAI_COMPATIBLE.values():
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "gh-test-token")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")

    available = llm.available_providers()
    assert {"github", "openrouter"} <= available
    assert not {"mistral", "gemini", "groq", "cerebras"} & available


@pytest.mark.parametrize("status", [400, 401, 404])
def test_key_is_sent_but_never_in_error_text(monkeypatch, status):
    secret = "sk-super-secret-value-123"
    monkeypatch.setenv("MISTRAL_API_KEY", secret)
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)
    bad = _FakeResponse(status)
    bad.text = f'{{"error": "invalid request for key {secret}"}}'  # server echoes the key
    calls = _capture_post(monkeypatch, bad)

    with pytest.raises(Exception) as excinfo:
        llm.LLMClient("mistral:mistral-large-latest", use_cache=False).complete("sys", "q")

    assert calls[0]["headers"]["Authorization"] == f"Bearer {secret}"
    assert str(status) in str(excinfo.value)
    rendered = "".join(traceback.format_exception(excinfo.type, excinfo.value, excinfo.tb))
    assert secret not in rendered


def test_key_not_in_error_after_network_failures(monkeypatch, capsys):
    secret = "gh-secret-token-xyz"
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)

    def boom(url, headers, json, timeout):
        assert headers["Authorization"] == f"Bearer {secret}"
        raise llm.requests.ConnectionError(f"failed with headers {headers}")

    monkeypatch.setattr(llm.requests, "post", boom)
    with pytest.raises(llm.LLMUnavailable) as excinfo:
        llm.LLMClient("github:openai/gpt-4.1-mini", use_cache=False).complete("sys", "q")

    assert secret not in str(excinfo.value)
    assert secret not in capsys.readouterr().out
