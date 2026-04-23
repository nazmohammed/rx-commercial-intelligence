"""Smoke test: verify Foundry connection + agent invocation.

Sends a trivial "hello" message to the Analyst agent (no tools) to validate
Foundry auth + agent ID config. Does NOT hit PBI.

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
    agent_id = os.getenv("FOUNDRY_ANALYST_AGENT_ID")

    if not endpoint or not agent_id:
        print("❌ FOUNDRY_PROJECT_ENDPOINT or FOUNDRY_ANALYST_AGENT_ID not set")
        return 1

    print("── Foundry smoke test ──")
    print(f"Endpoint: {endpoint}")
    print(f"Agent ID: {agent_id}")
    print()

    credential = DefaultAzureCredential()
    try:
        async with AIProjectClient(endpoint=endpoint, credential=credential) as client:
            print("Creating thread...")
            thread = await client.agents.threads.create()

            print("Sending test message...")
            await client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content="Reply with exactly: 'smoke test ok'",
            )

            print("Running agent...")
            run = await client.agents.runs.create(
                thread_id=thread.id, agent_id=agent_id
            )

            while run.status not in ("completed", "failed", "cancelled"):
                await asyncio.sleep(1)
                run = await client.agents.runs.get(thread_id=thread.id, run_id=run.id)

            if run.status != "completed":
                err = run.last_error.message if run.last_error else "unknown"
                print(f"❌ Run status: {run.status} — {err}")
                return 1

            collected = []
            async for msg in client.agents.messages.list(thread_id=thread.id):
                collected.append(msg)
            for msg in reversed(collected):
                if msg.role == "assistant":
                    for block in msg.content:
                        if hasattr(block, "text") and block.text is not None:
                            print(f"\n✅ Agent replied: {block.text.value}")
                            await client.agents.threads.delete(thread.id)
                            return 0

            print("❌ No assistant message found")
            return 1
    finally:
        await credential.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
