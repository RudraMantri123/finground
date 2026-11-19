"""Versioned prompt templates loaded from ``prompts/<name>.<version>.toml``.

Prompts live in files rather than code so that a wording change is an explicit,
reviewable new *version* instead of a silent edit: the answer and judge prompts
are part of what the benchmark measures, and part of the LLM cache key, so
every result row should be attributable to an exact prompt version.

TOML (stdlib ``tomllib``) keeps this dependency-free, and its literal
multi-line strings make the stored text byte-identical to what is sent.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache

from .config import CONFIG


@dataclass(frozen=True)
class PromptTemplate:
    """A system prompt plus a ``str.format`` user template, with its version."""

    name: str
    version: str
    system: str
    user: str

    @property
    def id(self) -> str:
        """Stable identifier recorded alongside results, e.g. ``"answer.v1"``."""
        return f"{self.name}.{self.version}"


@cache
def load_prompt(name: str, version: str) -> PromptTemplate:
    """Load ``prompts/<name>.<version>.toml``.

    The file's own ``name``/``version`` keys must match its filename, so a file
    copied to start a new version cannot accidentally report the old id.
    """
    path = CONFIG.paths.prompts / f"{name}.{version}.toml"
    if not path.exists():
        available = sorted(p.name for p in CONFIG.paths.prompts.glob(f"{name}.*.toml"))
        raise FileNotFoundError(f"No prompt {path.name}; available: {available}")
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    if data.get("name") != name or data.get("version") != version:
        raise ValueError(
            f"{path.name} declares name={data.get('name')!r} version={data.get('version')!r}; "
            f"expected {name!r} / {version!r}"
        )
    return PromptTemplate(name=name, version=version, system=data["system"], user=data["user"])


def answer_prompt(version: str | None = None) -> PromptTemplate:
    """The active answering prompt (``FINGROUND_ANSWER_PROMPT_VERSION``, default v1)."""
    return load_prompt("answer", version or CONFIG.prompts.answer_version)


def judge_prompt(version: str | None = None) -> PromptTemplate:
    """The active judge prompt (``FINGROUND_JUDGE_PROMPT_VERSION``, default v1)."""
    return load_prompt("judge", version or CONFIG.prompts.judge_version)
