"""RX-Coordinator — routes user questions through Foundry prompt agents.

Flow: User Question -> RX-QueryEngine (Prompt Agent, returns DAX in markers)
                    -> Coordinator extracts DAX + executes against Power BI
                    -> RX-Analyst (Prompt Agent, interprets raw data)
                    -> Adaptive Card

Both agents are pure Foundry Prompt Agents (no function tools). The Coordinator
performs deterministic DAX extraction + execution between the two agents.
"""

import asyncio
import json
import os
import re
import structlog
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient

from src.bot.turn_state import ConversationState
from src.bot.adaptive_cards import build_insight_card, build_error_card
from src.orchestrator.response_formatter import parse_analyst_response
from src.tools.pbi_execute_query import execute_dax_query

logger = structlog.get_logger(__name__)

# Marker-delimited DAX contract between RX-QueryEngine and the Coordinator.
DAX_START_MARKER = "=== DAX START ==="
DAX_END_MARKER = "=== DAX END ==="
CANNOT_ANSWER_SENTINEL = "CANNOT_ANSWER"

_DAX_BLOCK_RE = re.compile(
    rf"{re.escape(DAX_START_MARKER)}\s*(.*?)\s*{re.escape(DAX_END_MARKER)}",
    re.DOTALL | re.IGNORECASE,
)


class Coordinator:
    """Deterministic router — no LLM reasoning at this layer.

    1. Sends user question to RX-QueryEngine prompt agent.
    2. Parses DAX from `=== DAX START === / === DAX END ===` markers.
    3. Executes DAX against Power BI (with RLS via impersonatedUser).
    4. Feeds original question + DAX + raw result into RX-Analyst prompt agent.
    5. Parses Analyst output into an Adaptive Card.
    """

    def __init__(self) -> None:
        self.project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
        self.query_engine_agent_id = os.environ["FOUNDRY_QUERY_ENGINE_AGENT_ID"]
        self.analyst_agent_id = os.environ["FOUNDRY_ANALYST_AGENT_ID"]

    async def process(
        self,
        user_question: str,
        state: ConversationState,
        user_principal_name: str | None = None,
    ) -> dict:
        """Run the full pipeline and return a dict with 'card', 'dax', 'summary'.

        Args:
            user_question: The natural-language question from the Teams user.
            state: Conversation turn state.
            user_principal_name: UPN (email) of the Teams user for PBI RLS.
        """
        credential = DefaultAzureCredential()

        try:
            async with AIProjectClient(
                endpoint=self.project_endpoint,
                credential=credential,
            ) as client:
                # -- Step 1: RX-QueryEngine (Prompt Agent -> DAX text) --
                logger.info("invoking_query_engine", question=user_question[:100])

                qe_thread = await client.agents.create_thread()
                await client.agents.create_message(
                    thread_id=qe_thread.id,
                    role="user",
                    content=user_question,
                )

                qe_run = await client.agents.create_run(
                    thread_id=qe_thread.id,
                    assistant_id=self.query_engine_agent_id,
                )
                qe_run = await self._poll_run(
                    client, qe_thread.id, qe_run.id, label="query_engine"
                )

                qe_messages = await client.agents.list_messages(thread_id=qe_thread.id)
                qe_response = self._extract_last_assistant_message(qe_messages)

                logger.info(
                    "query_engine_complete",
                    response_length=len(qe_response),
                )

                # -- Step 2: Parse + execute DAX --
                dax = self._extract_dax_from_markers(qe_response)

                if dax.strip().upper() == CANNOT_ANSWER_SENTINEL:
                    reason = self._extract_reason(qe_response)
                    logger.info("query_engine_cannot_answer", reason=reason)
                    await client.agents.delete_thread(qe_thread.id)
                    message = (
                        reason
                        or "The Routes Insights - Flyr model does not contain the data needed to answer that question."
                    )
                    card = build_error_card(message)
                    return {"card": card, "dax": "", "summary": reason or ""}

                if not dax:
                    logger.error(
                        "query_engine_missing_dax_markers",
                        response=qe_response[:500],
                    )
                    await client.agents.delete_thread(qe_thread.id)
                    card = build_error_card(
                        "QueryEngine did not return DAX between the expected === DAX START === / === DAX END === markers."
                    )
                    return {"card": card, "dax": "", "summary": ""}

                logger.info("executing_dax", dax=dax[:200])
                pbi_result = await execute_dax_query(
                    dax, user_principal_name=user_principal_name
                )

                # -- Step 3: RX-Analyst (Prompt Agent -> commercial interpretation) --
                logger.info("invoking_analyst")

                analyst_prompt = (
                    f"Original question: {user_question}\n\n"
                    f"DAX executed:\n```dax\n{dax}\n```\n\n"
                    f"Raw result (JSON):\n{json.dumps(pbi_result, default=str)}"
                )

                analyst_thread = await client.agents.create_thread()
                await client.agents.create_message(
                    thread_id=analyst_thread.id,
                    role="user",
                    content=analyst_prompt,
                )

                analyst_run = await client.agents.create_run(
                    thread_id=analyst_thread.id,
                    assistant_id=self.analyst_agent_id,
                )
                analyst_run = await self._poll_run(
                    client, analyst_thread.id, analyst_run.id, label="analyst"
                )

                analyst_messages = await client.agents.list_messages(thread_id=analyst_thread.id)
                analyst_response = self._extract_last_assistant_message(analyst_messages)

                logger.info(
                    "analyst_complete",
                    response_length=len(analyst_response),
                )

                # -- Step 4: Format -> Adaptive Card --
                parsed = parse_analyst_response(analyst_response)

                card = build_insight_card(
                    question=user_question,
                    summary=parsed["summary"],
                    findings=parsed["findings"],
                    flags=parsed.get("flags"),
                    recommendation=parsed.get("recommendation"),
                    dax=dax,
                )

                # Cleanup threads
                await client.agents.delete_thread(qe_thread.id)
                await client.agents.delete_thread(analyst_thread.id)

                return {
                    "card": card,
                    "dax": dax,
                    "summary": parsed["summary"],
                }

        finally:
            await credential.close()

    async def _poll_run(self, client, thread_id: str, run_id: str, label: str = "run"):
        """Poll a Prompt Agent run until completion.

        Prompt Agents never enter `requires_action` (no function tools), so this
        is a simple status poll. If the run ever requests tool outputs we fail
        fast — it means the agent was misconfigured as a Hosted Agent.
        """
        while True:
            run = await client.agents.get_run(thread_id=thread_id, run_id=run_id)

            if run.status == "completed":
                return run
            if run.status == "failed":
                raise RuntimeError(
                    f"{label} run failed: {run.last_error.message if run.last_error else 'unknown'}"
                )
            if run.status == "requires_action":
                raise RuntimeError(
                    f"{label} entered requires_action — Prompt Agents must not request tools."
                )

            await asyncio.sleep(1)

    def _extract_last_assistant_message(self, messages) -> str:
        """Extract the text content of the last assistant message."""
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                for block in msg.content:
                    if hasattr(block, "text"):
                        return block.text.value
        return ""

    def _extract_dax_from_markers(self, qe_response: str) -> str:
        """Extract DAX between === DAX START === / === DAX END === markers.

        Returns the inner text stripped of whitespace, or empty string if
        markers are missing. Strips accidental code fences inside the block.
        """
        match = _DAX_BLOCK_RE.search(qe_response)
        if not match:
            return ""
        inner = match.group(1).strip()
        # Defensive: strip accidental ```dax ... ``` fences inside the markers.
        inner = re.sub(r"^```(?:dax)?\s*", "", inner, flags=re.IGNORECASE)
        inner = re.sub(r"\s*```$", "", inner)
        return inner.strip()

    def _extract_reason(self, qe_response: str) -> str:
        """Extract the `Reason: ...` line after a CANNOT_ANSWER block."""
        for line in qe_response.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("reason:"):
                return stripped[len("reason:"):].strip()
        return ""
