"""Conditional routing helpers for the graph.

The decision of escalate-vs-auto lives in `human_review_gate`; the router simply
reads the resulting flag. Both branches still produce a rationale memo and a
finalised case, so the routing keeps the audit trail complete either way.
"""
from __future__ import annotations

from .state import GraphState


def should_escalate(state: GraphState) -> str:
    """After the gate, branch label for LangGraph conditional edges."""
    return "escalated" if state["case"].needs_human_review else "auto"
