"""Replay summary endpoint + service."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_replay_summary_service():
    from app.services.replay import replay_summary

    summary = replay_summary()
    assert summary["total_cases"] == 8
    assert summary["straight_through"] + summary["human_review"] == 8
    assert summary["estimated_manual_working_days_saved"] >= 0
    assert "by_outcome" in summary and summary["by_outcome"]


def test_replay_summary_endpoint():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/api/replay/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cases"] == 8
        assert len(data["cases"]) == 8


def test_proactive_alerts_endpoint():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/api/proactive/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) >= 1
        assert "redefault_probability" in alerts[0]
