from pydantic import BaseModel, Field

from app.services.ask_ai.constants.ticket import TicketStatus, TicketPriority
from app.schemas.ask_ai.auto_response import MessageSegment


class UnifiedResponseWithSegmentation(BaseModel):
    reasoning: str = Field(default="", description="Step-by-step thought process explaining the approach")
    should_skip: bool = Field(description="Whether to skip responding")
    skip_reason: str = Field(default="", description="Reason for skip")
    segments: list[MessageSegment] = Field(
        default_factory=list,
        description="Message segments to send sequentially"
    )
    ticket_priority: TicketPriority = Field(description="Ticket priority")
    ticket_status: TicketStatus = Field(description="Ticket status")
    ticket_summary: str = Field(default="", description="Brief 1-line ticket summary")
    agent_can_reply: bool = Field(description="Whether AI can handle this")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
