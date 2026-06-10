"""Organizer-provided historical dataset ingestion.

This package loads, cleans, and exposes the official MOEI / Sheikh Zayed Housing
Programme historical arrears-rescheduling dataset (``data/RescheduleArrears.xlsx``,
2023–2025). It is used for aggregated insights, risk calibration, policy
edge-case analysis, and data-informed demo realism — never to expose raw,
identifiable records in the UI.
"""
from __future__ import annotations

from .organizer_dataset import (
    DATASET_RELATIVE_PATH,
    OrganizerDataset,
    load_organizer_dataset,
    resolve_dataset_path,
)

__all__ = [
    "DATASET_RELATIVE_PATH",
    "OrganizerDataset",
    "load_organizer_dataset",
    "resolve_dataset_path",
]
