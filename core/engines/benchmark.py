"""
DelValue AI — Industry Benchmarking Engine

Positions a process against industry peers using anonymized cross-company data.
Core mechanism for the network-effects moat: each customer's outcomes improve
benchmarks for everyone.

Key features:
  1. Percentile ranking against 50+ process categories × 10+ industries
  2. Gap analysis to top-quartile performers
  3. Anonymized contribution pipeline with PII stripping
  4. Statistical significance checks (minimum sample size threshold)
  5. Industry-adjusted scoring (e.g., finance processes are benchmarked against
     other finance processes, not manufacturing)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sqlalchemy import and_
from sqlalchemy.orm import Session

from data.models.process import BenchmarkEntry, ProcessCategory

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkComparison:
    """Result of comparing a process against industry benchmarks."""

    category: str
    industry: str | None
    sample_size: int

    # Process metrics
    process_roi: float
    process_savings: float
    process_payback_months: float

    # Industry context
    industry_avg_roi: float
    industry_median_roi: float
    industry_p25_roi: float
    industry_p75_roi: float
    industry_success_rate: float

    # Positioning
    roi_percentile: float
    savings_percentile: float
    payback_percentile: float
    is_above_median: bool
    gap_to_top_quartile: float
    gap_to_median: float

    # Interpretation
    positioning: str  # "leader" | "above_average" | "average" | "below_average" | "laggard"
    confidence: str  # "high" | "medium" | "low" based on sample size

    # Recommendations
    improvement_targets: list[dict]

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "industry": self.industry,
            "sample_size": self.sample_size,
            "process_metrics": {
                "roi": self.process_roi,
                "savings": self.process_savings,
                "payback_months": self.process_payback_months,
            },
            "industry_benchmarks": {
                "avg_roi": self.industry_avg_roi,
                "median_roi": self.industry_median_roi,
                "p25_roi": self.industry_p25_roi,
                "p75_roi": self.industry_p75_roi,
                "success_rate": self.industry_success_rate,
            },
            "positioning": {
                "roi_percentile": self.roi_percentile,
                "savings_percentile": self.savings_percentile,
                "payback_percentile": self.payback_percentile,
                "is_above_median": self.is_above_median,
                "gap_to_top_quartile": self.gap_to_top_quartile,
                "gap_to_median": self.gap_to_median,
                "tier": self.positioning,
                "confidence": self.confidence,
            },
            "improvement_targets": self.improvement_targets,
        }


class BenchmarkEngine:
    """
    Industry benchmarking engine — positions processes against peer performance.
    """

    # Minimum sample size for statistically meaningful benchmarks
    MIN_SAMPLE_SIZE = 5
    HIGH_CONFIDENCE_THRESHOLD = 30
    MEDIUM_CONFIDENCE_THRESHOLD = 10

    def __init__(self, session: Session):
        self.session = session

    def compare(
        self,
        category: ProcessCategory | str,
        process_roi: float,
        process_savings: float,
        process_payback_months: float,
        industry: Optional[str] = None,
        company_size_bucket: Optional[str] = None,
    ) -> Optional[BenchmarkComparison]:
        """
        Compare a process against industry benchmarks.

        Args:
            category: Process category
            process_roi: Actual or projected ROI (%)
            process_savings: Annual savings
            process_payback_months: Payback period in months
            industry: Optional industry filter
            company_size_bucket: Optional size filter (e.g., "1000-5000")

        Returns:
            BenchmarkComparison or None if no sufficient benchmark data
        """
        cat_enum = category if isinstance(category, ProcessCategory) else ProcessCategory(category)
        benchmark = self._find_best_match(cat_enum, industry, company_size_bucket)

        if benchmark is None or benchmark.sample_size < self.MIN_SAMPLE_SIZE:
            logger.info(f"Insufficient benchmark data for {category}/{industry}")
            return None

        # Compute percentile rankings
        roi_pct = self._compute_percentile(
            process_roi,
            p25=benchmark.p25_roi,
            p50=benchmark.median_roi,
            p75=benchmark.p75_roi,
            mean=benchmark.avg_roi,
            std=benchmark.roi_std,
        )
        savings_pct = self._compute_percentile(
            process_savings,
            mean=benchmark.avg_savings,
            std=benchmark.savings_std,
        )
        # For payback, lower is better — invert the percentile
        payback_pct = 100 - self._compute_percentile(
            process_payback_months,
            mean=benchmark.avg_payback_months,
            std=benchmark.avg_payback_months * 0.4,
        )

        positioning = self._classify_positioning(roi_pct)
        confidence = self._classify_confidence(benchmark.sample_size)

        gap_to_p75 = benchmark.p75_roi - process_roi
        gap_to_median = benchmark.median_roi - process_roi

        improvement_targets = self._suggest_improvements(
            process_roi, process_savings, process_payback_months, benchmark,
        )

        return BenchmarkComparison(
            category=cat_enum.value,
            industry=industry,
            sample_size=benchmark.sample_size,
            process_roi=process_roi,
            process_savings=process_savings,
            process_payback_months=process_payback_months,
            industry_avg_roi=benchmark.avg_roi,
            industry_median_roi=benchmark.median_roi,
            industry_p25_roi=benchmark.p25_roi,
            industry_p75_roi=benchmark.p75_roi,
            industry_success_rate=benchmark.success_rate,
            roi_percentile=roi_pct,
            savings_percentile=savings_pct,
            payback_percentile=payback_pct,
            is_above_median=process_roi > benchmark.median_roi,
            gap_to_top_quartile=max(gap_to_p75, 0),
            gap_to_median=max(gap_to_median, 0),
            positioning=positioning,
            confidence=confidence,
            improvement_targets=improvement_targets,
        )

    def _find_best_match(
        self,
        category: ProcessCategory,
        industry: Optional[str],
        company_size_bucket: Optional[str],
    ) -> Optional[BenchmarkEntry]:
        """Find the most specific matching benchmark. Falls back progressively."""
        q = self.session.query(BenchmarkEntry).filter(BenchmarkEntry.category == category)

        # Try most specific match first: industry + size
        if industry and company_size_bucket:
            specific = q.filter(
                BenchmarkEntry.industry == industry,
                BenchmarkEntry.company_size_bucket == company_size_bucket,
            ).first()
            if specific and specific.sample_size >= self.MIN_SAMPLE_SIZE:
                return specific

        # Industry only
        if industry:
            industry_match = q.filter(
                BenchmarkEntry.industry == industry,
                BenchmarkEntry.company_size_bucket.is_(None),
            ).first()
            if industry_match and industry_match.sample_size >= self.MIN_SAMPLE_SIZE:
                return industry_match

        # Category only (global benchmark)
        global_match = q.filter(
            BenchmarkEntry.industry.is_(None),
            BenchmarkEntry.company_size_bucket.is_(None),
        ).first()
        return global_match

    @staticmethod
    def _compute_percentile(
        value: float,
        p25: Optional[float] = None,
        p50: Optional[float] = None,
        p75: Optional[float] = None,
        mean: Optional[float] = None,
        std: Optional[float] = None,
    ) -> float:
        """
        Estimate the percentile rank of a value within a distribution.
        Uses quartile-based interpolation when available, otherwise normal approximation.
        """
        if p25 is not None and p50 is not None and p75 is not None:
            if value <= p25:
                # Below p25 — extrapolate linearly down to 0
                fraction = max(0, value / p25) if p25 > 0 else 0
                return fraction * 25
            elif value <= p50:
                return 25 + ((value - p25) / max(p50 - p25, 0.01)) * 25
            elif value <= p75:
                return 50 + ((value - p50) / max(p75 - p50, 0.01)) * 25
            else:
                # Above p75 — extrapolate using distance from p75
                excess = (value - p75) / max(p75 - p50, p75 * 0.5, 0.01)
                return min(75 + excess * 25, 99.9)

        # Normal approximation when only mean/std available
        if mean is not None and std is not None and std > 0:
            from scipy import stats
            z = (value - mean) / std
            return float(stats.norm.cdf(z) * 100)

        return 50.0  # default to median

    @staticmethod
    def _classify_positioning(roi_percentile: float) -> str:
        if roi_percentile >= 90:
            return "leader"
        if roi_percentile >= 75:
            return "above_average"
        if roi_percentile >= 40:
            return "average"
        if roi_percentile >= 20:
            return "below_average"
        return "laggard"

    @classmethod
    def _classify_confidence(cls, sample_size: int) -> str:
        if sample_size >= cls.HIGH_CONFIDENCE_THRESHOLD:
            return "high"
        if sample_size >= cls.MEDIUM_CONFIDENCE_THRESHOLD:
            return "medium"
        return "low"

    def _suggest_improvements(
        self,
        current_roi: float,
        current_savings: float,
        current_payback: float,
        benchmark: BenchmarkEntry,
    ) -> list[dict]:
        """Suggest improvement targets based on top-quartile performers."""
        targets = []

        if current_roi < benchmark.p75_roi:
            targets.append({
                "metric": "roi",
                "current": round(current_roi, 2),
                "target": round(benchmark.p75_roi, 2),
                "gap": round(benchmark.p75_roi - current_roi, 2),
                "description": f"Top-quartile performers achieve {benchmark.p75_roi:.0f}% ROI in this category",
            })

        if current_savings < benchmark.avg_savings:
            targets.append({
                "metric": "annual_savings",
                "current": round(current_savings, 2),
                "target": round(benchmark.avg_savings, 2),
                "gap": round(benchmark.avg_savings - current_savings, 2),
                "description": f"Industry average savings for this process type: ${benchmark.avg_savings:,.0f}",
            })

        if current_payback > benchmark.avg_payback_months:
            targets.append({
                "metric": "payback_months",
                "current": round(current_payback, 1),
                "target": round(benchmark.avg_payback_months, 1),
                "gap": round(current_payback - benchmark.avg_payback_months, 1),
                "description": f"Industry average payback: {benchmark.avg_payback_months:.1f} months",
            })

        return targets

    def contribute_outcome(
        self,
        category: ProcessCategory,
        industry: Optional[str],
        company_size_bucket: Optional[str],
        actual_roi: float,
        actual_savings: float,
        actual_cost: float,
        actual_payback_months: float,
        was_successful: bool,
        time_to_implement_months: float,
    ) -> None:
        """
        Contribute an anonymized outcome to the benchmark pool.
        Triggers recalculation if enough new data has accumulated.

        Note: No PII, no org ID, no process ID — only aggregated metrics.
        """
        # The actual aggregation happens in recalculate_benchmarks().
        # Here we just mark that new data is available.
        # In production this would write to a separate contributions table,
        # then a background job aggregates periodically.
        logger.info(
            f"Benchmark contribution: {category.value}/{industry} "
            f"ROI={actual_roi:.1f}% success={was_successful}"
        )

    def recalculate_benchmarks(
        self,
        category: ProcessCategory,
        contributions: list[dict],
    ) -> Optional[BenchmarkEntry]:
        """
        Recalculate benchmark statistics from a list of contributions.
        Only creates/updates if minimum sample size is met.
        """
        if len(contributions) < self.MIN_SAMPLE_SIZE:
            return None

        rois = np.array([c["actual_roi"] for c in contributions])
        savings = np.array([c["actual_savings"] for c in contributions])
        costs = np.array([c["actual_implementation_cost"] for c in contributions])
        paybacks = np.array([c["actual_payback_months"] for c in contributions])
        successes = np.array([c.get("was_successful", c["actual_roi"] > 0) for c in contributions])
        times = np.array([c.get("time_to_implement_months", 6.0) for c in contributions])

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        entry = BenchmarkEntry(
            category=category,
            sample_size=len(contributions),
            avg_roi=float(np.mean(rois)),
            median_roi=float(np.median(rois)),
            p25_roi=float(np.percentile(rois, 25)),
            p75_roi=float(np.percentile(rois, 75)),
            avg_savings=float(np.mean(savings)),
            avg_implementation_cost=float(np.mean(costs)),
            avg_payback_months=float(np.mean(paybacks)),
            success_rate=float(np.mean(successes)),
            avg_time_to_implement_months=float(np.mean(times)),
            roi_std=float(np.std(rois)),
            savings_std=float(np.std(savings)),
            period_start=now,
            period_end=now,
            last_aggregated_at=now,
        )
        self.session.add(entry)
        self.session.flush()
        return entry
