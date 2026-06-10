"""Replay summary endpoint + service."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _fixture_count() -> int:
    from app.services.mocks import registry

    return len(registry.all_fixtures())


def test_replay_summary_service():
    from app.services.replay import replay_summary

    n = _fixture_count()
    summary = replay_summary()
    assert summary["total_cases"] == n
    assert summary["straight_through"] + summary["human_review"] == n
    assert summary["estimated_manual_working_days_saved"] >= 0
    assert "by_outcome" in summary and summary["by_outcome"]


def test_replay_summary_endpoint():
    from app.main import app

    n = _fixture_count()
    with TestClient(app) as client:
        resp = client.get("/api/replay/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cases"] == n
        assert len(data["cases"]) == n


def test_proactive_alerts_endpoint():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/api/proactive/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) >= 1
        assert "redefault_probability" in alerts[0]
