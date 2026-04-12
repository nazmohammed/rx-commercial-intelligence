"""RX-QueryEngine — Foundry prompt agent configuration."""

AGENT_CONFIG = {
    "name": "RX-QueryEngine",
    "model": "gpt-5.4-mini",
    "description": (
        "Translates natural-language commercial questions into DAX queries, "
        "executes them against the Routes Insights Power BI semantic model, "
        "and returns raw tabular results."
    ),
    "tools": ["execute_dax_query"],
}
