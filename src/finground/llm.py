"""Provider-agnostic LLM client.

Swapping models is a config change, not a code change: models are named
``provider:model`` (e.g. ``openai:gpt-4o-mini``, ``anthropic:claude-sonnet-5``,
``cohere:command-a-03-2025``, ``mistral:mistral-small-latest``,
``groq:llama-3.3-70b-versatile``, ``ollama:llama3.1``). Only the first colon
separates provider from model, so model ids may themselves contain ``/`` or
``:`` (``openrouter:meta-llama/llama-3.3-70b-instruct:free``). Keys are read
from the environment; a provider with no key is simply reported as unavailable
so the benchmark can skip it.

Responses are cached on disk keyed by (provider, model, system, user, temp) so
re-running the benchmark does not re-bill the API.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests

from . import tracing
from .config import CONFIG

# Approximate published list prices in USD per 1M tokens (input, output), used
# only to estimate cost_per_100q in the benchmark. These change over time —
# edit here; they never affect correctness/faithfulness metrics.
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5": (15.00, 75.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "command-a-03-2025": (2.50, 10.00),
    "command-r-08-2024": (0.15, 0.60),
    "command-r7b-12-2024": (0.0375, 0.15),
    # local models cost nothing per token
    # Models served via the OpenAI-compatible providers below (mistral, gemini,
    # groq, ...) are deliberately unpriced until a verified list price is added:
    # cost is then reported as unknown rather than guessed.
}

# Hosted providers that speak the OpenAI chat-completions wire format and differ
# only in endpoint and key variable. Adding one is a single line here.
OPENAI_COMPATIBLE: dict[str, tuple[str, str]] = {
    # provider: (chat completions URL, API key env var)
    "mistral": ("https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY"),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "GEMINI_API_KEY",
    ),
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "cerebras": ("https://api.cerebras.ai/v1/chat/completions", "CEREBRAS_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "github": ("https://models.github.ai/inference/chat/completions", "GITHUB_TOKEN"),
}

# Keyed REST providers: provider -> env var holding its key.
_KEY_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "cohere": "COHERE_API_KEY",
    **{name: env for name, (_url, env) in OPENAI_COMPATIBLE.items()},
}

# Hosted-request robustness knobs (shared by every requests-based adapter).
HTTP_TIMEOUT_S = 300
HTTP_ATTEMPTS = 6
_RETRY_STATUS = {429, 500, 502, 503, 504}


class LLMUnavailable(RuntimeError):
    """Raised when the requested provider has no credentials / is unreachable."""


@dataclass
class LLMResponse:
    text: str
    model: str  # full provider:model spec
    prompt_tokens: int
    completion_tokens: int
    latency_s: float
    cached: bool = False

    @property
    def cost_usd(self) -> float | None:
        return estimate_cost(self.model, self.prompt_tokens, self.completion_tokens)


def parse_model(spec: str) -> tuple[str, str]:
    """Split ``provider:model`` into ``(provider, model)``."""
    if ":" not in spec:
        raise ValueError(f"Model spec must be 'provider:model', got {spec!r}")
    provider, model = spec.split(":", 1)
    return provider.lower(), model


def estimate_cost(spec: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """USD cost estimate from token usage, or None if price is unknown."""
    _provider, model = parse_model(spec)
    price = PRICING.get(model)
    if price is None:
        return None
    in_price, out_price = price
    return (prompt_tokens * in_price + completion_tokens * out_price) / 1_000_000


def available_providers() -> set[str]:
    """Providers usable right now (key present, or Ollama reachable)."""
    available = {provider for provider, env in _KEY_ENV.items() if os.environ.get(env)}
    try:
        requests.get(f"{CONFIG.ollama_base_url}/api/tags", timeout=1.5)
        available.add("ollama")
    except Exception:  # noqa: BLE001 — unreachable Ollama is just "unavailable"
        pass
    return available


# ---------------------------------------------------------------------------
# Disk cache
# ---------------------------------------------------------------------------


def _cache_key(
    provider: str, model: str, system: str, user: str, temperature: float, extra: str = ""
) -> str:
    """Cache key over everything that can change the generation.

    ``extra`` carries provider-specific generation options (e.g. Ollama's
    num_ctx) so changing them invalidates stale cached responses.
    """
    blob = json.dumps(
        {"p": provider, "m": model, "s": system, "u": user, "t": temperature, "x": extra},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def ollama_num_ctx() -> int:
    """Context window for Ollama requests.

    Ollama defaults to a small num_ctx (2048 in many builds), which silently
    truncates the front of long RAG prompts — the system rules and question get
    cut off while the excerpts survive. Always set it explicitly.
    """
    return int(os.environ.get("OLLAMA_NUM_CTX", "8192"))


def _cache_path(key: str):
    CONFIG.paths.ensure()
    return CONFIG.paths.llm_cache / f"{key}.json"


# ---------------------------------------------------------------------------
# Shared HTTP for hosted providers
# ---------------------------------------------------------------------------


def _retry_after(resp: Any, attempt: int) -> float:
    """Seconds to wait: the server's Retry-After (seconds form) or linear backoff."""
    try:
        wait = float(resp.headers.get("Retry-After", 0))
    except (TypeError, ValueError):  # HTTP-date form or junk -> our own backoff
        wait = 0.0
    return min(wait, 120.0) if wait > 0 else 15.0 * attempt


def _scrub(text: str, key: str) -> str:
    """Remove the API key from text bound for logs or exception messages."""
    return text.replace(key, "***") if key else text


def _post_json(provider: str, url: str, key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST with Bearer auth, timeouts, and backoff on 429/5xx/network errors.

    The key goes only in the Authorization header; it never appears in printed
    messages or raised exceptions (error bodies are scrubbed, and exceptions
    are raised ``from None`` so the request object is not chained along).
    """
    last = "no response"
    for attempt in range(1, HTTP_ATTEMPTS + 1):
        try:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
                timeout=HTTP_TIMEOUT_S,
            )
        except requests.RequestException as exc:
            last = exc.__class__.__name__
            if attempt < HTTP_ATTEMPTS:
                wait = 15.0 * attempt
                print(
                    f"[llm] {provider} request failed ({last}, attempt "
                    f"{attempt}/{HTTP_ATTEMPTS}); retrying in {wait:.0f}s"
                )
                time.sleep(wait)
                continue
            break
        status = resp.status_code
        if status in _RETRY_STATUS:
            last = f"HTTP {status}"
            if attempt < HTTP_ATTEMPTS:
                wait = _retry_after(resp, attempt)
                print(
                    f"[llm] {provider} returned {status} (attempt "
                    f"{attempt}/{HTTP_ATTEMPTS}); retrying in {wait:.0f}s"
                )
                time.sleep(wait)
                continue
            break
        if status >= 400:
            body = _scrub(str(getattr(resp, "text", "") or "")[:300], key)
            msg = f"{provider} request failed: HTTP {status}: {body}".rstrip(": ")
            if status in (401, 403):
                raise LLMUnavailable(msg) from None
            raise RuntimeError(msg) from None
        try:
            return resp.json()
        except ValueError:
            raise RuntimeError(f"{provider} returned non-JSON response") from None
    raise LLMUnavailable(f"{provider} unavailable after {HTTP_ATTEMPTS} attempts ({last})")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LLMClient:
    """A thin wrapper exposing ``complete(system, user) -> LLMResponse``."""

    def __init__(self, model_spec: str, *, temperature: float = 0.0, use_cache: bool = True):
        self.model_spec = model_spec
        self.provider, self.model = parse_model(model_spec)
        self.temperature = temperature
        self.use_cache = use_cache

    # -- public API ---------------------------------------------------------

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResponse:
        extra = f"num_ctx={ollama_num_ctx()}" if self.provider == "ollama" else ""
        t0 = tracing.now()
        if self.use_cache:
            key = _cache_key(self.provider, self.model, system, user, self.temperature, extra)
            path = _cache_path(key)
            if path.exists():
                data = json.loads(path.read_text())
                cached = LLMResponse(
                    text=data["text"],
                    model=self.model_spec,
                    prompt_tokens=data.get("prompt_tokens", 0),
                    completion_tokens=data.get("completion_tokens", 0),
                    latency_s=data.get("latency_s", 0.0),
                    cached=True,
                )
                self._trace(t0, system, user, cached)
                return cached

        start = time.perf_counter()
        try:
            text, in_tok, out_tok = self._dispatch(system, user, max_tokens)
        except Exception as exc:
            if tracing.active():
                err: dict[str, Any] = {
                    "model": self.model_spec,
                    "error": type(exc).__name__,
                    "error_message": str(exc)[:500],
                    "prompt_hash": tracing.prompt_hash(system, user),
                }
                if tracing.capture_prompts():
                    err["prompt_system"] = system
                    err["prompt_user"] = user
                tracing.record_span("generate", t0, **err)
            raise
        latency = time.perf_counter() - start
        resp = LLMResponse(
            text=text,
            model=self.model_spec,
            prompt_tokens=in_tok,
            completion_tokens=out_tok,
            latency_s=latency,
        )
        if self.use_cache:
            _cache_path(key).write_text(
                json.dumps(
                    {
                        "text": text,
                        "prompt_tokens": in_tok,
                        "completion_tokens": out_tok,
                        "latency_s": latency,
                    }
                )
            )
        self._trace(t0, system, user, resp)
        return resp

    def _trace(self, t0: float, system: str, user: str, resp: LLMResponse) -> None:
        """Record the generation span (hash, tokens, cost, cache hit) if traced.

        ``llm_latency_s`` is the provider latency as originally measured — on a
        cache hit that is the cached call's latency, while the span duration is
        the (near-zero) time actually spent now.
        """
        if not tracing.active():
            return
        attrs: dict[str, Any] = {
            "model": self.model_spec,
            "prompt_hash": tracing.prompt_hash(system, user),
            "cache_hit": resp.cached,
            "prompt_tokens": resp.prompt_tokens,
            "completion_tokens": resp.completion_tokens,
            "cost_usd": resp.cost_usd,
            "llm_latency_s": resp.latency_s,
            "temperature": self.temperature,
        }
        if tracing.capture_prompts():  # kept in JSONL only with FINGROUND_TRACE_PROMPTS=1
            attrs["prompt_system"] = system
            attrs["prompt_user"] = user
            attrs["response_text"] = resp.text
        tracing.record_span("generate", t0, **attrs)

    # -- provider dispatch --------------------------------------------------

    def _dispatch(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        if self.provider == "openai":
            return self._openai(system, user, max_tokens)
        if self.provider == "anthropic":
            return self._anthropic(system, user, max_tokens)
        if self.provider == "ollama":
            return self._ollama(system, user, max_tokens)
        if self.provider == "cohere":
            return self._cohere(system, user, max_tokens)
        if self.provider in OPENAI_COMPATIBLE:
            return self._openai_compatible(system, user, max_tokens)
        raise LLMUnavailable(f"Unknown provider {self.provider!r}")

    def _openai(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMUnavailable("OPENAI_API_KEY not set")
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        return text, getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0)

    def _anthropic(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMUnavailable("ANTHROPIC_API_KEY not set")
        from anthropic import Anthropic

        client = Anthropic()
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        usage = resp.usage
        return text, getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0)

    def _cohere(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        key = os.environ.get("COHERE_API_KEY")
        if not key:
            raise LLMUnavailable("COHERE_API_KEY not set")
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # Trial keys are rate-limited per minute; _post_json backs off on 429
        # instead of failing the item. Answers are disk-cached, so a stopped
        # run resumes.
        data = _post_json("cohere", "https://api.cohere.com/v2/chat", key, payload)
        text = "".join(
            part.get("text", "")
            for part in data.get("message", {}).get("content", [])
            if part.get("type") == "text"
        )
        tokens = data.get("usage", {}).get("tokens", {})
        return text, tokens.get("input_tokens", 0), tokens.get("output_tokens", 0)

    def _openai_compatible(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        """Any provider in OPENAI_COMPATIBLE (mistral, gemini, groq, ...)."""
        url, env = OPENAI_COMPATIBLE[self.provider]
        key = os.environ.get(env)
        if not key:
            raise LLMUnavailable(f"{env} not set")
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = _post_json(self.provider, url, key, payload)
        choices = data.get("choices") or [{}]
        content = (choices[0].get("message") or {}).get("content") or ""
        if isinstance(content, list):  # some providers return content parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        usage = data.get("usage") or {}
        return content, usage.get("prompt_tokens") or 0, usage.get("completion_tokens") or 0

    def _ollama(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        url = f"{CONFIG.ollama_base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": max_tokens,
                # Explicit context window — see ollama_num_ctx().
                "num_ctx": ollama_num_ctx(),
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # The local daemon can crash and auto-restart under memory pressure
        # (observed when two ~5GB models swap as answerer/judge). Retry with
        # backoff so a restart delays the benchmark instead of failing items.
        attempts = 4
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                resp = requests.post(url, json=payload, timeout=900)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("message", {}).get("content", "")
                return text, data.get("prompt_eval_count", 0), data.get("eval_count", 0)
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < attempts:
                    wait = 15 * attempt  # 15s, 30s, 45s — time for a daemon relaunch
                    print(
                        f"[llm] ollama request failed (attempt {attempt}/{attempts}): "
                        f"{exc.__class__.__name__}; retrying in {wait}s"
                    )
                    time.sleep(wait)
        raise LLMUnavailable(f"Ollama unreachable at {url}: {last_exc}") from last_exc
