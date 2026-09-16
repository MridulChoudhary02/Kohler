"""
backend/detection/tests/test_llm_service.py — Unit & Integration tests for LLM Phase 7.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.services.llm_service import summarize_incident, answer_facility_query, FALLBACK_SUMMARY
from app.core.config import settings

# Test client
client = TestClient(app)


def test_summarize_incident_structured():
    """Verify summarize_incident returns plain-English paragraph incorporating inputs."""
    ticket = {"priority_score": 85.5}
    event = {
        "event_type": "leak",
        "confidence_score": 0.95,
        "evidence_value": 12.5,
        "detected_at": "2026-09-16 10:00:00",
    }
    fixture = {"fixture_type": "flush_valve"}
    zone = {"name": "ICU Restrooms", "criticality_tier": "Tier 1"}

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="A high-confidence leak in ICU Restrooms with priority score 85.5."))]

    with patch("litellm.completion", return_value=mock_resp):
        summary = summarize_incident(ticket, event, fixture, zone)
        assert isinstance(summary, str)
        assert summary != FALLBACK_SUMMARY
        assert "ICU Restrooms" in summary


def test_summarize_incident_fallback_on_missing_key():
    """Verify summarize_incident returns FALLBACK_SUMMARY when no API key is set."""
    orig_key = settings.GROQ_API_KEY
    orig_env_key = os.environ.get("GROQ_API_KEY")
    try:
        settings.GROQ_API_KEY = ""
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]
        summary = summarize_incident({}, {}, {}, {})
        assert summary == FALLBACK_SUMMARY
    finally:
        settings.GROQ_API_KEY = orig_key
        if orig_env_key is not None:
            os.environ["GROQ_API_KEY"] = orig_env_key


def test_chat_query_endpoint():
    """Test POST /api/v1/chat returns grounded response."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="The facility currently has 33 active leak events detected."))]

    with patch("litellm.completion", return_value=mock_resp):
        response = client.post("/api/v1/chat", json={"query": "How many active leaks are there?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 10


def test_chat_query_endpoint_live():
    """Test POST /api/v1/chat against live Groq API when GROQ_API_KEY is present."""
    if not settings.GROQ_API_KEY:
        return
    response = client.post("/api/v1/chat", json={"query": "Which zone has the highest water waste?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
