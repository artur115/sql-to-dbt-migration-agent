"""A small Claude client with record / replay, so evals are reproducible.

Modes
  live    call the API, keep nothing
  record  call the API and save each response under recordings/
  replay  never call the API; serve saved responses (what CI uses, no key needed)

A recording is keyed by a hash of everything that shapes the answer: model,
effort, system prompt, messages and output schema. Change any of them and the
old recording no longer applies, so replay can't quietly serve a stale answer.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = os.environ.get("MIGRATOR_MODEL", "claude-opus-5-5")
DEFAULT_EFFORT = os.environ.get("MIGRATOR_EFFORT", "high")
# USD per million tokens, from Anthropic's published price list (Nov 2026).
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00),
          "claude-haiku-5-5": (0.10, 0.50)}


class MissingRecording(Exception):
    pass


class ModelRefused(Exception):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    calls: int = 0

    def add(self, other: dict) -> None:
        self.input_tokens += other.get("input_tokens", 0)
        self.output_tokens += other.get("output_tokens", 0)
        self.cache_read_input_tokens += other.get("cache_read_input_tokens", 0)
        self.calls += 1

    def cost_usd(self, model: str) -> float | None:
        if model not in PRICES:
            return None
        pin, pout = PRICES[model]
        # Cache reads bill at a tenth of the input rate.
        uncached = self.input_tokens
        return round((uncached * pin + self.cache_read_input_tokens * pin * 0.1
                      + self.output_tokens * pout) / 1e6, 4)


class LLM:
    def __init__(self, mode: str, recordings: Path, model: str = DEFAULT_MODEL,
                 effort: str = DEFAULT_EFFORT):
        if mode not in {"live", "record", "replay"}:
            raise ValueError(mode)
        self.mode, self.dir, self.model, self.effort = mode, Path(recordings), model, effort
        self.usage = Usage()
        self._client = None

    def _key(self, system: str, messages: list[dict], schema: dict) -> str:
        blob = json.dumps({"model": self.model, "effort": self.effort, "system": system,
                           "messages": messages, "schema": schema}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:24]

    def complete_json(self, system: str, messages: list[dict], schema: dict,
                      tag: str = "") -> dict:
        key = self._key(system, messages, schema)
        path = self.dir / f"{tag + '-' if tag else ''}{key}.json"
        if self.mode == "replay":
            if not path.exists():
                raise MissingRecording(path.name)
            saved = json.loads(path.read_text())
            self.usage.add(saved["usage"])
            return saved["output"]

        output, usage = self._call(system, messages, schema)
        self.usage.add(usage)
        if self.mode == "record":
            self.dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": self.model, "effort": self.effort,
                                        "usage": usage, "output": output}, indent=2) + "\n")
        return output

    def _call(self, system: str, messages: list[dict], schema: dict) -> tuple[dict, dict]:
        import anthropic

        if self._client is None:
            # Own variable and an explicit base URL: Claude Code cloud sessions set
            # ANTHROPIC_BASE_URL for themselves, and an ANTHROPIC_API_KEY there is not used.
            key = os.environ.get("PROOF_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError("Set PROOF_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY) to run against the API.")
            self._client = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")
        response = self._client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            output_config={"effort": self.effort,
                           "format": {"type": "json_schema", "schema": schema}},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise ModelRefused(str(response.stop_details))
        text = next(b.text for b in response.content if b.type == "text")
        u = response.usage
        usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                 "cache_read_input_tokens": u.cache_read_input_tokens or 0}
        return json.loads(text), usage
