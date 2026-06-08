"""Build and run the case-processing pipeline.

LangGraph is the workflow spine. If `langgraph` is installed we compile a real
`StateGraph`; if it is not (or fails to import), we fall back to an equivalent
in-process sequential runner so the application ALWAYS runs. Both drive the exact
same node functions over the same shared `CaseState`.
"""
from __future__ import annotations

from ..schemas import CaseState
from . import nodes
from .router import should_escalate
from .state import GraphState

_LANGGRAPH_AVAILABLE = False
try:  # pragma: no cover - import guard
    from langgraph.graph import END, START, StateGraph

    _LANGGRAPH_AVAILABLE = True
except Exception:  # langgraph not installed -> fallback runner
    _LANGGRAPH_AVAILABLE = False


def _wrap(node_module):
    """Adapt a `run(CaseState)->CaseState` node to the GraphState channel."""

    def _inner(state: GraphState) -> dict:
        return {"case": node_module.run(state["case"])}

    _inner.__name__ = node_module.NODE
    return _inner


def _build_langgraph():
    g = StateGraph(GraphState)

    ordered = [
        nodes.intake_and_retrieve,
        nodes.document_audit,
        nodes.fraud_and_dedupe_check,
        nodes.affordability_analysis,
        nodes.risk_forecast,
        nodes.policy_solver,
        nodes.human_review_gate,
        nodes.rationale_generator,
        nodes.finalize_case,
    ]
    for n in ordered:
        g.add_node(n.NODE, _wrap(n))

    g.add_edge(START, nodes.intake_and_retrieve.NODE)
    # Linear chain up to the gate.
    chain = ordered[:7]  # through human_review_gate
    for a, b in zip(chain, chain[1:]):
        g.add_edge(a.NODE, b.NODE)

    # After the gate, both branches converge on rationale -> finalize.
    g.add_conditional_edges(
        nodes.human_review_gate.NODE,
        should_escalate,
        {"escalated": nodes.rationale_generator.NODE, "auto": nodes.rationale_generator.NODE},
    )
    g.add_edge(nodes.rationale_generator.NODE, nodes.finalize_case.NODE)
    g.add_edge(nodes.finalize_case.NODE, END)
    return g.compile()


_compiled = None


def get_pipeline():
    global _compiled
    if _compiled is None and _LANGGRAPH_AVAILABLE:
        try:
            _compiled = _build_langgraph()
        except Exception:
            _compiled = None
    return _compiled


def run_pipeline(case: CaseState) -> CaseState:
    """Execute the full pipeline on a case, returning the finalised state."""
    pipeline = get_pipeline()
    if pipeline is not None:
        result = pipeline.invoke({"case": case})
        out = result["case"]
        return out if isinstance(out, CaseState) else CaseState.model_validate(out)

    # Fallback: deterministic sequential runner.
    for node_module in nodes.PIPELINE:
        case = node_module.run(case)
    return case


def engine_name() -> str:
    return "langgraph" if get_pipeline() is not None else "sequential-fallback"
