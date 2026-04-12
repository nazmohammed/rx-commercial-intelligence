"""Conversation turn-state management for RX-Coordinator."""

from dataclasses import dataclass, field


@dataclass
class ConversationState:
    """Tracks conversation context across turns."""

    conversation_id: str = ""
    turn_count: int = 0
    last_query: str = ""
    last_dax: str = ""
    last_result_summary: str = ""
    pending_clarification: bool = False

    def new_turn(self, user_message: str) -> None:
        self.turn_count += 1
        self.last_query = user_message
        self.pending_clarification = False


# In-memory store — swap for Redis/Cosmos in production.
_STATES: dict[str, ConversationState] = {}


def get_state(conversation_id: str) -> ConversationState:
    if conversation_id not in _STATES:
        _STATES[conversation_id] = ConversationState(conversation_id=conversation_id)
    return _STATES[conversation_id]
