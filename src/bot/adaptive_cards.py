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


def build_error_card(message: str) -> dict:
    """Build an Adaptive Card for error states."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
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
        ],
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
