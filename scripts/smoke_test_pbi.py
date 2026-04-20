"""Smoke test: verify PBI authentication and executeQueries API access.

Runs a minimal DAX query against the configured dataset. Does NOT invoke Foundry.
Uses DefaultAzureCredential — make sure you've run `az login` first.

Usage:
    python -m scripts.smoke_test_pbi
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

from src.tools.pbi_execute_query import execute_dax_query
from src.tools.pbi_auth import close_credential

MINIMAL_DAX = "EVALUATE ROW(\"probe\", 1)"


async def main() -> int:
    load_dotenv()

    for var in ("PBI_WORKSPACE_ID", "PBI_DATASET_ID"):
        if not os.getenv(var):
            print(f"❌ {var} not set in .env")
            return 1

    print("── PBI smoke test ──")
    print(f"Workspace: {os.getenv('PBI_WORKSPACE_ID')}")
    print(f"Dataset:   {os.getenv('PBI_DATASET_ID')}")
    print(f"DAX:       {MINIMAL_DAX}")
    print()

    upn = os.getenv("TEST_USER_UPN")
    if upn:
        print(f"Impersonating: {upn}")

    try:
        result = await execute_dax_query(MINIMAL_DAX, user_principal_name=upn)
    finally:
        await close_credential()

    if result["success"]:
        print(f"✅ Query succeeded — {result['row_count']} row(s)")
        print(f"   Tables: {result['tables']}")
        return 0

    print(f"❌ Query failed: {result['error']}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
