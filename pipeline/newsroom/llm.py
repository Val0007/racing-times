"""Tiny wrapper: ask Claude for JSON that matches a schema (forced tool call)."""
from __future__ import annotations

import os

import anthropic

FAST_MODEL = os.getenv("RT_FAST_MODEL", "claude-haiku-5-5")      # link extraction, triage
EDITOR_MODEL = os.getenv("RT_EDITOR_MODEL", "claude-sonnet-5-5")  # clustering, writing, layout choices

_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


def ask_json(prompt: str, schema: dict, *, model: str = FAST_MODEL, system: str = "", max_tokens: int = 8000) -> dict:
    resp = _client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system or "You are a precise assistant that returns only structured data.",
        tools=[{"name": "submit", "description": "Return the result.", "input_schema": schema}],
        tool_choice={"type": "tool", "name": "submit"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("model returned no structured output")
