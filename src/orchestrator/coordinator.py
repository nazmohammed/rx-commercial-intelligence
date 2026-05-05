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
                openai_client = project_client.get_openai_client()
                # -- Step 1: RX-QueryEngine (Prompt Agent -> DAX text) --
                logger.info("invoking_query_engine", question=user_question[:100])

                qe_resp = await openai_client.responses.create(
                    input=user_question,
                    extra_body=_agent_reference(self.query_engine_agent_name),
                    timeout=30.0,
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
                    timeout=30.0,
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
                    # Raw PBI rows for the web frontend to draw charts/tables.
                    # Shape: list of {col: value, ...} dicts. May be empty.
                    "data": pbi_result.get("tables", []) if isinstance(pbi_result, dict) else [],
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
