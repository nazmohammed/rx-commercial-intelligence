"""Smoke test: verify Foundry Prompt Agent invocation via Responses API.

Invokes the Analyst Prompt Agent by its display name (e.g. "RX-Analyst") via
the OpenAI Responses API using `agent_reference`. This is the correct path
for agents created in the new Foundry portal experience.

Usage:
    python -m scripts.smoke_test_foundry
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
    agent_name = os.getenv("FOUNDRY_ANALYST_AGENT_ID")

    if not endpoint or not agent_name:
        print("FOUNDRY_PROJECT_ENDPOINT or FOUNDRY_ANALYST_AGENT_ID not set")
        return 1

    print("-- Foundry smoke test --")
    print(f"Endpoint:   {endpoint}")
    print(f"Agent name: {agent_name}")
    print()

    credential = DefaultAzureCredential()
    try:
        async with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            openai_client = await project_client.get_openai_client()
            print("Invoking agent via Responses API...")
            resp = await openai_client.responses.create(
                input="Reply with exactly: 'smoke test ok'",
                extra_body={
                    "agent_reference": {
                        "name": agent_name,
                        "type": "agent_reference",
                    }
                },
            )
            text = resp.output_text or ""
            if text:
                print(f"\nAgent replied: {text}")
                return 0
            print("Agent returned no text output")
            print(f"Full response: {resp}")
            return 1
    finally:
        await credential.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
