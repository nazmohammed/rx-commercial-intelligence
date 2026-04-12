"""Bot application — M365 Agents SDK activity handlers for Teams."""

import json
import structlog
from botbuilder.core import ActivityHandler, TurnContext, CardFactory
from botbuilder.schema import Activity, ActivityTypes

from src.bot.turn_state import get_state
from src.bot.adaptive_cards import build_thinking_card, build_error_card
from src.orchestrator.coordinator import Coordinator

logger = structlog.get_logger(__name__)


class RXBot(ActivityHandler):
    """Teams bot that routes user messages to the RX-Coordinator pipeline."""

    def __init__(self) -> None:
        super().__init__()
        self.coordinator = Coordinator()

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        user_message = turn_context.activity.text or ""
        conversation_id = turn_context.activity.conversation.id
        user_name = turn_context.activity.from_property.name or "User"

        logger.info(
            "message_received",
            user=user_name,
            conversation=conversation_id,
            message=user_message[:100],
        )

        if not user_message.strip():
            return

        state = get_state(conversation_id)
        state.new_turn(user_message)

        # Send "thinking" card
        thinking_card = CardFactory.adaptive_card(build_thinking_card())
        thinking_activity = Activity(
            type=ActivityTypes.message,
            attachments=[thinking_card],
        )
        thinking_response = await turn_context.send_activity(thinking_activity)

        try:
            # Run the full pipeline: QueryEngine → Analyst → Card
            result = await self.coordinator.process(user_message, state)

            # Update the thinking card with the real result
            card = CardFactory.adaptive_card(result["card"])
            update_activity = Activity(
                id=thinking_response.id,
                type=ActivityTypes.message,
                attachments=[card],
            )
            await turn_context.update_activity(update_activity)

            # Persist DAX for follow-up questions
            state.last_dax = result.get("dax", "")
            state.last_result_summary = result.get("summary", "")

        except Exception as e:
            logger.error("pipeline_failed", error=str(e), conversation=conversation_id)
            error_card = CardFactory.adaptive_card(
                build_error_card(f"Pipeline error: {str(e)[:200]}")
            )
            update_activity = Activity(
                id=thinking_response.id,
                type=ActivityTypes.message,
                attachments=[error_card],
            )
            await turn_context.update_activity(update_activity)

    async def on_members_added_activity(self, members_added, turn_context: TurnContext) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "👋 Hi! I'm **RX Commercial Intelligence**. "
                    "Ask me any question about routes, revenue, load factors, "
                    "or passenger trends and I'll query the data and give you "
                    "a commercial interpretation.\n\n"
                    "Try: *What's the load factor on RUH-LHR for Q1 2025?*"
                )
