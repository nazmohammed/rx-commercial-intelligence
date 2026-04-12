"""RX-Analyst — Foundry prompt agent configuration."""

AGENT_CONFIG = {
    "name": "RX-Analyst",
    "model": "gpt-5.4-mini",
    "description": (
        "Validates query results, interprets data in Riyadh Air commercial context, "
        "flags anomalies against KPI benchmarks, and provides actionable insights "
        "for senior leadership."
    ),
    "tools": [],
}
