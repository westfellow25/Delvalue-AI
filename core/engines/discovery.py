"""
DelValue AI — Process Mining & Discovery Engine

Discovers processes from enterprise system event logs — no manual entry required.
This is the automation layer that eliminates the #1 friction point for competitors:
the need for consultants to document every process.

Core capabilities:
  1. Event log ingestion (CSV, XES, API)
  2. Process discovery (alpha miner variant — builds a directly-follows graph)
  3. Variant analysis (distinct execution paths through a process)
  4. Bottleneck detection (waiting time analysis)
  5. Conformance checking (actual vs expected flow)
  6. Automation candidate ranking (finds highly repetitive, structured paths)

Event log format (normalized):
  case_id: unique execution instance
  activity: step name
  timestamp: when it happened
  resource: who/what performed it (optional)
  cost: per-activity cost (optional)
"""

from __future__ import annotations

import csv
import io
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from data.models.process import ProcessMiningLog

logger = logging.getLogger(__name__)


@dataclass
class ProcessVariant:
    """A distinct sequence of activities observed in the event log."""

    sequence: tuple[str, ...]
    frequency: int
    avg_duration_seconds: float
    pct_of_total: float
    sample_case_ids: list[str] = field(default_factory=list)


@dataclass
class ActivityStats:
    """Statistics for a single activity."""

    activity: str
    frequency: int
    avg_duration_seconds: float
    median_duration_seconds: float
    avg_waiting_time_seconds: float
    unique_resources: int
    error_count: int
    automation_score: float  # 0-1, higher = easier to automate


@dataclass
class Bottleneck:
    """An activity identified as a bottleneck."""

    activity: str
    avg_waiting_time_seconds: float
    total_waiting_time_hours: float
    frequency: int
    impact_score: float  # weighted by frequency × avg waiting time
    description: str


@dataclass
class AutomationCandidate:
    """A process fragment identified as a good automation candidate."""

    name: str
    activities: list[str]
    frequency: int
    avg_duration_seconds: float
    annual_executions: int
    estimated_hours_saved: float
    automation_score: float
    rationale: str


@dataclass
class ProcessMiningResult:
    """Complete output of a process mining analysis."""

    total_cases: int
    total_events: int
    period_start: datetime
    period_end: datetime
    avg_case_duration_seconds: float
    median_case_duration_seconds: float

    # Process model
    activities: list[ActivityStats]
    transitions: dict[tuple[str, str], int]  # (from, to) -> frequency
    variants: list[ProcessVariant]

    # Insights
    bottlenecks: list[Bottleneck]
    automation_candidates: list[AutomationCandidate]

    # Conformance
    conformance_fitness: float  # 0-1
    num_deviations: int

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_cases": self.total_cases,
                "total_events": self.total_events,
                "period_start": self.period_start.isoformat() if self.period_start else None,
                "period_end": self.period_end.isoformat() if self.period_end else None,
                "avg_case_duration_hours": round(self.avg_case_duration_seconds / 3600, 2),
                "median_case_duration_hours": round(self.median_case_duration_seconds / 3600, 2),
            },
            "activities": [
                {
                    "activity": a.activity,
                    "frequency": a.frequency,
                    "avg_duration_minutes": round(a.avg_duration_seconds / 60, 2),
                    "avg_waiting_time_minutes": round(a.avg_waiting_time_seconds / 60, 2),
                    "unique_resources": a.unique_resources,
                    "automation_score": round(a.automation_score, 3),
                }
                for a in self.activities
            ],
            "transitions": {
                f"{src}->{dst}": count
                for (src, dst), count in self.transitions.items()
            },
            "variants": [
                {
                    "sequence": list(v.sequence),
                    "frequency": v.frequency,
                    "pct_of_total": round(v.pct_of_total, 2),
                    "avg_duration_hours": round(v.avg_duration_seconds / 3600, 2),
                }
                for v in self.variants[:20]  # top 20 variants
            ],
            "bottlenecks": [
                {
                    "activity": b.activity,
                    "avg_waiting_time_hours": round(b.avg_waiting_time_seconds / 3600, 2),
                    "total_waiting_time_hours": round(b.total_waiting_time_hours, 2),
                    "frequency": b.frequency,
                    "impact_score": round(b.impact_score, 2),
                    "description": b.description,
                }
                for b in self.bottlenecks
            ],
            "automation_candidates": [
                {
                    "name": c.name,
                    "activities": c.activities,
                    "frequency": c.frequency,
                    "annual_executions": c.annual_executions,
                    "estimated_hours_saved": round(c.estimated_hours_saved, 1),
                    "automation_score": round(c.automation_score, 3),
                    "rationale": c.rationale,
                }
                for c in self.automation_candidates
            ],
            "conformance": {
                "fitness": round(self.conformance_fitness, 3),
                "num_deviations": self.num_deviations,
            },
        }


class ProcessMiningEngine:
    """
    Process mining engine — discovers, analyzes, and ranks business processes
    from event log data.
    """

    # Activities with these keywords are likely automatable
    AUTOMATION_KEYWORDS = [
        "approve", "validate", "check", "review", "verify",
        "send", "notify", "email", "create", "update",
        "calculate", "compute", "extract", "export", "import",
        "generate", "populate", "match", "reconcile",
    ]

    # Activities with these keywords typically require human judgment
    HUMAN_KEYWORDS = [
        "negotiate", "investigate", "consult", "discuss",
        "decide", "judge", "interpret", "advise", "counsel",
    ]

    def __init__(self, session: Optional[Session] = None):
        self.session = session

    # -- Event log ingestion --

    def ingest_csv(
        self,
        csv_content: str,
        organization_id: str,
        source_system: Optional[str] = None,
        mapping: Optional[dict[str, str]] = None,
    ) -> int:
        """
        Ingest events from CSV content.

        Args:
            csv_content: CSV string with headers
            organization_id: Tenant ID for multi-tenant isolation
            source_system: Name of the source system
            mapping: Optional column mapping (e.g., {"case_id": "OrderID"})

        Returns:
            Number of events ingested
        """
        if self.session is None:
            raise RuntimeError("Session required for ingestion")

        mapping = mapping or {
            "case_id": "case_id",
            "activity": "activity",
            "timestamp": "timestamp",
            "resource": "resource",
        }

        reader = csv.DictReader(io.StringIO(csv_content))
        events = []
        for row in reader:
            try:
                events.append(ProcessMiningLog(
                    organization_id=organization_id,
                    case_id=row[mapping["case_id"]],
                    activity=row[mapping["activity"]],
                    timestamp=self._parse_timestamp(row[mapping["timestamp"]]),
                    resource=row.get(mapping.get("resource", "resource")),
                    source_system=source_system,
                ))
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping malformed row: {e}")
                continue

        self.session.add_all(events)
        self.session.flush()
        return len(events)

    @staticmethod
    def _parse_timestamp(s: str) -> datetime:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s.strip(), fmt)
            except ValueError:
                continue
        # Last resort: ISO format
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    # -- Analysis --

    def mine(
        self,
        events: Optional[list[dict]] = None,
        organization_id: Optional[str] = None,
        hourly_cost: float = 75.0,
    ) -> ProcessMiningResult:
        """
        Run full process mining analysis.

        Args:
            events: Optional list of event dicts (for stateless analysis)
            organization_id: If provided, loads events from DB
            hourly_cost: Hourly cost for automation savings calculations

        Returns:
            Complete mining result with activities, variants, bottlenecks, candidates
        """
        if events is None and organization_id and self.session:
            events = self._load_events_from_db(organization_id)
        if not events:
            raise ValueError("No events provided")

        # Group by case
        cases: dict[str, list[dict]] = defaultdict(list)
        for e in events:
            cases[e["case_id"]].append(e)

        # Sort each case by timestamp
        for case_id in cases:
            cases[case_id].sort(key=lambda x: x["timestamp"])

        # Compute case durations
        case_durations = []
        period_start = None
        period_end = None
        for case_events in cases.values():
            if len(case_events) < 2:
                continue
            start = case_events[0]["timestamp"]
            end = case_events[-1]["timestamp"]
            duration = (end - start).total_seconds()
            case_durations.append(duration)
            if period_start is None or start < period_start:
                period_start = start
            if period_end is None or end > period_end:
                period_end = end

        case_durations.sort()
        avg_case_duration = sum(case_durations) / max(len(case_durations), 1)
        median_case_duration = case_durations[len(case_durations) // 2] if case_durations else 0

        # Analyze activities
        activities = self._analyze_activities(cases)

        # Build directly-follows graph (transitions)
        transitions = self._build_transitions(cases)

        # Discover variants
        variants = self._discover_variants(cases)

        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks(cases, activities)

        # Identify automation candidates
        candidates = self._identify_automation_candidates(
            activities, variants, hourly_cost,
        )

        # Conformance — fitness score based on variant concentration
        fitness = self._compute_fitness(variants)

        return ProcessMiningResult(
            total_cases=len(cases),
            total_events=len(events),
            period_start=period_start,
            period_end=period_end,
            avg_case_duration_seconds=avg_case_duration,
            median_case_duration_seconds=median_case_duration,
            activities=activities,
            transitions=transitions,
            variants=variants,
            bottlenecks=bottlenecks,
            automation_candidates=candidates,
            conformance_fitness=fitness,
            num_deviations=max(0, len(variants) - 5),  # deviations beyond top-5 paths
        )

    def _load_events_from_db(self, organization_id: str) -> list[dict]:
        logs = (
            self.session.query(ProcessMiningLog)
            .filter(ProcessMiningLog.organization_id == organization_id)
            .order_by(ProcessMiningLog.case_id, ProcessMiningLog.timestamp)
            .all()
        )
        return [
            {
                "case_id": log.case_id,
                "activity": log.activity,
                "timestamp": log.timestamp,
                "resource": log.resource,
            }
            for log in logs
        ]

    def _analyze_activities(self, cases: dict[str, list[dict]]) -> list[ActivityStats]:
        """Compute per-activity statistics."""
        activity_events: dict[str, list[dict]] = defaultdict(list)
        activity_durations: dict[str, list[float]] = defaultdict(list)
        activity_waits: dict[str, list[float]] = defaultdict(list)
        activity_resources: dict[str, set] = defaultdict(set)

        for case_events in cases.values():
            for i, event in enumerate(case_events):
                activity = event["activity"]
                activity_events[activity].append(event)
                if event.get("resource"):
                    activity_resources[activity].add(event["resource"])

                # Waiting time from previous activity completion
                if i > 0:
                    wait = (event["timestamp"] - case_events[i - 1]["timestamp"]).total_seconds()
                    activity_waits[activity].append(wait)

                # Duration to next activity (as proxy for this activity's duration)
                if i < len(case_events) - 1:
                    dur = (case_events[i + 1]["timestamp"] - event["timestamp"]).total_seconds()
                    activity_durations[activity].append(dur)

        result = []
        for activity, evs in activity_events.items():
            durations = activity_durations.get(activity, [0])
            waits = activity_waits.get(activity, [0])
            result.append(ActivityStats(
                activity=activity,
                frequency=len(evs),
                avg_duration_seconds=sum(durations) / max(len(durations), 1),
                median_duration_seconds=sorted(durations)[len(durations) // 2] if durations else 0,
                avg_waiting_time_seconds=sum(waits) / max(len(waits), 1),
                unique_resources=len(activity_resources[activity]),
                error_count=0,  # would require error labels
                automation_score=self._score_automation_potential(activity),
            ))
        result.sort(key=lambda a: a.frequency, reverse=True)
        return result

    def _build_transitions(self, cases: dict[str, list[dict]]) -> dict[tuple[str, str], int]:
        """Build the directly-follows graph."""
        transitions: dict[tuple[str, str], int] = Counter()
        for case_events in cases.values():
            for i in range(len(case_events) - 1):
                edge = (case_events[i]["activity"], case_events[i + 1]["activity"])
                transitions[edge] += 1
        return dict(transitions)

    def _discover_variants(self, cases: dict[str, list[dict]]) -> list[ProcessVariant]:
        """Find distinct execution paths (variants)."""
        variant_counts: dict[tuple[str, ...], list[str]] = defaultdict(list)
        variant_durations: dict[tuple[str, ...], list[float]] = defaultdict(list)

        for case_id, case_events in cases.items():
            sequence = tuple(e["activity"] for e in case_events)
            variant_counts[sequence].append(case_id)
            if len(case_events) >= 2:
                duration = (case_events[-1]["timestamp"] - case_events[0]["timestamp"]).total_seconds()
                variant_durations[sequence].append(duration)

        total_cases = len(cases)
        variants = []
        for sequence, case_ids in variant_counts.items():
            durations = variant_durations.get(sequence, [0])
            variants.append(ProcessVariant(
                sequence=sequence,
                frequency=len(case_ids),
                avg_duration_seconds=sum(durations) / max(len(durations), 1),
                pct_of_total=(len(case_ids) / max(total_cases, 1)) * 100,
                sample_case_ids=case_ids[:5],
            ))
        variants.sort(key=lambda v: v.frequency, reverse=True)
        return variants

    def _detect_bottlenecks(
        self,
        cases: dict[str, list[dict]],
        activities: list[ActivityStats],
    ) -> list[Bottleneck]:
        """Identify activities with the highest waiting times."""
        bottlenecks = []
        for act in activities:
            if act.avg_waiting_time_seconds <= 0:
                continue
            total_wait = act.avg_waiting_time_seconds * act.frequency
            impact = total_wait / 3600  # hours
            bottlenecks.append(Bottleneck(
                activity=act.activity,
                avg_waiting_time_seconds=act.avg_waiting_time_seconds,
                total_waiting_time_hours=impact,
                frequency=act.frequency,
                impact_score=impact,
                description=self._describe_bottleneck(act),
            ))
        bottlenecks.sort(key=lambda b: b.impact_score, reverse=True)
        return bottlenecks[:10]

    def _describe_bottleneck(self, act: ActivityStats) -> str:
        wait_hours = act.avg_waiting_time_seconds / 3600
        if wait_hours > 24:
            severity = "critical"
        elif wait_hours > 8:
            severity = "high"
        elif wait_hours > 2:
            severity = "moderate"
        else:
            severity = "minor"
        return (
            f"{severity.capitalize()} bottleneck: '{act.activity}' has avg "
            f"{wait_hours:.1f}h waiting time across {act.frequency} executions"
        )

    def _identify_automation_candidates(
        self,
        activities: list[ActivityStats],
        variants: list[ProcessVariant],
        hourly_cost: float,
    ) -> list[AutomationCandidate]:
        """Identify high-value automation opportunities."""
        candidates = []

        # Single high-frequency, high-automatability activities
        for act in activities[:15]:
            if act.automation_score < 0.5:
                continue
            annual_executions = act.frequency * 12  # assume 1 month of data -> annual
            hours_per_execution = act.avg_duration_seconds / 3600
            hours_saved = annual_executions * hours_per_execution * 0.7  # 70% time reduction

            candidates.append(AutomationCandidate(
                name=f"Automate: {act.activity}",
                activities=[act.activity],
                frequency=act.frequency,
                avg_duration_seconds=act.avg_duration_seconds,
                annual_executions=annual_executions,
                estimated_hours_saved=hours_saved,
                automation_score=act.automation_score,
                rationale=(
                    f"Activity '{act.activity}' runs {act.frequency} times with "
                    f"{hours_per_execution:.1f}h avg duration. High-volume, "
                    f"structured activity — strong automation candidate."
                ),
            ))

        # Common variant sequences (automate the whole flow)
        for variant in variants[:5]:
            if variant.pct_of_total < 15:
                continue
            # Score: average automation potential across activities in sequence
            seq_scores = []
            act_map = {a.activity: a for a in activities}
            for a_name in variant.sequence:
                if a_name in act_map:
                    seq_scores.append(act_map[a_name].automation_score)
            if not seq_scores:
                continue
            avg_score = sum(seq_scores) / len(seq_scores)
            if avg_score < 0.5:
                continue

            annual_executions = variant.frequency * 12
            hours_saved = annual_executions * (variant.avg_duration_seconds / 3600) * 0.5

            candidates.append(AutomationCandidate(
                name=f"Automate variant: {' → '.join(list(variant.sequence)[:3])}...",
                activities=list(variant.sequence),
                frequency=variant.frequency,
                avg_duration_seconds=variant.avg_duration_seconds,
                annual_executions=annual_executions,
                estimated_hours_saved=hours_saved,
                automation_score=avg_score,
                rationale=(
                    f"This variant represents {variant.pct_of_total:.1f}% of all cases. "
                    f"End-to-end automation could save {hours_saved:.0f} hours/year."
                ),
            ))

        candidates.sort(key=lambda c: c.estimated_hours_saved, reverse=True)
        return candidates[:10]

    def _score_automation_potential(self, activity: str) -> float:
        """Heuristic — score an activity's automation potential from its name."""
        name = activity.lower()
        auto_hits = sum(1 for kw in self.AUTOMATION_KEYWORDS if kw in name)
        human_hits = sum(1 for kw in self.HUMAN_KEYWORDS if kw in name)

        base_score = 0.50
        score = base_score + 0.15 * auto_hits - 0.20 * human_hits
        return max(0.0, min(1.0, score))

    @staticmethod
    def _compute_fitness(variants: list[ProcessVariant]) -> float:
        """
        Fitness = concentration of traces in dominant variants.
        High fitness = few dominant paths (standardized process).
        Low fitness = many variants (chaotic process).
        """
        if not variants:
            return 0.0
        top_5_pct = sum(v.pct_of_total for v in variants[:5])
        return min(top_5_pct / 100.0, 1.0)
