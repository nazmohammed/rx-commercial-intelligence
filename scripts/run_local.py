"""Local CLI runner for RX-Commercial-Intelligence — no bot, no Teams.

Runs the full Coordinator pipeline against a question read from the command
line or stdin, and prints the DAX, summary, findings, and recommendation.

Usage:
    python -m scripts.run_local
    python -m scripts.run_local "What's the flown load factor on RUH-LHR for Q1 2025?"

Requires `az login` (DefaultAzureCredential) and a populated .env file.
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

from src.bot.turn_state import ConversationState
from src.orchestrator.coordinator import Coordinator
from src.orchestrator.response_formatter import parse_analyst_response
from src.tools.pbi_auth import close_credential


def _print_section(title: str, body: str) -> None:
    print(f"\n── {title} ──")
    print(body.strip() if body else "(empty)")


async def run_once(question: str, user_upn: str | None) -> int:
    state = ConversationState(conversation_id="local-cli")
    state.new_turn(question)

    coordinator = Coordinator()
    try:
        result = await coordinator.process(
            question, state, user_principal_name=user_upn
        )
    finally:
        await close_credential()

    _print_section("DAX", result.get("dax", ""))
    _print_section("Summary", result.get("summary", ""))

    # Re-parse for full breakdown (coordinator already parsed once, but we
    # only kept summary in the result dict)
    card = result.get("card", {})
    # Best-effort pretty print of the Adaptive Card body
    print("\n── Adaptive Card (JSON preview) ──")
    import json
    print(json.dumps(card, indent=2)[:2000])
    return 0


async def main() -> int:
    load_dotenv()

    required = [
        "FOUNDRY_PROJECT_ENDPOINT",
        "FOUNDRY_QUERY_ENGINE_AGENT_ID",
        "FOUNDRY_ANALYST_AGENT_ID",
        "PBI_WORKSPACE_ID",
        "PBI_DATASET_ID",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        print("   Run: python -m scripts.check_env")
        return 1

    user_upn = os.getenv("TEST_USER_UPN")  # for RLS — optional

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        print("RX-Commercial-Intelligence — Local CLI")
        print("Type your question (or Ctrl+C to exit):")
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0

    if not question:
        print("❌ No question provided.")
        return 1

    print(f"\n🔎 Processing: {question}")
    if user_upn:
        print(f"   Impersonating: {user_upn}")

    return await run_once(question, user_upn)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
