"""Tests for RX-Coordinator routing logic."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.orchestrator.response_formatter import parse_analyst_response


class TestResponseFormatter:
    """Test parsing of analyst markdown into card sections."""

    def test_full_structured_response(self):
        response = """### 📊 Summary
JED-LHR load factor was 87% in Q1 2025.

### 📈 Key Findings
- Load factor of 87% is 12 points above network average of 75%
- Revenue grew 8% QoQ to SAR 28.5M
- Business class yield at SAR 0.45/RPK — 15% premium

### ⚠️ Flags
- Load factor above 85% suggests upgauging opportunity
- Economy yield declining 4% — monitor competitive pressure

### 💡 Recommendation
Consider upgauging JED-LHR from 787-9 to 787-10 for Q3 2025 summer peak.
"""
        result = parse_analyst_response(response)

        assert "87%" in result["summary"]
        assert len(result["findings"]) == 3
        assert len(result["flags"]) == 2
        assert "upgauging" in result["recommendation"]

    def test_no_flags_section(self):
        response = """### 📊 Summary
Revenue was SAR 45.2M.

### 📈 Key Findings
- Total revenue SAR 45.2M for Q1
- Top route: RUH-LHR with SAR 12.1M
"""
        result = parse_analyst_response(response)

        assert result["summary"]
        assert len(result["findings"]) == 2
        assert result["flags"] is None
        assert result["recommendation"] is None

    def test_unstructured_fallback(self):
        response = "The load factor on RUH-LHR was 82% in March 2025, which is healthy."
        result = parse_analyst_response(response)

        assert "82%" in result["summary"]
        assert result["findings"] == ["See summary above."]

    def test_empty_response(self):
        result = parse_analyst_response("")

        assert result["summary"] == "Analysis complete."
