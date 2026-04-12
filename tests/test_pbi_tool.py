"""Tests for PBI executeQueries tool."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.tools.pbi_execute_query import execute_dax_query


@pytest.fixture
def mock_token():
    with patch("src.tools.pbi_execute_query.get_pbi_access_token", return_value="mock-token"):
        yield


@pytest.fixture
def sample_pbi_response():
    with open("tests/fixtures/sample_dax_responses.json") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_execute_dax_success(mock_token, sample_pbi_response):
    """Successful DAX execution returns flattened rows."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sample_pbi_response

    with patch("src.tools.pbi_execute_query.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        result = await execute_dax_query(
            "EVALUATE SUMMARIZECOLUMNS('Dim Routes'[Route Pair], \"Revenue\", [Total Revenue])"
        )

    assert result["success"] is True
    assert result["row_count"] == 5
    assert len(result["tables"]) == 5
    assert result["tables"][0]["[Route Pair]"] == "RUH-LHR"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_execute_dax_auth_failure():
    """Auth failure returns structured error."""
    with patch(
        "src.tools.pbi_execute_query.get_pbi_access_token",
        side_effect=RuntimeError("MSAL failed"),
    ):
        result = await execute_dax_query("EVALUATE VALUES('Dim Routes')")

    assert result["success"] is False
    assert "Authentication failed" in result["error"]
    assert result["row_count"] == 0


@pytest.mark.asyncio
async def test_execute_dax_api_error(mock_token):
    """PBI API 400 error returns structured error."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad DAX syntax"

    with patch("src.tools.pbi_execute_query.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        result = await execute_dax_query("EVALUATE BAD QUERY")

    assert result["success"] is False
    assert "400" in result["error"]


@pytest.mark.asyncio
async def test_execute_dax_timeout(mock_token):
    """Timeout returns user-friendly error."""
    import httpx

    with patch("src.tools.pbi_execute_query.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        result = await execute_dax_query("EVALUATE LONG_RUNNING_QUERY")

    assert result["success"] is False
    assert "timed out" in result["error"].lower()
