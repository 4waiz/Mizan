"""LLM telemetry — extract live token usage + model metadata from LangChain
`AIMessage` responses and record it onto the `CaseState`.

This layer is deliberately defensive: token metadata shapes differ across
providers and LangChain versions, and a missing field must NEVER crash the
pipeline. Every extractor degrades gracefully to zeros and the run continues.

Groq returns OpenAI-compatible usage on the `AIMessage`:

    AIMessage(
        content=...,
        response_metadata={
            "model_name": "llama-3.3-70b-versatile",
            "finish_reason": "stop",
            "token_usage": {              # <-- Groq / OpenAI shape
                "prompt_tokens": 812,
                "completion_tokens": 143,
                "total_tokens": 955,
            },
        },
        usage_metadata={                  # <-- LangChain-normalised shape
            "input_tokens": 812,
            "output_tokens": 143,
            "total_tokens": 955,
        },
    )

We prefer `usage_metadata` (provider-agnostic), then fall back to the raw
`response_metadata["token_usage"]` (Groq native), then to a usage object
hanging off `additional_kwargs` — whichever is present.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

from ..config import get_settings
from ..schemas import CaseState, ComputationLogEntry, TokenUsage
from . import audit


def _as_int(value: Any) -> int:
    """Coerce a possibly-missing/None/str token count to a non-negative int."""
    try:
        n = int(value)
        return n if n >= 0 else 0
    except (TypeError, ValueError):
        return 0


def extract_token_usage(message: Any) -> TokenUsage:
    """Pull prompt/completion/total tokens off any LangChain AIMessage-like object.

    Tries every known location and never raises — returns zeroed usage if the
    metadata is absent or malformed.
    """
    if message is None:
        return TokenUsage()

    # 1) LangChain-normalised usage_metadata (preferred; provider-agnostic).
    usage_meta = getattr(message, "usage_metadata", None)
    if isinstance(usage_meta, dict) and usage_meta:
        prompt = _as_int(usage_meta.get("input_tokens"))
        completion = _as_int(usage_meta.get("output_tokens"))
        total = _as_int(usage_meta.get("total_tokens")) or (prompt + completion)
        if prompt or completion or total:
            return TokenUsage(
                prompt_tokens=prompt, completion_tokens=completion, total_tokens=total
            )

    # 2) Raw provider metadata — Groq/OpenAI nest it under "token_usage".
    resp_meta = getattr(message, "response_metadata", None) or {}
    if isinstance(resp_meta, dict):
        tu = resp_meta.get("token_usage") or resp_meta.get("usage") or {}
        if isinstance(tu, dict) and tu:
            prompt = _as_int(tu.get("prompt_tokens") or tu.get("input_tokens"))
            completion = _as_int(tu.get("completion_tokens") or tu.get("output_tokens"))
            total = _as_int(tu.get("total_tokens")) or (prompt + completion)
            if prompt or completion or total:
                return TokenUsage(
                    prompt_tokens=prompt, completion_tokens=completion, total_tokens=total
                )

    # 3) Last resort: additional_kwargs.usage (older LangChain shims).
    add_kwargs = getattr(message, "additional_kwargs", None) or {}
    if isinstance(add_kwargs, dict):
        tu = add_kwargs.get("usage") or {}
        if isinstance(tu, dict) and tu:
            prompt = _as_int(tu.get("prompt_tokens"))
            completion = _as_int(tu.get("completion_tokens"))
            total = _as_int(tu.get("total_tokens")) or (prompt + completion)
            return TokenUsage(
                prompt_tokens=prompt, completion_tokens=completion, total_tokens=total
            )

    return TokenUsage()


def extract_model_name(message: Any, fallback: str) -> str:
    """Resolve the model name the provider actually served the response with."""
    resp_meta = getattr(message, "response_metadata", None) or {}
    if isinstance(resp_meta, dict):
        name = resp_meta.get("model_name") or resp_meta.get("model")
        if name:
            return str(name)
    return fallback


def extract_finish_reason(message: Any) -> str | None:
    resp_meta = getattr(message, "response_metadata", None) or {}
    if isinstance(resp_meta, dict):
        fr = resp_meta.get("finish_reason") or resp_meta.get("stop_reason")
        if fr:
            return str(fr)
    return None


def record_call(
    state: CaseState,
    *,
    node: str,
    task: str,
    message: Any,
    duration_ms: float | None,
    live: bool,
) -> ComputationLogEntry:
    """Build a ComputationLogEntry from an AIMessage and append it to the
    case telemetry. Always succeeds, even with no/partial metadata."""
    settings = get_settings()
    usage = extract_token_usage(message)
    provider = settings.llm_provider if live else "mock"
    model = (
        extract_model_name(message, settings.active_model)
        if live
        else "mock-deterministic"
    )
    entry = ComputationLogEntry(
        seq=len(state.telemetry.computation_log),
        node=node,
        task=task,
        provider=provider,
        model=model,
        usage=usage,
        finish_reason=extract_finish_reason(message) if live else "mock",
        live=live,
        duration_ms=duration_ms,
        timestamp=audit.now_iso(),
    )
    state.telemetry.record(entry)
    return entry


def record_mock(state: CaseState, *, node: str, task: str) -> ComputationLogEntry:
    """Log a deterministic (no-API) computation so the dashboard still shows the
    pipeline ran — clearly flagged live=False with zero tokens."""
    return record_call(
        state, node=node, task=task, message=None, duration_ms=None, live=False
    )


@contextmanager
def timed():
    """Context manager yielding a callable that returns elapsed milliseconds."""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000.0
