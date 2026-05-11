"""RX-GX-Analyst — Foundry prompt agent configuration."""

AGENT_CONFIG = {
    "name": "RX-GX-Analyst",
    "model": "gpt-5.4-mini",
    "description": (
        "Interprets Power BI results from the RX Guest Experience model and "
        "writes a concise executive narrative (CSAT, sentiment, response rate, "
        "route/cabin breakdowns) for senior Customer / Cabin Experience leaders."
    ),
    "tools": [],
}
