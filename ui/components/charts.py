"""Reusable chart components for the DelValue AI UI."""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go
import plotly.express as px


def score_radar_chart(
    feasibility: float,
    value: float,
    risk: float,
    complexity: float,
    confidence: float,
    title: str = "Score Breakdown",
) -> go.Figure:
    """Spider/radar chart for multi-dimensional scoring."""
    categories = ["Feasibility", "Value", "Risk (inv)", "Simplicity", "Confidence"]
    values = [feasibility, value, 1 - risk, 1 - complexity, confidence]
    values.append(values[0])  # close the polygon
    categories.append(categories[0])

    fig = go.Figure(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(59, 130, 246, 0.15)",
        line=dict(color="rgb(59, 130, 246)", width=2),
        name="Score",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title=title,
        height=350,
        margin=dict(l=60, r=60, t=40, b=40),
        showlegend=False,
    )
    return fig


def roi_distribution_chart(histogram_data: dict, title: str = "ROI Distribution") -> go.Figure:
    """Histogram of Monte Carlo ROI simulation results."""
    bin_centers = histogram_data.get("bin_centers", [])
    counts = histogram_data.get("counts", [])

    colors = ["#ef4444" if c < 0 else "#22c55e" for c in bin_centers]

    fig = go.Figure(go.Bar(
        x=bin_centers,
        y=counts,
        marker_color=colors,
        opacity=0.8,
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
    fig.update_layout(
        title=title,
        xaxis_title="ROI (%)",
        yaxis_title="Frequency",
        height=350,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def portfolio_scatter(opportunities: list[dict]) -> go.Figure:
    """Value vs feasibility bubble chart (bubble size = savings)."""
    if not opportunities:
        return go.Figure().update_layout(title="No data")

    names = [o.get("name", "?")[:30] for o in opportunities]
    feasibility = [o["prediction"]["feasibility_score"] for o in opportunities]
    value = [o["prediction"]["value_score"] for o in opportunities]
    risk = [o["prediction"]["risk_score"] for o in opportunities]
    savings = [max(o["prediction"]["estimated_annual_savings"], 1000) for o in opportunities]
    recs = [o["prediction"]["recommendation"] for o in opportunities]

    color_map = {
        "automate_now": "#22c55e",
        "strong_candidate": "#3b82f6",
        "investigate_further": "#f59e0b",
        "defer": "#f97316",
        "not_recommended": "#ef4444",
    }
    colors = [color_map.get(r, "#94a3b8") for r in recs]

    fig = go.Figure(go.Scatter(
        x=feasibility,
        y=value,
        mode="markers+text",
        text=names,
        textposition="top center",
        textfont=dict(size=9),
        marker=dict(
            size=[max(s / 10000, 10) for s in savings],
            sizemode="area",
            sizeref=2,
            color=colors,
            opacity=0.7,
            line=dict(width=1, color="white"),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Feasibility: %{x:.2f}<br>"
            "Value: %{y:.2f}<br>"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="Portfolio Map — Value vs Feasibility",
        xaxis_title="Feasibility Score",
        yaxis_title="Value Score",
        height=450,
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1]),
    )
    return fig


def benchmark_bullet_chart(
    process_value: float,
    p25: float,
    p50: float,
    p75: float,
    metric_name: str = "ROI",
    unit: str = "%",
) -> go.Figure:
    """Bullet chart showing process position vs industry benchmarks."""
    fig = go.Figure()

    # Background ranges
    fig.add_trace(go.Bar(
        x=[p75], y=[metric_name], orientation="h",
        marker=dict(color="#e5e7eb"), width=0.5, showlegend=False,
    ))
    fig.add_trace(go.Bar(
        x=[p50], y=[metric_name], orientation="h",
        marker=dict(color="#d1d5db"), width=0.5, showlegend=False,
    ))
    fig.add_trace(go.Bar(
        x=[p25], y=[metric_name], orientation="h",
        marker=dict(color="#9ca3af"), width=0.5, showlegend=False,
    ))

    # Process marker
    fig.add_trace(go.Scatter(
        x=[process_value], y=[metric_name],
        mode="markers",
        marker=dict(
            size=16,
            color="#3b82f6" if process_value >= p50 else "#ef4444",
            symbol="diamond",
        ),
        name=f"Your process ({process_value:.0f}{unit})",
    ))

    fig.update_layout(
        barmode="overlay",
        height=120,
        margin=dict(l=20, r=20, t=10, b=10),
        xaxis_title=f"{metric_name} ({unit})",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def savings_waterfall(processes: list[dict]) -> go.Figure:
    """Waterfall chart of cumulative savings."""
    if not processes:
        return go.Figure()

    sorted_procs = sorted(processes, key=lambda p: p.get("estimated_savings", 0), reverse=True)[:10]
    names = [p.get("name", "?")[:20] for p in sorted_procs]
    savings = [p.get("estimated_savings", 0) for p in sorted_procs]

    fig = go.Figure(go.Waterfall(
        name="Savings",
        orientation="v",
        x=names,
        y=savings,
        connector=dict(line=dict(color="rgb(63, 63, 63)")),
        increasing=dict(marker=dict(color="#22c55e")),
        totals=dict(marker=dict(color="#3b82f6")),
    ))
    fig.update_layout(
        title="Annual Savings by Process",
        yaxis_title="Annual Savings ($)",
        height=400,
        margin=dict(l=40, r=20, t=40, b=80),
    )
    return fig


def trend_line_chart(
    x_values: list,
    y_values: list,
    title: str = "",
    y_label: str = "",
) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=x_values,
        y=y_values,
        mode="lines+markers",
        line=dict(color="#3b82f6", width=2),
        marker=dict(size=6),
    ))
    fig.update_layout(
        title=title,
        yaxis_title=y_label,
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig
