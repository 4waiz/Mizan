"""Mock document store.

Returns the documents on file for a case (with mock raw_text the extractor
reads). Beneficiary uploads in the UI are merged into this set by the API.
"""
from __future__ import annotations

from ...schemas import Document, DocumentInventory


def get_documents(record: dict) -> list[Document]:
    return [Document(**d) for d in record.get("documents", [])]


def build_inventory(record: dict) -> DocumentInventory:
    return DocumentInventory(documents=get_documents(record))
