"""RX-GX-QEngine — Foundry prompt agent configuration."""

AGENT_CONFIG = {
    "name": "RX-GX-QEngine",
    "model": "gpt-5.4-mini",
    "description": (
        "Translates natural-language guest experience questions into DAX queries "
        "against the RX Guest Experience Power BI semantic model "
        "(survey scores, sentiment, response rates, route/cabin breakdowns)."
    ),
    "tools": [],
}
