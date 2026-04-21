"""Tests for the process mining engine."""

from datetime import datetime, timedelta

import pytest
from core.engines.discovery import ProcessMiningEngine, ProcessMiningResult


@pytest.fixture
def sample_events():
    """Simple 10-case event log for a 3-step process."""
    events = []
    activities = ["Receive", "Process", "Approve", "Close"]
    base = datetime(2024, 1, 1, 9, 0)
    for case_num in range(1, 11):
        ts = base + timedelta(hours=case_num)
        for i, act in enumerate(activities):
            events.append({
                "case_id": f"C{case_num:03d}",
                "activity": act,
                "timestamp": ts + timedelta(minutes=i * 30),
                "resource": f"User-{case_num % 3 + 1}",
            })
    return events


@pytest.fixture
def engine():
    return ProcessMiningEngine()


def test_mine_returns_result(engine, sample_events):
    result = engine.mine(events=sample_events)
    assert isinstance(result, ProcessMiningResult)


def test_correct_case_count(engine, sample_events):
    result = engine.mine(events=sample_events)
    assert result.total_cases == 10


def test_correct_event_count(engine, sample_events):
    result = engine.mine(events=sample_events)
    assert result.total_events == 40  # 10 cases × 4 activities


def test_activities_discovered(engine, sample_events):
    result = engine.mine(events=sample_events)
    names = {a.activity for a in result.activities}
    assert names == {"Receive", "Process", "Approve", "Close"}


def test_transitions_discovered(engine, sample_events):
    result = engine.mine(events=sample_events)
    assert ("Receive", "Process") in result.transitions
    assert ("Process", "Approve") in result.transitions
    assert ("Approve", "Close") in result.transitions


def test_single_variant_for_uniform_log(engine, sample_events):
    result = engine.mine(events=sample_events)
    assert len(result.variants) == 1
    assert result.variants[0].pct_of_total == 100.0


def test_high_conformance_fitness(engine, sample_events):
    result = engine.mine(events=sample_events)
    assert result.conformance_fitness >= 0.9


def test_to_dict_format(engine, sample_events):
    result = engine.mine(events=sample_events)
    d = result.to_dict()
    assert "summary" in d
    assert "activities" in d
    assert "variants" in d
    assert "bottlenecks" in d
    assert "automation_candidates" in d


def test_automation_score_heuristic(engine):
    assert engine._score_automation_potential("Send Email Notification") > 0.5
    assert engine._score_automation_potential("Negotiate Contract") < 0.5


def test_empty_events_raises(engine):
    with pytest.raises(ValueError):
        engine.mine(events=[])
