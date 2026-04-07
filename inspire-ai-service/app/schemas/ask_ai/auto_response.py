from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.ask_ai.draft_response import ChatMessageSchema, TopicSchema
from app.schemas.ask_ai.message_segment import MessageSegment
from app.services.ask_ai.constants.draft_response import Channel
from app.schemas.ask_ai.ticket import Ticket


class CustomerContext(BaseModel):
    """Customer information for personalization"""
    customer_id: str = ""
    name: str = "Khách hàng"
    email: str = ""
    phone: str = ""


class TicketInfo(BaseModel):
    """Ticket context information"""
    ticket_id: str = ""
    status: str = ""
    source: str = ""
    priority: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class ConversationContext(BaseModel):
    """Conversation-level context and notes"""
    chatroom_id: str = ""
    internal_notes: List[str] = Field(default_factory=list)
    total_messages: int = 0
    last_agent_name: str | None = None


class MessageAttachment(BaseModel):
    type: str = Field(..., description="Attachment type: 'image' | 'file' | 'video'")
    url: str = Field(..., description="URL of the attachment")
    name: str = Field(default="", description="Filename")


class AutoResponseDto(BaseModel):
    agent_name: str | None = None
    org_desc: str | None = None
    chat_history: list[ChatMessageSchema]
    rules: list[str] | None = None
    response_template: str | None = None
    topics: list[TopicSchema] | None = None
    channel: Channel | None = None
    tone: str | None = None
    language: str | None = None
    additional_context: dict[str, str] = {}
    doc_ids: Optional[list[str]] = Field(
        None, description="Optional document IDs to filter by"
    )
    user_id: str | None = None
    customer_context: dict | None = None
    email_metadata: dict | None = None
    ticket_info: dict | None = None
    conversation_context: dict | None = None


class AutoResponseResultDto(BaseModel):
    response: list[MessageSegment] = Field(
        default_factory=list,
        description="List of message segments to send sequentially"
    )

    ticket: Ticket
    agent_can_reply: bool
    skipResponse: bool = False
