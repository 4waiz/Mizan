"""Services: LLM wrapper (structured-only), audit trail, explanation builder,
and mock external connectors."""
from . import audit, explain, llm

__all__ = ["audit", "explain", "llm"]
