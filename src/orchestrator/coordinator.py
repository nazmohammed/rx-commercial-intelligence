"""RX-Coordinator — routes user questions through Foundry prompt agents.

Flow: User Question -> RX-QueryEngine (Prompt Agent, returns DAX in markers)
                    -> Coordinator extracts DAX + executes against Power BI
                    -> RX-Analyst (Prompt Agent, interprets raw data)
                    -> Adaptive Card

Both agents are Foundry Prompt Agents created via the new Foundry portal
experience. They are invoked via the OpenAI Responses API with an
`agent_reference` (by display name). No tools; Coordinator does all deterministic
DAX extraction and execution between the two agents.
"""

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


def _agent_reference(name: str) -> dict:
    """Build the extra_body payload for invoking a Foundry Prompt Agent by name."""
    return {"agent_reference": {"name": name, "type": "agent_reference"}}


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
        # Display names of the Foundry Prompt Agents (e.g. "RX-QueryEngine", "RX-Analyst")
        self.query_engine_agent_name = os.environ["FOUNDRY_QUERY_ENGINE_AGENT_ID"]
        self.analyst_agent_name = os.environ["FOUNDRY_ANALYST_AGENT_ID"]

    async def process(
        self,
        user_question: str,
        state: ConversationState,
        user_principal_name: str | None = None,
    ) -> dict:
        """Run the full pipeline and return a dict with 'card', 'dax', 'summary'."""
        credential = DefaultAzureCredential()

        try:
            async with AIProjectClient(
                endpoint=self.project_endpoint,
                credential=credential,
            ) as project_client:
                openai_client = await project_client.get_openai_client()
                # -- Step 1: RX-QueryEngine (Prompt Agent -> DAX text) --
                logger.info("invoking_query_engine", question=user_question[:100])

                qe_resp = await openai_client.responses.create(
                    input=user_question,
                    extra_body=_agent_reference(self.query_engine_agent_name),
                )
                qe_response = qe_resp.output_text or ""

                logger.info(
                    "query_engine_complete",
                    response_length=len(qe_response),
                )

                # -- Step 2: Parse + execute DAX --
                dax = self._extract_dax_from_markers(qe_response)

                if dax.strip().upper() == CANNOT_ANSWER_SENTINEL:
                    reason = self._extract_reason(qe_response)
                    logger.info("query_engine_cannot_answer", reason=reason)
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

                analyst_resp = await openai_client.responses.create(
                    input=analyst_prompt,
                    extra_body=_agent_reference(self.analyst_agent_name),
                )
                analyst_response = analyst_resp.output_text or ""

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

                return {
                    "card": card,
                    "dax": dax,
                    "summary": parsed["summary"],
                }

        finally:
            await credential.close()

    def _extract_dax_from_markers(self, qe_response: str) -> str:
        """Extract DAX between === DAX START === / === DAX END === markers."""
        match = _DAX_BLOCK_RE.search(qe_response)
        if not match:
            return ""
        inner = match.group(1).strip()
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
        self.query_engine_agent_ref = os.environ["FOUNDRY_QUERY_ENGINE_AGENT_ID"]
        self.analyst_agent_ref = os.environ["FOUNDRY_ANALYST_AGENT_ID"]
        # Resolved asst_* IDs are cached after first lookup.
        self._resolved_ids: dict[str, str] = {}

    async def _resolve_agent_id(self, client, ref: str) -> str:
        """Resolve a reference (either `asst_*` ID or display name) to an asst_* ID.

        The Foundry SDK requires `assistant_id` to begin with `asst`. The portal
        exposes agents by display name (e.g., `RX-Analyst`), so we look them up
        via `list_agents()` when the env var is a name rather than an ID.
        """
        if ref.startswith("asst"):
            return ref
        if ref in self._resolved_ids:
            return self._resolved_ids[ref]
        async for agent in client.agents.list_agents():
            if agent.name == ref:
                self._resolved_ids[ref] = agent.id
                logger.info("resolved_agent_name", name=ref, agent_id=agent.id)
                return agent.id
        raise RuntimeError(
            f"Could not find Foundry agent with name '{ref}'. "
            f"Check the display name in the portal or set the env var to the asst_* ID."
        )

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

                qe_thread = await client.agents.threads.create()
                await client.agents.messages.create(
                    thread_id=qe_thread.id,
                    role="user",
                    content=user_question,
                )

                qe_agent_id = await self._resolve_agent_id(
                    client, self.query_engine_agent_ref
                )
                qe_run = await client.agents.runs.create(
                    thread_id=qe_thread.id,
                    agent_id=qe_agent_id,
                )
                qe_run = await self._poll_run(
                    client, qe_thread.id, qe_run.id, label="query_engine"
                )

                qe_response = await self._extract_last_assistant_message(
                    client, qe_thread.id
                )

                logger.info(
                    "query_engine_complete",
                    response_length=len(qe_response),
                )

                # -- Step 2: Parse + execute DAX --
                dax = self._extract_dax_from_markers(qe_response)

                if dax.strip().upper() == CANNOT_ANSWER_SENTINEL:
                    reason = self._extract_reason(qe_response)
                    logger.info("query_engine_cannot_answer", reason=reason)
                    await client.agents.threads.delete(qe_thread.id)
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
                    await client.agents.threads.delete(qe_thread.id)
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

                analyst_thread = await client.agents.threads.create()
                await client.agents.messages.create(
                    thread_id=analyst_thread.id,
                    role="user",
                    content=analyst_prompt,
                )

                analyst_agent_id = await self._resolve_agent_id(
                    client, self.analyst_agent_ref
                )
                analyst_run = await client.agents.runs.create(
                    thread_id=analyst_thread.id,
                    agent_id=analyst_agent_id,
                )
                analyst_run = await self._poll_run(
                    client, analyst_thread.id, analyst_run.id, label="analyst"
                )

                analyst_response = await self._extract_last_assistant_message(
                    client, analyst_thread.id
                )

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
                await client.agents.threads.delete(qe_thread.id)
                await client.agents.threads.delete(analyst_thread.id)

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
            run = await client.agents.runs.get(thread_id=thread_id, run_id=run_id)

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

    async def _extract_last_assistant_message(self, client, thread_id: str) -> str:
        """Fetch the last assistant message on the thread and return its text."""
        collected = []
        async for msg in client.agents.messages.list(thread_id=thread_id):
            collected.append(msg)
        for msg in reversed(collected):
            if msg.role == "assistant":
                for block in msg.content:
                    if hasattr(block, "text") and block.text is not None:
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
