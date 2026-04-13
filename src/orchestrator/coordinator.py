"""RX-Coordinator — routes user questions through Foundry prompt agents.

Flow: User Question → RX-QueryEngine (DAX + execute) → RX-Analyst (interpret) → Adaptive Card
"""

import json
import os
import structlog
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import AgentStreamEvent

from src.bot.turn_state import ConversationState
from src.bot.adaptive_cards import build_insight_card, build_error_card
from src.orchestrator.response_formatter import parse_analyst_response
from src.tools.pbi_execute_query import execute_dax_query

logger = structlog.get_logger(__name__)


class Coordinator:
    """Deterministic router — no LLM reasoning at this layer.

    1. Sends user question to RX-QueryEngine prompt agent.
    2. When QueryEngine calls execute_dax_query tool, we execute it locally
       and return the result.
    3. Takes QueryEngine's response (DAX + raw data) and feeds it to RX-Analyst.
    4. Parses Analyst output into an Adaptive Card.
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
        self._current_upn = user_principal_name

        credential = DefaultAzureCredential()

        try:
            async with AIProjectClient(
                endpoint=self.project_endpoint,
                credential=credential,
            ) as client:
                # ── Step 1: RX-QueryEngine ──
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

                # Poll until complete, handling tool calls
                qe_run = await self._poll_run_with_tools(
                    client, qe_thread.id, qe_run.id, user_principal_name
                )

                # Get QueryEngine response
                qe_messages = await client.agents.list_messages(thread_id=qe_thread.id)
                qe_response = self._extract_last_assistant_message(qe_messages)

                logger.info(
                    "query_engine_complete",
                    response_length=len(qe_response),
                )

                # ── Step 2: RX-Analyst ──
                logger.info("invoking_analyst")

                analyst_prompt = (
                    f"Original question: {user_question}\n\n"
                    f"QueryEngine response (contains DAX + raw data):\n{qe_response}"
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

                # Analyst has no tools — just poll until done
                analyst_run = await self._poll_run(client, analyst_thread.id, analyst_run.id)

                analyst_messages = await client.agents.list_messages(thread_id=analyst_thread.id)
                analyst_response = self._extract_last_assistant_message(analyst_messages)

                logger.info(
                    "analyst_complete",
                    response_length=len(analyst_response),
                )

                # ── Step 3: Format → Adaptive Card ──
                parsed = parse_analyst_response(analyst_response)
                dax = self._extract_dax_from_qe(qe_response)

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

    async def _poll_run_with_tools(
        self, client, thread_id: str, run_id: str, user_principal_name: str | None = None
    ):
        """Poll a run, handling tool-call actions for execute_dax_query."""
        import asyncio

        while True:
            run = await client.agents.get_run(thread_id=thread_id, run_id=run_id)

            if run.status == "completed":
                return run

            if run.status == "failed":
                raise RuntimeError(
                    f"QueryEngine run failed: {run.last_error.message if run.last_error else 'unknown'}"
                )

            if run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []

                for tc in tool_calls:
                    if tc.function.name == "execute_dax_query":
                        args = json.loads(tc.function.arguments)
                        dax = args.get("dax_query", "")
                        logger.info("executing_dax_tool", dax=dax[:200])

                        result = await execute_dax_query(
                            dax, user_principal_name=user_principal_name
                        )
                        tool_outputs.append({
                            "tool_call_id": tc.id,
                            "output": json.dumps(result),
                        })
                    else:
                        logger.warning("unknown_tool_call", name=tc.function.name)
                        tool_outputs.append({
                            "tool_call_id": tc.id,
                            "output": json.dumps({"error": f"Unknown tool: {tc.function.name}"}),
                        })

                await client.agents.submit_tool_outputs_to_run(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs,
                )

            await asyncio.sleep(1)

    async def _poll_run(self, client, thread_id: str, run_id: str):
        """Poll a run until complete (no tool handling)."""
        import asyncio

        while True:
            run = await client.agents.get_run(thread_id=thread_id, run_id=run_id)

            if run.status == "completed":
                return run
            if run.status == "failed":
                raise RuntimeError(
                    f"Analyst run failed: {run.last_error.message if run.last_error else 'unknown'}"
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

    def _extract_dax_from_qe(self, qe_response: str) -> str:
        """Pull the DAX query out of the QueryEngine response."""
        # QueryEngine is instructed to include DAX — look for the EVALUATE block
        lines = qe_response.split("\n")
        dax_lines = []
        capturing = False
        for line in lines:
            if "EVALUATE" in line.upper() and not capturing:
                capturing = True
            if capturing:
                dax_lines.append(line)
                # End on empty line or ``` fence after EVALUATE
                if line.strip() == "```" and len(dax_lines) > 1:
                    dax_lines.pop()  # remove closing fence
                    break
                if line.strip() == "" and len(dax_lines) > 2:
                    break

        return "\n".join(dax_lines).strip() if dax_lines else ""
