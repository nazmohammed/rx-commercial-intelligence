"""Validate that all required environment variables are set for local dev.

Usage:
    python -m scripts.check_env
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

REQUIRED_VARS = [
    "FOUNDRY_PROJECT_ENDPOINT",
    "FOUNDRY_QUERY_ENGINE_AGENT_ID",
    "FOUNDRY_ANALYST_AGENT_ID",
    "PBI_WORKSPACE_ID",
    "PBI_DATASET_ID",
]

OPTIONAL_VARS = [
    "BOT_APP_ID",
    "BOT_APP_PASSWORD",
    "LOG_LEVEL",
    "PORT",
]


def main() -> int:
    load_dotenv()
    missing: list[str] = []

    print("── Required variables ──")
    for var in REQUIRED_VARS:
        value = os.getenv(var)
        if not value:
            print(f"  [MISSING] {var}")
            missing.append(var)
        else:
            display = value if len(value) < 60 else value[:57] + "..."
            print(f"  [OK]      {var} = {display}")

    print("\n── Optional variables (only needed for bot mode) ──")
    for var in OPTIONAL_VARS:
        value = os.getenv(var)
        status = "[set]" if value else "[unset]"
        print(f"  {status} {var}")

    if missing:
        print(f"\n❌ {len(missing)} required variable(s) missing. "
              f"Copy .env.template to .env and fill them in.")
        return 1

    print("\n✅ All required variables present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
