"""Persistence layer (SQLite by default, Postgres-ready via the repository)."""
from .repository import CaseRepository, get_repository

__all__ = ["CaseRepository", "get_repository"]
