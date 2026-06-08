"""Repository over the cases table. Persists the full CaseState as JSON plus a
few indexed columns for the officer queue / proactive list."""
from __future__ import annotations

from ..schemas import CaseState
from ..services import audit
from .database import get_connection, init_db


class CaseRepository:
    def __init__(self) -> None:
        init_db()

    # ── writes ───────────────────────────────────────────────────────────────
    def save(self, case: CaseState) -> CaseState:
        conn = get_connection()
        try:
            created_at = case.sla.created_at if case.sla else audit.now_iso()
            conn.execute(
                """
                INSERT INTO cases (case_id, status, trigger_type, beneficiary_name,
                                   needs_review, confidence, arrears_amount,
                                   redefault_prob, created_at, updated_at, data)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(case_id) DO UPDATE SET
                    status=excluded.status,
                    beneficiary_name=excluded.beneficiary_name,
                    needs_review=excluded.needs_review,
                    confidence=excluded.confidence,
                    arrears_amount=excluded.arrears_amount,
                    redefault_prob=excluded.redefault_prob,
                    updated_at=excluded.updated_at,
                    data=excluded.data
                """,
                (
                    case.case_id,
                    case.status.value,
                    case.trigger_type.value,
                    case.beneficiary.full_name_en if case.beneficiary else None,
                    1 if case.needs_human_review else 0,
                    case.confidence.value if case.confidence else None,
                    case.arrears.arrears_amount_aed if case.arrears else None,
                    case.risk.redefault_probability if case.risk else None,
                    created_at,
                    audit.now_iso(),
                    case.model_dump_json(),
                ),
            )
            conn.commit()
            return case
        finally:
            conn.close()

    # ── reads ────────────────────────────────────────────────────────────────
    def get(self, case_id: str) -> CaseState | None:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT data FROM cases WHERE case_id=?", (case_id,)
            ).fetchone()
            return CaseState.model_validate_json(row["data"]) if row else None
        finally:
            conn.close()

    def list_all(self) -> list[CaseState]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT data FROM cases ORDER BY created_at DESC"
            ).fetchall()
            return [CaseState.model_validate_json(r["data"]) for r in rows]
        finally:
            conn.close()

    def list_queue(self) -> list[CaseState]:
        """Cases awaiting human review (officer queue)."""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT data FROM cases WHERE needs_review=1 "
                "AND status='pending_human_review' ORDER BY created_at ASC"
            ).fetchall()
            return [CaseState.model_validate_json(r["data"]) for r in rows]
        finally:
            conn.close()

    def list_proactive(self) -> list[CaseState]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT data FROM cases WHERE trigger_type='proactive_flag' "
                "ORDER BY redefault_prob DESC"
            ).fetchall()
            return [CaseState.model_validate_json(r["data"]) for r in rows]
        finally:
            conn.close()


_repo: CaseRepository | None = None


def get_repository() -> CaseRepository:
    global _repo
    if _repo is None:
        _repo = CaseRepository()
    return _repo
