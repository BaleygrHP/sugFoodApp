from pydantic import BaseModel
from typing import Any, Optional

from app.services.ask_ai.constants.ticket import TicketPriority, TicketStatus


class TriageContext(BaseModel):
    current_ticket_status: str = ""
    chat_history: list[Any] | None = None
    channel: Any | None = None
    org_desc: str = ""
    additional_context: dict[str, Any] = {}
    customer_context: dict[str, Any] | None = None
    email_metadata: dict[str, Any] | None = None
    ticket_info: dict[str, Any] | None = None
    conversation_context: dict[str, Any] | None = None
    skip_triage: bool = False


class TriageDecision(BaseModel):
    should_reactivate: bool
    should_skip: bool
    skip_reason: str = ""
    priority_level: TicketPriority = TicketPriority.MEDIUM
    confidence: float = 0.0
    ticket_status: TicketStatus | None = None


def default_activate_decision() -> TriageDecision:
    return TriageDecision(
        should_reactivate=True,
        should_skip=False,
        skip_reason="",
        priority_level=TicketPriority.MEDIUM,
        confidence=0.5,
    )
