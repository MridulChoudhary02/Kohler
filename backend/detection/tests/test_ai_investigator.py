"""
backend/detection/tests/test_ai_investigator.py — Guardrail Tests for AI Incident Investigator.

Tests per spec:
1. Strict schema validation of InvestigationReport (summary, likely_cause, evidence, recommended_actions, impact, risk_note).
2. Numeric fidelity cross-check: ensures NO numeric values in the LLM's "evidence" list differ from the real numbers in the evidence object.
3. Read-only DB proof: confirms ticket priority_score and status remain strictly identical in the database before and after the investigation call.
4. Schema validation failure retry and graceful fallback error handling.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Set
from unittest.mock import patch, MagicMock

import httpx
import pytest
from sqlalchemy import select, update

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.main import app
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.models.models import Ticket, DetectionEvent
from app.services.investigation_service import (
    InvestigationReport,
    assemble_ticket_evidence,
    run_incident_investigation,
    parse_and_validate_investigation,
)


def _collect_numbers_from_object(obj: Any) -> Set[float]:
    """Recursively harvest all float/int/timestamp numbers from an evidence object."""
    numbers: Set[float] = set()
    if isinstance(obj, bool):
        return numbers
    if isinstance(obj, (int, float)):
        numbers.add(round(float(obj), 4))
    elif isinstance(obj, str):
        # Extract number tokens, including timestamps and identifiers
        for m in re.findall(r"\b\d+(?:\.\d+)?\b", obj):
            try:
                numbers.add(round(float(m), 4))
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            numbers.update(_collect_numbers_from_object(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            numbers.update(_collect_numbers_from_object(item))
    return numbers


@pytest.mark.anyio
async def test_guardrail_stuck_valve_ticket_investigation():
    """
    Guardrail test for AI Incident Investigator:
    (a) LLM response is valid against the InvestigationReport schema.
    (b) Numeric fidelity cross-check: none of the numbers in LLM 'evidence' differ from actual evidence numbers.
    (c) Ticket's priority_score and status in the DB are provably unchanged (read-only verification).
    """
    # Ensure real database session is used
    app.dependency_overrides.pop(get_db, None)

    # 1. Locate a real leak ticket in DB and set sub_type to stuck_valve
    target_ticket_id = None
    target_event_id = None
    initial_status = None
    initial_priority = None

    async with AsyncSessionLocal() as session:
        stmt = (
            select(Ticket, DetectionEvent)
            .join(DetectionEvent, Ticket.event_id == DetectionEvent.event_id)
            .where(DetectionEvent.event_type == "leak")
            .limit(1)
        )
        res = await session.execute(stmt)
        row = res.first()
        assert row is not None, "A leak ticket must exist in the database for investigation test"
        ticket, event = row

        target_ticket_id = ticket.ticket_id
        target_event_id = event.event_id
        initial_status = str(ticket.status)
        initial_priority = float(ticket.priority_score)

        # Set sub_type to stuck_valve to simulate genuine stuck_valve condition
        event.sub_type = "stuck_valve"
        await session.commit()

    try:
        # 2. Call the new investigation endpoint using httpx.AsyncClient with ASGITransport
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/tickets/{target_ticket_id}/investigation")
            assert response.status_code == 200, f"Endpoint returned error: {response.text}"
            data = response.json()

            assert data["ticket_id"] == target_ticket_id
            assert "evidence" in data
            assert data["error"] is None, f"Investigation returned error: {data['error']}"
            assert data["investigation"] is not None

            # 3. Assertion (a): Strict schema validation
            report = InvestigationReport(**data["investigation"])
            assert len(report.summary.strip()) > 10, "Summary must be non-empty"
            assert len(report.likely_cause.strip()) > 5, "Likely cause must be non-empty"
            assert isinstance(report.evidence, list) and len(report.evidence) >= 1, "Evidence must be non-empty list"
            assert isinstance(report.recommended_actions, list) and len(report.recommended_actions) >= 1, "Actions must be non-empty list"
            assert len(report.impact.strip()) > 5, "Impact must be non-empty"
            assert len(report.risk_note.strip()) > 5, "Risk note must be non-empty"

            # 4. Assertion (b): Numeric cross-check against actual evidence object
            evidence_numbers = _collect_numbers_from_object(data["evidence"])

            for item in report.evidence:
                number_matches = re.findall(r"\b\d+(?:\.\d+)?\b", item)
                for n_str in number_matches:
                    n_val = round(float(n_str), 4)
                    assert n_val in evidence_numbers, (
                        f"LLM hallucinated number {n_str} (value {n_val}) in evidence bullet: '{item}'. "
                        f"Must match a real number from the evidence object!"
                    )

            # 5. Assertion (c): Verify ticket in DB is strictly unchanged
            async with AsyncSessionLocal() as verify_session:
                v_stmt = select(Ticket).where(Ticket.ticket_id == target_ticket_id)
                v_ticket = (await verify_session.execute(v_stmt)).scalars().first()

                assert v_ticket is not None
                assert v_ticket.priority_score == initial_priority, (
                    f"Priority score changed in DB! Initial: {initial_priority}, After: {v_ticket.priority_score}"
                )
                assert v_ticket.status == initial_status, (
                    f"Status changed in DB! Initial: {initial_status}, After: {v_ticket.status}"
                )

    finally:
        # Revert sub_type back cleanly
        async with AsyncSessionLocal() as cleanup_session:
            await cleanup_session.execute(
                update(DetectionEvent)
                .where(DetectionEvent.event_id == target_event_id)
                .values(sub_type=None)
            )
            await cleanup_session.commit()


def test_investigation_json_cleaner_and_parser():
    """Verify clean_json_string and parser cleanly extract JSON from code blocks and validate schema."""
    valid_raw = """```json
    {
        "summary": "Valid summary text here.",
        "likely_cause": "Faulty diaphragm valve.",
        "evidence": ["Flow rate: 4.5 LPM", "Confidence: 0.95"],
        "recommended_actions": ["Isolate line", "Inspect seal"],
        "impact": "Minimal waste",
        "risk_note": "Monitor pressure"
    }
    ```"""
    parsed = parse_and_validate_investigation(valid_raw)
    assert parsed.summary == "Valid summary text here."
    assert len(parsed.evidence) == 2
    assert parsed.likely_cause == "Faulty diaphragm valve."

    # Free text without JSON raises exception
    with pytest.raises(Exception):
        parse_and_validate_investigation("I am not returning JSON, just plain commentary.")


@pytest.mark.anyio
async def test_investigation_retry_and_graceful_error():
    """Verify run_incident_investigation retries once on invalid JSON, then returns graceful structured error."""
    mock_bad_resp = MagicMock()
    mock_bad_resp.choices = [MagicMock(message=MagicMock(content="Invalid free text without JSON"))]

    mock_good_resp = MagicMock()
    mock_good_resp.choices = [MagicMock(message=MagicMock(content="""{
        "summary": "Retry succeeded.",
        "likely_cause": "Solenoid stuck.",
        "evidence": ["UCL: 0.12"],
        "recommended_actions": ["Replace solenoid"],
        "impact": "Water loss",
        "risk_note": "Tier 1 risk"
    }"""))]

    sample_evidence = {
        "ticket": {"ticket_id": "test-1", "status": "open", "priority_score": 85.0},
        "detection_event": {"event_id": "ev-1", "event_type": "leak", "confidence_score": 0.9},
    }

    # Case 1: First attempt fails, retry succeeds
    with patch("litellm.completion", side_effect=[mock_bad_resp, mock_good_resp]):
        report, err = await run_incident_investigation(sample_evidence)
        assert err is None
        assert report is not None
        assert report.summary == "Retry succeeded."

    # Case 2: Both attempts fail -> graceful error returned, no crash
    with patch("litellm.completion", side_effect=[mock_bad_resp, mock_bad_resp]):
        report, err = await run_incident_investigation(sample_evidence)
        assert report is None
        assert err is not None
        assert "validation failed" in err.lower()
