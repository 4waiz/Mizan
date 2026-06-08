"""Graph state wrapper.

The LangGraph channel carries the whole `CaseState` under a single key with
last-value-wins semantics, so node functions can keep their simple
`CaseState -> CaseState` signature regardless of LangGraph version.
"""
from __future__ import annotations

from typing import TypedDict

from ..schemas import CaseState  # re-exported for convenience

__all__ = ["CaseState", "GraphState"]


class GraphState(TypedDict):
    case: CaseState
