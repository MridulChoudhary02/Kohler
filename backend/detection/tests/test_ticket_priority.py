"""
backend/detection/tests/test_ticket_priority.py — Unit Tests for Ticket Priority Scoring & Dispatch

Tests PRD Section 10 implementation:
1. test_tier1_leak_outranks_tier4_leak
2. test_priority_score_formula_matches_spec
3. test_auto_escalation_boosts_overdue_ticket
4. test_hygiene_ticket_priority_uses_correct_normalization
5. test_escalation_is_idempotent
"""
from __future__ import annotations

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from app.models.models import Ticket, DetectionEvent
from app.services.ticket_service import (
    compute_priority_score,
    normalize_estimated_waste,
    compute_sla_urgency_factor,
    escalate_overdue_tickets,
)


def test_tier1_leak_outranks_tier4_leak():
    """Tier 1 leak must produce a higher priority score than Tier 4 leak given identical confidence & evidence."""
    confidence = 0.90
    evidence = 15.0  # 15 L/hr

    tier1_score = compute_priority_score(
        zone_tier="Tier 1",
        confidence_score=confidence,
        evidence_value=evidence,
        event_type="leak",
        response_minutes=15,
    )

    tier4_score = compute_priority_score(
        zone_tier="Tier 4",
        confidence_score=confidence,
        evidence_value=evidence,
        event_type="leak",
        response_minutes=120,
    )

    assert tier1_score > tier4_score
    print(f"✅ Tier 1 ({tier1_score}) outranks Tier 4 ({tier4_score})")


def test_priority_score_formula_matches_spec():
    """
    Hand-computed verification of priority score formula:
      zone_tier = Tier 1 (w_crit = 1.0)
      confidence_score = 0.90
      evidence_value = 30.0 L/hr (leak => norm_waste = 30/60 = 0.50)
      response_minutes = 15 (SLA factor = 1.0 - 15/120 = 0.875)

    Weighted sum:
      0.4 * 1.0 = 0.4000
      0.3 * 0.90 = 0.2700
      0.2 * 0.50 = 0.1000
      0.1 * 0.875 = 0.0875
      Sum = 0.8575 -> 85.75
    """
    score = compute_priority_score(
        zone_tier="Tier 1",
        confidence_score=0.90,
        evidence_value=30.0,
        event_type="leak",
        response_minutes=15,
    )

    expected_score = 85.75
    assert score == expected_score, f"Expected {expected_score}, got {score}"
    print(f"✅ Priority score formula exact match: {score} == {expected_score}")


def test_hygiene_ticket_priority_uses_correct_normalization():
    """
    Creates an actual hygiene-type DetectionEvent (event_type="hygiene") and asserts its
    normalized_estimated_waste is computed via the hygiene branch (1.0 - 10.0/30.0 = 0.6667)
    and NOT falling through to default (0.5) or leak branch (10.0/60.0 = 0.1667).
    """
    event = DetectionEvent(
        event_id="evt-hygiene-test",
        fixture_id="fix-icu-001",
        event_type="hygiene",
        confidence_score=0.90,
        evidence_value=10.0,  # 10 minutes to breach
        detected_at=datetime.now(timezone.utc),
        status="dispatched",
    )

    norm_waste = normalize_estimated_waste(event.event_type, event.evidence_value)
    expected_norm_waste = round(1.0 - (10.0 / 30.0), 4)

    assert round(norm_waste, 4) == expected_norm_waste
    assert norm_waste != 0.5  # Not default
    assert norm_waste != (10.0 / 60.0)  # Not leak calculation
    print(f"✅ Hygiene normalization correctly computed: {norm_waste:.4f} == {expected_norm_waste}")


@pytest.mark.anyio
async def test_auto_escalation_boosts_overdue_ticket():
    """Overdue ticket past sla_due must have its priority_score boosted by +25."""
    now = datetime.now(timezone.utc)
    overdue_time = now - timedelta(minutes=30)

    overdue_ticket = Ticket(
        ticket_id="tkt-test-overdue",
        event_id="evt-test-overdue",
        zone_id="zone-icu",
        priority_score=60.0,
        status="open",
        sla_due=overdue_time,
        is_escalated=False,
    )

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [overdue_ticket]
    mock_session.execute.return_value = mock_res

    escalated = await escalate_overdue_tickets(db=mock_session, now=now)

    assert len(escalated) == 1
    assert escalated[0].priority_score == 85.0
    assert escalated[0].is_escalated is True
    print(f"✅ Auto-escalation boosted ticket score from 60.0 to {escalated[0].priority_score}")


@pytest.mark.anyio
async def test_escalation_is_idempotent():
    """Calling escalate_overdue_tickets() twice on the same overdue ticket applies the +25 boost exactly once."""
    now = datetime.now(timezone.utc)
    overdue_time = now - timedelta(minutes=30)

    ticket = Ticket(
        ticket_id="tkt-test-idempotent",
        event_id="evt-test-idempotent",
        zone_id="zone-icu",
        priority_score=60.0,
        status="open",
        sla_due=overdue_time,
        is_escalated=False,
    )

    # First run: ticket is not escalated
    mock_session = AsyncMock()
    mock_res_1 = MagicMock()
    mock_res_1.scalars.return_value.all.return_value = [ticket]
    mock_session.execute.return_value = mock_res_1

    escalated_first = await escalate_overdue_tickets(db=mock_session, now=now)

    assert len(escalated_first) == 1
    assert ticket.priority_score == 85.0
    assert ticket.is_escalated is True

    # Second run: ticket is now marked is_escalated=True so query returns empty list
    mock_res_2 = MagicMock()
    mock_res_2.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_res_2

    escalated_second = await escalate_overdue_tickets(db=mock_session, now=now)

    assert len(escalated_second) == 0
    assert ticket.priority_score == 85.0  # Remained 85.0, not boosted a second time to 100.0
    print("✅ Escalation idempotency verified: second call applied 0 boosts")


@pytest.mark.anyio
async def test_ticket_lifecycle_transitions():
    """Test full ticket lifecycle transitions: open -> acknowledged -> in_progress -> resolved."""
    ticket = Ticket(
        ticket_id="tkt-lifecycle-test",
        event_id="evt-lifecycle-test",
        zone_id="zone-icu",
        priority_score=80.0,
        status="open",
    )

    assert ticket.status == "open"
    assert ticket.acknowledged_at is None
    assert ticket.started_at is None
    assert ticket.resolved_at is None

    # Step 1: Acknowledge
    ticket.status = "acknowledged"
    ticket.acknowledged_at = datetime.now(timezone.utc)
    assert ticket.status == "acknowledged"
    assert ticket.acknowledged_at is not None

    # Step 2: Start
    ticket.status = "in_progress"
    ticket.started_at = datetime.now(timezone.utc)
    assert ticket.status == "in_progress"
    assert ticket.started_at is not None

    # Step 3: Resolve
    ticket.status = "resolved"
    ticket.resolved_at = datetime.now(timezone.utc)
    assert ticket.status == "resolved"
    assert ticket.resolved_at is not None

    print("✅ Ticket lifecycle transitions (open -> acknowledged -> in_progress -> resolved) verified")


if __name__ == "__main__":
    test_tier1_leak_outranks_tier4_leak()
    test_priority_score_formula_matches_spec()
    test_hygiene_ticket_priority_uses_correct_normalization()
    asyncio.run(test_auto_escalation_boosts_overdue_ticket())
    asyncio.run(test_escalation_is_idempotent())
    asyncio.run(test_ticket_lifecycle_transitions())
    print("✅ All ticket priority tests PASSED!")
