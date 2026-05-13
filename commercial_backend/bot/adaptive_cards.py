"""Adaptive Card templates for Teams responses."""

import json


def build_insight_card(
    question: str,
    summary: str,
    findings: list[str],
    flags: list[str] | None = None,
    recommendation: str | None = None,
    dax: str | None = None,
) -> dict:
    """Build an Adaptive Card payload for a commercial insight response."""

    body: list[dict] = [
        {
            "type": "TextBlock",
            "text": "📊 RX Commercial Intelligence",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": question,
            "wrap": True,
            "isSubtle": True,
            "size": "Small",
        },
        {"type": "TextBlock", "text": "---", "spacing": "Small"},
        # Summary
        {
            "type": "TextBlock",
            "text": summary,
            "wrap": True,
            "weight": "Bolder",
        },
    ]

    # Key Findings
    if findings:
        body.append({
            "type": "TextBlock",
            "text": "📈 Key Findings",
            "weight": "Bolder",
            "spacing": "Medium",
        })
        for f in findings:
            body.append({
                "type": "TextBlock",
                "text": f"• {f}",
                "wrap": True,
                "spacing": "None",
            })

    # Flags
    if flags:
        body.append({
            "type": "TextBlock",
            "text": "⚠️ Flags",
            "weight": "Bolder",
            "spacing": "Medium",
            "color": "Warning",
        })
        for flag in flags:
            body.append({
                "type": "TextBlock",
                "text": f"• {flag}",
                "wrap": True,
                "spacing": "None",
                "color": "Warning",
            })

    # Recommendation
    if recommendation:
        body.append({
            "type": "TextBlock",
            "text": "💡 Recommendation",
            "weight": "Bolder",
            "spacing": "Medium",
        })
        body.append({
            "type": "TextBlock",
            "text": recommendation,
            "wrap": True,
        })

    # Collapsible DAX (for transparency)
    if dax:
        body.append({
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.ToggleVisibility",
                    "title": "Show DAX Query",
                    "targetElements": ["daxBlock"],
                }
            ],
        })
        body.append({
            "type": "TextBlock",
            "id": "daxBlock",
            "text": f"```\n{dax}\n```",
            "wrap": True,
            "fontType": "Monospace",
            "size": "Small",
            "isVisible": False,
        })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
    }


def build_greeting_card() -> dict:
    """Friendly introduction shown when the user sends a greeting."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": "👋 Hi! I'm your RX Insights Companion",
                "weight": "Bolder",
                "size": "Large",
                "color": "Accent",
            },
            {
                "type": "TextBlock",
                "text": "Your Commercial Intelligence & Guest Experience assistant for Riyadh Air.",
                "wrap": True,
                "spacing": "Small",
            },
            {
                "type": "TextBlock",
                "text": "📊 Commercial Intelligence",
                "weight": "Bolder",
                "spacing": "Medium",
            },
            {
                "type": "TextBlock",
                "text": "• Revenue & sales by channel (Website, App, indirect)\n• Ancillary revenue and per-passenger metrics\n• Load factor and yield by route\n• Booking trends — daily, monthly, year-on-year\n• Business vs economy class performance",
                "wrap": True,
                "spacing": "None",
            },
            {
                "type": "TextBlock",
                "text": "🌟 Guest Experience",
                "weight": "Bolder",
                "spacing": "Medium",
            },
            {
                "type": "TextBlock",
                "text": "• Guest Satisfaction Score (CSAT) by route and cabin — vs last year\n• Survey response rate and total survey volume\n• Sentiment analysis on guest reviews (positive / negative / neutral)\n• Journey stage breakdown: lounge, cabin crew, boarding, dining & more\n• Attribute-level scores (e.g. crew friendliness, lounge comfort, check-in efficiency)",
                "wrap": True,
                "spacing": "None",
            },
            {
                "type": "TextBlock",
                "text": "How can I help you today?",
                "wrap": True,
                "weight": "Bolder",
                "spacing": "Medium",
            },
        ],
    }


def build_error_card(message: str, debug_info: dict | None = None) -> dict:
    """Build an Adaptive Card for error states."""
    body: list[dict] = [
        {
            "type": "TextBlock",
            "text": "❌ Something went wrong",
            "weight": "Bolder",
            "color": "Attention",
        },
        {
            "type": "TextBlock",
            "text": message,
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "Try rephrasing your question or contact the Cx Insights team.",
            "isSubtle": True,
            "size": "Small",
        },
    ]

    # [DEBUG] collapsible traceback block — only present when debug_info is passed
    if debug_info:
        body.append({
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.ToggleVisibility",
                    "title": "Show Debug Details",
                    "targetElements": ["debugBlock"],
                }
            ],
        })
        body.append({
            "type": "TextBlock",
            "id": "debugBlock",
            "text": f"Step: {debug_info.get('error_type', '')}\n\n{debug_info.get('traceback', '')}",
            "wrap": True,
            "fontType": "Monospace",
            "size": "Small",
            "isVisible": False,
            "color": "Attention",
        })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
    }


def build_thinking_card() -> dict:
    """Build a 'thinking' card shown while agents are processing."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": "🔍 Analyzing your question...",
                "weight": "Bolder",
            },
            {
                "type": "TextBlock",
                "text": "Generating DAX → Querying Power BI → Interpreting results",
                "isSubtle": True,
                "size": "Small",
            },
        ],
    }
