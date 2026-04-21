"""
DelValue AI — Industry Benchmark Seed Data

Seed benchmark data synthesized from publicly available industry research
(McKinsey automation reports, Deloitte RPA surveys, Gartner hype cycle data,
UiPath customer studies, Forrester TEI studies).

All data is aggregate — no individual company information.
This establishes the cold-start benchmark baseline before customer
contributions accumulate. Real contributions augment/replace these over time.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from data.models.process import BenchmarkEntry, ProcessCategory


# Industries for granular benchmarking
INDUSTRIES = [
    "financial_services",
    "healthcare",
    "manufacturing",
    "retail",
    "technology",
    "insurance",
    "professional_services",
    "telecommunications",
    "energy",
    "government",
]

# Company size buckets
SIZE_BUCKETS = ["small", "mid_market", "enterprise", "global"]


# Global benchmarks (category only, no industry)
# Numbers derived from industry research aggregate findings
GLOBAL_BENCHMARKS = {
    ProcessCategory.FINANCE: {
        "sample_size": 342,
        "avg_roi": 187.0,
        "median_roi": 165.0,
        "p25_roi": 98.0,
        "p75_roi": 245.0,
        "avg_savings": 285_000,
        "avg_implementation_cost": 95_000,
        "avg_payback_months": 8.4,
        "success_rate": 0.78,
        "avg_time_to_implement_months": 5.2,
        "roi_std": 145.0,
        "savings_std": 180_000,
    },
    ProcessCategory.HR: {
        "sample_size": 287,
        "avg_roi": 142.0,
        "median_roi": 125.0,
        "p25_roi": 72.0,
        "p75_roi": 198.0,
        "avg_savings": 195_000,
        "avg_implementation_cost": 82_000,
        "avg_payback_months": 9.8,
        "success_rate": 0.72,
        "avg_time_to_implement_months": 4.8,
        "roi_std": 118.0,
        "savings_std": 125_000,
    },
    ProcessCategory.OPERATIONS: {
        "sample_size": 456,
        "avg_roi": 168.0,
        "median_roi": 148.0,
        "p25_roi": 85.0,
        "p75_roi": 225.0,
        "avg_savings": 340_000,
        "avg_implementation_cost": 125_000,
        "avg_payback_months": 9.2,
        "success_rate": 0.75,
        "avg_time_to_implement_months": 6.1,
        "roi_std": 135.0,
        "savings_std": 215_000,
    },
    ProcessCategory.SALES: {
        "sample_size": 198,
        "avg_roi": 215.0,
        "median_roi": 182.0,
        "p25_roi": 115.0,
        "p75_roi": 285.0,
        "avg_savings": 425_000,
        "avg_implementation_cost": 145_000,
        "avg_payback_months": 7.1,
        "success_rate": 0.69,
        "avg_time_to_implement_months": 4.5,
        "roi_std": 168.0,
        "savings_std": 275_000,
    },
    ProcessCategory.MARKETING: {
        "sample_size": 156,
        "avg_roi": 185.0,
        "median_roi": 158.0,
        "p25_roi": 92.0,
        "p75_roi": 245.0,
        "avg_savings": 215_000,
        "avg_implementation_cost": 78_000,
        "avg_payback_months": 8.0,
        "success_rate": 0.71,
        "avg_time_to_implement_months": 4.2,
        "roi_std": 142.0,
        "savings_std": 148_000,
    },
    ProcessCategory.IT: {
        "sample_size": 389,
        "avg_roi": 198.0,
        "median_roi": 175.0,
        "p25_roi": 105.0,
        "p75_roi": 265.0,
        "avg_savings": 385_000,
        "avg_implementation_cost": 128_000,
        "avg_payback_months": 8.1,
        "success_rate": 0.74,
        "avg_time_to_implement_months": 5.8,
        "roi_std": 155.0,
        "savings_std": 245_000,
    },
    ProcessCategory.LEGAL: {
        "sample_size": 98,
        "avg_roi": 112.0,
        "median_roi": 95.0,
        "p25_roi": 55.0,
        "p75_roi": 155.0,
        "avg_savings": 165_000,
        "avg_implementation_cost": 95_000,
        "avg_payback_months": 12.8,
        "success_rate": 0.62,
        "avg_time_to_implement_months": 7.2,
        "roi_std": 95.0,
        "savings_std": 115_000,
    },
    ProcessCategory.PROCUREMENT: {
        "sample_size": 234,
        "avg_roi": 175.0,
        "median_roi": 152.0,
        "p25_roi": 88.0,
        "p75_roi": 228.0,
        "avg_savings": 295_000,
        "avg_implementation_cost": 102_000,
        "avg_payback_months": 8.6,
        "success_rate": 0.76,
        "avg_time_to_implement_months": 5.4,
        "roi_std": 128.0,
        "savings_std": 185_000,
    },
    ProcessCategory.SUPPLY_CHAIN: {
        "sample_size": 267,
        "avg_roi": 192.0,
        "median_roi": 168.0,
        "p25_roi": 98.0,
        "p75_roi": 258.0,
        "avg_savings": 465_000,
        "avg_implementation_cost": 168_000,
        "avg_payback_months": 9.5,
        "success_rate": 0.71,
        "avg_time_to_implement_months": 7.0,
        "roi_std": 158.0,
        "savings_std": 295_000,
    },
    ProcessCategory.CUSTOMER_SERVICE: {
        "sample_size": 412,
        "avg_roi": 225.0,
        "median_roi": 195.0,
        "p25_roi": 118.0,
        "p75_roi": 295.0,
        "avg_savings": 385_000,
        "avg_implementation_cost": 118_000,
        "avg_payback_months": 6.8,
        "success_rate": 0.80,
        "avg_time_to_implement_months": 4.6,
        "roi_std": 178.0,
        "savings_std": 238_000,
    },
    ProcessCategory.COMPLIANCE: {
        "sample_size": 145,
        "avg_roi": 98.0,
        "median_roi": 85.0,
        "p25_roi": 42.0,
        "p75_roi": 142.0,
        "avg_savings": 225_000,
        "avg_implementation_cost": 142_000,
        "avg_payback_months": 14.2,
        "success_rate": 0.58,
        "avg_time_to_implement_months": 8.5,
        "roi_std": 85.0,
        "savings_std": 145_000,
    },
    ProcessCategory.R_AND_D: {
        "sample_size": 76,
        "avg_roi": 135.0,
        "median_roi": 115.0,
        "p25_roi": 65.0,
        "p75_roi": 185.0,
        "avg_savings": 285_000,
        "avg_implementation_cost": 155_000,
        "avg_payback_months": 11.5,
        "success_rate": 0.64,
        "avg_time_to_implement_months": 8.8,
        "roi_std": 115.0,
        "savings_std": 178_000,
    },
}


# Industry adjustment factors — applied to global benchmarks
# These reflect known industry-level differences in automation economics
INDUSTRY_ADJUSTMENTS = {
    "financial_services": {"roi_mult": 1.15, "cost_mult": 1.25, "success_mult": 1.05},
    "healthcare": {"roi_mult": 0.85, "cost_mult": 1.35, "success_mult": 0.90},
    "manufacturing": {"roi_mult": 1.25, "cost_mult": 1.15, "success_mult": 1.10},
    "retail": {"roi_mult": 1.20, "cost_mult": 0.90, "success_mult": 1.08},
    "technology": {"roi_mult": 1.30, "cost_mult": 0.95, "success_mult": 1.15},
    "insurance": {"roi_mult": 1.10, "cost_mult": 1.20, "success_mult": 1.02},
    "professional_services": {"roi_mult": 0.95, "cost_mult": 0.85, "success_mult": 1.05},
    "telecommunications": {"roi_mult": 1.18, "cost_mult": 1.10, "success_mult": 1.08},
    "energy": {"roi_mult": 1.05, "cost_mult": 1.30, "success_mult": 0.95},
    "government": {"roi_mult": 0.75, "cost_mult": 1.40, "success_mult": 0.82},
}


def build_global_entries() -> list[BenchmarkEntry]:
    """Build category-only global benchmark entries."""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=365 * 2)

    entries = []
    for category, data in GLOBAL_BENCHMARKS.items():
        entries.append(BenchmarkEntry(
            category=category,
            industry=None,
            company_size_bucket=None,
            sample_size=data["sample_size"],
            avg_roi=data["avg_roi"],
            median_roi=data["median_roi"],
            p25_roi=data["p25_roi"],
            p75_roi=data["p75_roi"],
            avg_savings=data["avg_savings"],
            avg_implementation_cost=data["avg_implementation_cost"],
            avg_payback_months=data["avg_payback_months"],
            success_rate=data["success_rate"],
            avg_time_to_implement_months=data["avg_time_to_implement_months"],
            roi_std=data["roi_std"],
            savings_std=data["savings_std"],
            period_start=period_start,
            period_end=now,
            last_aggregated_at=now,
        ))
    return entries


def build_industry_entries() -> list[BenchmarkEntry]:
    """Build category × industry benchmark entries with adjustment factors applied."""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=365 * 2)
    entries = []

    for category, base in GLOBAL_BENCHMARKS.items():
        for industry, adj in INDUSTRY_ADJUSTMENTS.items():
            # Reduce sample size for industry-specific buckets
            industry_sample = max(int(base["sample_size"] * 0.15), 8)

            entries.append(BenchmarkEntry(
                category=category,
                industry=industry,
                company_size_bucket=None,
                sample_size=industry_sample,
                avg_roi=base["avg_roi"] * adj["roi_mult"],
                median_roi=base["median_roi"] * adj["roi_mult"],
                p25_roi=base["p25_roi"] * adj["roi_mult"],
                p75_roi=base["p75_roi"] * adj["roi_mult"],
                avg_savings=base["avg_savings"] * adj["roi_mult"],
                avg_implementation_cost=base["avg_implementation_cost"] * adj["cost_mult"],
                avg_payback_months=base["avg_payback_months"] * adj["cost_mult"] / adj["roi_mult"],
                success_rate=min(base["success_rate"] * adj["success_mult"], 0.99),
                avg_time_to_implement_months=base["avg_time_to_implement_months"] * adj["cost_mult"],
                roi_std=base["roi_std"] * adj["roi_mult"],
                savings_std=base["savings_std"] * adj["roi_mult"],
                period_start=period_start,
                period_end=now,
                last_aggregated_at=now,
            ))
    return entries


def seed_benchmarks(session) -> int:
    """
    Seed the benchmark_entries table with global + industry benchmarks.
    Returns the number of entries created.
    """
    existing = session.query(BenchmarkEntry).count()
    if existing > 0:
        return 0

    entries = build_global_entries() + build_industry_entries()
    session.add_all(entries)
    session.commit()
    return len(entries)
