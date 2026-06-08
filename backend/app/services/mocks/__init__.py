"""Mock external connectors (UAE PASS, MOEI loan system, salary, bank, docs).

All read from a shared synthetic fixture registry; swap any one for a real
connector behind the same function signature without touching the graph.
"""
from . import (
    mock_bank_verifier,
    mock_document_store,
    mock_moei_loan_system,
    mock_salary_verifier,
    mock_uae_pass,
    registry,
)

__all__ = [
    "registry",
    "mock_uae_pass",
    "mock_moei_loan_system",
    "mock_salary_verifier",
    "mock_bank_verifier",
    "mock_document_store",
]
