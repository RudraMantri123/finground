"""Provider-agnostic LLM client.

Swapping models is a config change, not a code change: models are named
``provider:model`` (e.g. ``openai:gpt-4o-mini``, ``anthropic:claude-sonnet-5``,
``ollama:llama3.1``). Keys are read from the environment; a provider with no key
is simply reported as unavailable so the benchmark can mark it ``N/A``.

Responses are cached on disk keyed by (provider, model, system, user, temp) so
re-running the benchmark does not re-bill the API.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass

import requests

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
    # local models cost nothing per token
}


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
    available: set[str] = set()
    if os.environ.get("OPENAI_API_KEY"):
        available.add("openai")
    if os.environ.get("ANTHROPIC_API_KEY"):
        available.add("anthropic")
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
        if self.use_cache:
            key = _cache_key(self.provider, self.model, system, user, self.temperature, extra)
            path = _cache_path(key)
            if path.exists():
                data = json.loads(path.read_text())
                return LLMResponse(
                    text=data["text"],
                    model=self.model_spec,
                    prompt_tokens=data.get("prompt_tokens", 0),
                    completion_tokens=data.get("completion_tokens", 0),
                    latency_s=data.get("latency_s", 0.0),
                    cached=True,
                )

        start = time.perf_counter()
        text, in_tok, out_tok = self._dispatch(system, user, max_tokens)
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
        return resp

    # -- provider dispatch --------------------------------------------------

    def _dispatch(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        if self.provider == "openai":
            return self._openai(system, user, max_tokens)
        if self.provider == "anthropic":
            return self._anthropic(system, user, max_tokens)
        if self.provider == "ollama":
            return self._ollama(system, user, max_tokens)
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

    def _ollama(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        url = f"{CONFIG.ollama_base_url}/api/chat"
        try:
            resp = requests.post(
                url,
                json={
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
                },
                timeout=900,  # local CPU inference of long answers can be slow
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise LLMUnavailable(f"Ollama unreachable at {url}: {exc}") from exc
        data = resp.json()
        text = data.get("message", {}).get("content", "")
        return text, data.get("prompt_eval_count", 0), data.get("eval_count", 0)
