"""Diagnostic: list all agents in the Foundry project.

Usage:
    python -m scripts.list_foundry_agents
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient


async def main() -> int:
    load_dotenv()
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint:
        print("FOUNDRY_PROJECT_ENDPOINT not set in .env")
        return 1

    print(f"Endpoint: {endpoint}")
    print("-" * 60)

    credential = DefaultAzureCredential()
    try:
        async with AIProjectClient(endpoint=endpoint, credential=credential) as client:
            count = 0
            async for a in client.agents.list_agents():
                count += 1
                print(f"  [{count}] name={a.name!r}  id={a.id}")
            print("-" * 60)
            print(f"Total agents: {count}")
    finally:
        await credential.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
