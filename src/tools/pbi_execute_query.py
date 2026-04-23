"""Execute DAX queries against Power BI REST API.

Called directly by the RX-Coordinator after it extracts DAX from the
RX-QueryEngine prompt agent's marker-delimited response. RLS is enforced
via the ``impersonatedUser`` API parameter when a Teams user's UPN is known.
"""

import json
import os
import httpx
import structlog

from src.tools.pbi_auth import get_pbi_access_token

logger = structlog.get_logger(__name__)

PBI_API_BASE = "https://api.powerbi.com/v1.0/myorg"


async def execute_dax_query(
    dax_query: str, user_principal_name: str | None = None
) -> dict:
    """Execute a DAX query against the configured Power BI dataset.

    Args:
        dax_query: A valid DAX query string (e.g. EVALUATE SUMMARIZECOLUMNS(...))
        user_principal_name: UPN (email) of the Teams user. When provided, the
            query is executed under PBI Row-Level Security for that user via
            the ``impersonatedUser`` API parameter.

    Returns:
        dict with keys:
            - success (bool)
            - tables (list[dict]): result rows from PBI
            - dax (str): the query that was executed
            - row_count (int): number of result rows
            - error (str | None): error message if failed
    """
    workspace_id = os.environ["PBI_WORKSPACE_ID"]
    dataset_id = os.environ["PBI_DATASET_ID"]

    url = f"{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"

    payload: dict = {
        "queries": [{"query": dax_query}],
        "serializerSettings": {"includeNulls": True},
    }

    # Enforce RLS — MI authenticates, but the query runs as the real user
    if user_principal_name:
        payload["impersonatedUser"] = {"username": user_principal_name}

    try:
        token = await get_pbi_access_token()
    except Exception as e:
        logger.error("pbi_auth_failed", error=str(e))
        return {
            "success": False,
            "tables": [],
            "dax": dax_query,
            "row_count": 0,
            "error": f"Authentication failed: {e}",
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            error_body = resp.text[:500]
            logger.error(
                "pbi_query_failed",
                status=resp.status_code,
                body=error_body,
                dax=dax_query[:200],
            )
            return {
                "success": False,
                "tables": [],
                "dax": dax_query,
                "row_count": 0,
                "error": f"PBI API {resp.status_code}: {error_body}",
            }

        data = resp.json()
        results = data.get("results", [])

        # Flatten PBI response: results[].tables[].rows[]
        all_rows = []
        for result in results:
            for table in result.get("tables", []):
                all_rows.extend(table.get("rows", []))

        logger.info(
            "pbi_query_success",
            row_count=len(all_rows),
            dax_length=len(dax_query),
        )

        return {
            "success": True,
            "tables": all_rows,
            "dax": dax_query,
            "row_count": len(all_rows),
            "error": None,
        }

    except httpx.TimeoutException:
        logger.error("pbi_query_timeout", dax=dax_query[:200])
        return {
            "success": False,
            "tables": [],
            "dax": dax_query,
            "row_count": 0,
            "error": "Query timed out after 60s — simplify the DAX or reduce the date range.",
        }
    except Exception as e:
        logger.error("pbi_query_exception", error=str(e), dax=dax_query[:200])
        return {
            "success": False,
            "tables": [],
            "dax": dax_query,
            "row_count": 0,
            "error": str(e),
        }


# -- Function-tool schema (LEGACY / RESERVED) --
#
# Foundry **Prompt Agents** do not support function tools. RX-QueryEngine is a
# Prompt Agent, so this definition is not currently used: the Coordinator
# extracts DAX from the agent's marker-delimited text response and calls
# ``execute_dax_query`` directly.
#
# This schema is kept for a potential future migration to a **Hosted Agent**,
# where function-tool calling *is* supported. Do not register it against any
# Prompt Agent — the run will fail.
EXECUTE_DAX_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "execute_dax_query",
        "description": (
            "Execute a DAX query against the Riyadh Air 'Routes Insights - Flyr' "
            "Power BI semantic model and return the tabular result. "
            "Use EVALUATE with SUMMARIZECOLUMNS, CALCULATETABLE, or TOPN. "
            "Always include relevant filters (date range, route, cabin class) "
            "to avoid full-table scans."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dax_query": {
                    "type": "string",
                    "description": (
                        "A valid DAX query. Must start with EVALUATE. "
                        "Example: EVALUATE SUMMARIZECOLUMNS('Date'[Month], "
                        "\"Revenue\", [Total Revenue])"
                    ),
                }
            },
            "required": ["dax_query"],
        },
    },
}
