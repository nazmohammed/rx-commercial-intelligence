"""Parse RX-Analyst markdown response into structured sections for Adaptive Cards."""

import re


def parse_analyst_response(response: str) -> dict:
    """Parse the analyst's structured markdown into card-ready sections.

    Expected format from Analyst:
        ### 📊 Summary
        ...text...
        ### 📈 Key Findings
        - bullet
        - bullet
        ### ⚠️ Flags
        - bullet
        ### 💡 Recommendation
        ...text...

    Returns dict with keys: summary, findings, flags, recommendation.
    """
    sections = _split_sections(response)

    summary = sections.get("summary", "").strip()
    findings = _extract_bullets(sections.get("findings", ""))
    flags = _extract_bullets(sections.get("flags", ""))
    recommendation = sections.get("recommendation", "").strip()

    # Fallback: if no structured sections found, treat whole response as summary
    if not summary and not findings:
        summary = response[:500].strip()

    return {
        "summary": summary or "Analysis complete.",
        "findings": findings or ["See summary above."],
        "flags": flags if flags else None,
        "recommendation": recommendation if recommendation else None,
    }


def _split_sections(text: str) -> dict:
    """Split markdown by ### headers into named sections."""
    sections = {}
    current_key = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        header_match = re.match(r"^###?\s*[📊📈⚠️💡]*\s*(.+)", line)
        if header_match:
            if current_key:
                sections[current_key] = "\n".join(current_lines)
            raw_key = header_match.group(1).strip().lower()
            # Normalize header to section key
            if "summary" in raw_key:
                current_key = "summary"
            elif "finding" in raw_key:
                current_key = "findings"
            elif "flag" in raw_key:
                current_key = "flags"
            elif "recommend" in raw_key:
                current_key = "recommendation"
            else:
                current_key = raw_key
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines)

    return sections


def _extract_bullets(text: str) -> list[str]:
    """Extract bullet points from text (lines starting with - or *)."""
    bullets = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "• ")):
            bullets.append(stripped[2:].strip())
        elif stripped.startswith(("– ")):
            bullets.append(stripped[2:].strip())
    return bullets
